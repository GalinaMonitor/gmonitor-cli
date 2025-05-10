import asyncio
import uuid
from enum import StrEnum, auto
from typing import Optional

from faststream.kafka import KafkaBroker
from pydantic import BaseModel

from .settings import settings, logger


class TopicsEnum(StrEnum):
    """
    Перечисление тем для обмена сообщениями.
    """

    GPT_BOT_RESULT = "gpt_bot_result"
    GPT_BOT_REQUEST = "gpt_bot_request"


class GptDtoType(StrEnum):
    """
    Перечисление типов ответов от GPT модели.
    """

    IMAGE = auto()  # Изображение
    TEXT = auto()  # Текст
    AUDIO = auto()  # Аудио


class GptDto(BaseModel):
    """
    Модель данных для передачи ответов от GPT.
    """

    content: str  # Содержимое ответа
    is_error: bool = False  # Флаг ошибки
    chat_id: int | None = None  # Идентификатор чата
    type: GptDtoType = GptDtoType.TEXT  # Тип ответа


class RequestClient:
    def __init__(self) -> None:
        self.broker = KafkaBroker(
            f"{settings.kafka_host}:{settings.kafka_port}", logger=None
        )
        self.chat_id = int(uuid.uuid4())
        self.pending_request: asyncio.Future[GptDto] | None = None
        self.running = False

    async def start(self) -> None:
        if self.running:
            return

        @self.broker.subscriber(
            TopicsEnum.GPT_BOT_RESULT,
        )  # type: ignore
        async def handle_response(message: GptDto) -> None:
            if message.chat_id != self.chat_id:
                return
            future = self.pending_request
            if future and not future.done():
                future.set_result(message)

        await self.broker.start()
        self.running = True
        logger.info(f"Запуск клиента с ID {self.chat_id}")

    async def stop(self) -> None:
        if not self.running:
            return
        await self.broker.close()
        self.running = False
        if self.pending_request and not self.pending_request.done():
            self.pending_request.cancel()
        logger.info("Остановка клиента")

    async def send_request(
        self, content: str, timeout: float = 10.0
    ) -> Optional[GptDto]:
        if not self.running:
            await self.start()
        request = GptDto(content=content, chat_id=int(self.chat_id))
        future: asyncio.Future[GptDto] = asyncio.Future()
        self.pending_request = future
        await self.broker.publish(request, topic=TopicsEnum.GPT_BOT_REQUEST)
        logger.info(f"Отправлен запрос с ID {self.chat_id}: {content}")
        try:
            response = await asyncio.wait_for(future, timeout)
            return response
        except asyncio.TimeoutError:
            self.pending_request = None
            logger.info(f"Запрос с ID {self.chat_id} превысил лимит в {timeout} секунд")
            return None
