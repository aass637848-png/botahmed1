import logging
import traceback
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update

logger = logging.getLogger("BotLogger")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_info = f"ID:{user.id} | @{user.username or 'NoUser'} | Name:{user.full_name or ''}" if user else "Unknown User"

        if isinstance(event, Message):
            content = event.text or event.caption or f"<{event.content_type}>"
            chat_info = f"ChatID:{event.chat.id} ({event.chat.type})"
            logger.info(f"📥 [Message] [{user_info}] [{chat_info}] Content: {content}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"🔘 [Button Click] [{user_info}] Action: '{event.data}'")
        elif isinstance(event, Update):
            logger.info(f"🔄 [Update] UpdateID:{event.update_id} Type:{event.event_type}")

        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                f"💥 [Handler Error] Event caused an exception for [{user_info}]: {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            raise e
