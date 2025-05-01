import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    kafka_host: str = "localhost"
    kafka_port: int = 9092
    model_config = SettingsConfigDict(env_prefix="GMONITOR_CLI_")


settings = Settings()
