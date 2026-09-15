import logging
import re
from typing import Tuple, Dict, Any, List
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.target import Target

logger = logging.getLogger(__name__)


async def inspect_target(bot: Bot, identifier: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    فحص الهدف وإعداده للإرسال مباشرة بدون قيود أو شروط إشراف.
    """
    title = identifier
    chat_type = "channel"
    chat_id = None
    username = None

    # Check if identifier is numeric
    if re.fullmatch(r"-?\d+", identifier):
        val = int(identifier)
        # If user forgot negative sign for supergroup
        if val > 0 and len(str(val)) >= 9:
            val = -val
        chat_id = val
    elif identifier.startswith("@"):
        username = identifier

    try:
        chat = await bot.get_chat(chat_id=identifier)
        chat_id = chat.id
        title = chat.title or chat.full_name or str(chat.id)
        username = f"@{chat.username}" if chat.username else username
        chat_type = chat.type
    except Exception as e:
        logger.warning(f"Could not fetch full chat info for {identifier}: {str(e)}")

    if chat_id is None:
        chat_id = 0

    info = {
        "chat_id": chat_id,
        "title": title,
        "username": username,
        "chat_type": chat_type,
        "can_post_messages": True,  # دائماً مسموح بدون أي حظر إشراف
        "can_send_media": True,
        "status_description": "جاهز للإرسال ✅",
    }

    return True, info, "تم قبول الهدف بنجاح."


async def add_or_update_target(
    session: AsyncSession,
    owner_id: int,
    info: Dict[str, Any],
) -> Tuple[Target, bool]:
    """إضافة أو تحديث الهدف في قاعدة البيانات"""
    stmt = select(Target).where(
        Target.owner_id == owner_id,
        Target.chat_id == info["chat_id"],
    )
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    is_new = False
    if not target:
        target = Target(
            owner_id=owner_id,
            chat_id=info["chat_id"],
            username=info.get("username"),
            title=info.get("title", ""),
            chat_type=info.get("chat_type", "channel"),
            can_post_messages=True,
            can_send_media=True,
            status_description="جاهز للإرسال ✅",
            is_active=True,
        )
        session.add(target)
        is_new = True
    else:
        target.username = info.get("username", target.username)
        target.title = info.get("title", target.title)
        target.chat_type = info.get("chat_type", target.chat_type)
        target.can_post_messages = True
        target.can_send_media = True
        target.status_description = "جاهز للإرسال ✅"
        target.is_active = True

    await session.commit()
    await session.refresh(target)
    return target, is_new


async def refresh_user_targets(bot: Bot, session: AsyncSession, owner_id: int) -> List[Tuple[Target, bool, str]]:
    """تحديث الأهداف"""
    stmt = select(Target).where(Target.owner_id == owner_id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    results = []
    for t in targets:
        t.can_post_messages = True
        t.can_send_media = True
        t.status_description = "جاهز للإرسال ✅"
        results.append((t, True, "جاهز للإرسال"))

    await session.commit()
    return results
