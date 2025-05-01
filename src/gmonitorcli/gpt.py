import asyncio

import pyperclip
import typer
from typing_extensions import Annotated

from .publisher import RequestClient


async def gpt(request: str, is_base: bool = False) -> None:
    client = RequestClient()
    if not is_base:
        request = (
            f"Верни только команду для linux-терминала без markdown-разметки: {request}"
        )
    try:
        await client.start()
        response = await client.send_request(request)
        if response:
            if not is_base:
                print(f"Команда '{response.text}' скопирована в буфер обмена")
                pyperclip.copy(response.text)
            else:
                print(f"Ответ: {response.text}")
    finally:
        await client.stop()


def main(
    raw_request: Annotated[
        list[str], typer.Argument(help="Описание команды для терминала")
    ],
    base: Annotated[
        bool, typer.Option("-b", help="Запрос напрямую к gpt без форматирования")
    ] = False,
) -> None:
    request = " ".join(raw_request)
    asyncio.run(gpt(request, is_base=base))
