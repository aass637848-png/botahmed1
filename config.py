from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    BOT_TOKEN: str = "YOUR_BOT_TOKEN"
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    ADMIN_IDS: Union[List[int], str] = []
    DATABASE_URL: str = "sqlite+aiosqlite:///./bot_database.db"
    DEFAULT_TIMEZONE: str = "Africa/Cairo"
    DEFAULT_DELAY_BETWEEN_TARGETS: float = 1.5
    MAX_RETRY_ATTEMPTS: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_admin(self, user_id: int) -> bool:
        # Everyone has full access
        return True


settings = Settings()
