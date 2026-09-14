import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # بيانات البوت وتطبيق تيليجرام مدمجة تلقائياً حتى لا تحتاج لإدخالها في Railway
    BOT_TOKEN: str = "8842449473:AAEm6wVnqZ2jUykicJH-FvMeGo81MMiHoRc"
    TELEGRAM_API_ID: int = 30385406
    TELEGRAM_API_HASH: str = "550152f6b7d91c878af99abf61534eef"

    # المتغير الوحيد المطلوب في Railway (أو يعمل بـ SQLite افتراضياً بدون أي متغيرات)
    DATABASE_URL: str = "sqlite+aiosqlite:///./bot_database.db"

    # إعدادات وحدود الإرسال (Rate Limits)
    DEFAULT_TIMEZONE: str = "Africa/Cairo"
    DEFAULT_DELAY_BETWEEN_TARGETS: float = 1.5  # الفاصل الزمني الافتراضي بين الأهداف
    RATE_LIMIT_DELAY: float = 1.5               # أدنى فاصل زمني مسموح به
    MAX_REPEAT_LIMIT: int = 50                  # الحد الأقصى لمرات التكرار
    MAX_TARGETS_LIMIT: int = 500                # الحد الأقصى لعدد الأهداف في الحملة الواحدة
    MAX_RETRY_ATTEMPTS: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_admin(self, user_id: int) -> bool:
        return True


settings = Settings()
