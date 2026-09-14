import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_info = f"User({user.id}, @{user.username})" if user else "Unknown User"

        if isinstance(event, Message):
            content = event.text or event.caption or f"<{event.content_type}>"
            logger.info(f"[{user_info}] Message: {content[:100]}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"[{user_info}] CallbackQuery: {event.data}")

        return await handler(event, data)
