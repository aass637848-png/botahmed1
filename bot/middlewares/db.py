from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.session import async_session_factory
from bot.models.user import User
from config import settings


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session

            # Auto-register/sync user if event has from_user
            event_user: TgUser | None = data.get("event_from_user")
            if event_user:
                stmt = select(User).where(User.user_id == event_user.id)
                res = await session.execute(stmt)
                db_user = res.scalar_one_or_none()

                is_admin_flag = settings.is_admin(event_user.id)

                if not db_user:
                    db_user = User(
                        user_id=event_user.id,
                        username=event_user.username,
                        full_name=event_user.full_name or "",
                        is_admin=is_admin_flag,
                    )
                    session.add(db_user)
                    await session.commit()
                else:
                    # Update username or admin status if changed
                    updated = False
                    if db_user.username != event_user.username:
                        db_user.username = event_user.username
                        updated = True
                    if db_user.full_name != (event_user.full_name or ""):
                        db_user.full_name = event_user.full_name or ""
                        updated = True
                    if is_admin_flag and not db_user.is_admin:
                        db_user.is_admin = True
                        updated = True
                    if updated:
                        await session.commit()

                data["db_user"] = db_user

            return await handler(event, data)
