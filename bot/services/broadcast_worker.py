import asyncio
import io
import logging
from datetime import datetime
from typing import Set, Dict, Any, List, Tuple, Optional
from aiogram import Bot
from aiogram.exceptions import (
    TelegramRetryAfter,
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramAPIError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.session import async_session_factory
from bot.models.campaign import Campaign
from bot.models.target import Target
from bot.models.message_log import MessageLog
from bot.models.account import Account
from bot.services.userbot_service import send_via_userbot
from bot.utils.notifier import (
    notify_campaign_started,
    notify_campaign_finished,
    notify_campaign_error,
)

logger = logging.getLogger(__name__)

# In-memory target lock set to prevent running multiple campaigns on the same target simultaneously
active_target_locks: Set[int] = set()
lock_mutex = asyncio.Lock()


async def is_any_target_locked(target_chat_ids: List[int]) -> bool:
    """Check if any of the given targets is currently running in a campaign."""
    async with lock_mutex:
        for cid in target_chat_ids:
            if cid in active_target_locks:
                return True
        return False


async def acquire_target_locks(target_chat_ids: List[int]) -> bool:
    """Try to acquire lock on all target chat IDs."""
    async with lock_mutex:
        for cid in target_chat_ids:
            if cid in active_target_locks:
                return False
        for cid in target_chat_ids:
            active_target_locks.add(cid)
        return True


async def release_target_locks(target_chat_ids: List[int]) -> None:
    """Release locks for all given target chat IDs."""
    async with lock_mutex:
        for cid in target_chat_ids:
            active_target_locks.discard(cid)


async def send_single_message(
    bot: Bot,
    chat_id: int | str,
    content_type: str,
    text_content: str | None,
    file_id: str | None,
) -> Tuple[bool, str | None, int | None]:
    """
    Send a single content unit to a chat.
    Returns: (is_success, error_message, retry_after)
    """
    try:
        if content_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption=text_content)
        elif content_type == "video":
            await bot.send_video(chat_id=chat_id, video=file_id, caption=text_content)
        elif content_type == "document":
            await bot.send_document(chat_id=chat_id, document=file_id, caption=text_content)
        else:
            # Default is text
            await bot.send_message(chat_id=chat_id, text=text_content or "")
        return True, None, None

    except TelegramRetryAfter as e:
        logger.warning(f"TelegramRetryAfter encountered for {chat_id}: sleeping {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        # Retry once after sleep
        try:
            if content_type == "photo":
                await bot.send_photo(chat_id=chat_id, photo=file_id, caption=text_content)
            elif content_type == "video":
                await bot.send_video(chat_id=chat_id, video=file_id, caption=text_content)
            elif content_type == "document":
                await bot.send_document(chat_id=chat_id, document=file_id, caption=text_content)
            else:
                await bot.send_message(chat_id=chat_id, text=text_content or "")
            return True, None, e.retry_after
        except Exception as retry_err:
            return False, f"فشل بعد الانتظار: {str(retry_err)}", e.retry_after

    except TelegramForbiddenError as e:
        return False, f"تم حظر البوت أو لا يملك صلاحية النشر ({e.message})", None
    except TelegramBadRequest as e:
        return False, f"طلب غير صالح ({e.message})", None
    except TelegramAPIError as e:
        return False, f"خطأ تيليجرام ({e.message})", None
    except Exception as e:
        return False, f"خطأ غير متوقع: {str(e)}", None


async def execute_campaign(bot: Bot, campaign_id: int) -> None:
    """
    Worker task to execute a full campaign (including iterations, delays, and logging).
    """
    async with async_session_factory() as session:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        res = await session.execute(stmt)
        campaign = res.scalar_one_or_none()

        if not campaign:
            logger.error(f"Campaign #{campaign_id} not found.")
            return

        if campaign.status in ("completed", "cancelled"):
            logger.info(f"Campaign #{campaign_id} is already {campaign.status}.")
            return

        # Fetch targets
        stmt_t = select(Target).where(Target.id.in_(campaign.target_ids))
        res_t = await session.execute(stmt_t)
        targets = res_t.scalars().all()

        if not targets:
            campaign.status = "failed"
            campaign.error_summary = "لم يتم العثور على أهداف للحملة."
            await session.commit()
            await notify_campaign_error(bot, campaign.owner_id, campaign.id, campaign.error_summary)
            return

        target_chat_ids = [t.chat_id for t in targets]

    # Try acquiring target locks
    locks_acquired = await acquire_target_locks(target_chat_ids)
    if not locks_acquired:
        error_msg = "تعذر بدء الحملة: أحد الأهداف المختارة يتم استخدامه حاليًا في حملة إرسال أخرى جارية."
        async with async_session_factory() as session:
            stmt = select(Campaign).where(Campaign.id == campaign_id)
            res = await session.execute(stmt)
            camp = res.scalar_one()
            camp.status = "failed"
            camp.error_summary = error_msg
            await session.commit()
        await notify_campaign_error(bot, campaign.owner_id, campaign.id, error_msg)
        return

    # Mark running
    start_time = datetime.now()
    async with async_session_factory() as session:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        res = await session.execute(stmt)
        camp = res.scalar_one()
        camp.status = "running"
        camp.started_at = start_time
        await session.commit()

    await notify_campaign_started(
        bot=bot,
        user_id=campaign.owner_id,
        campaign_id=campaign.id,
        total_targets=len(targets),
        repeat_count=campaign.repeat_count,
    )

    total_success = 0
    total_failed = 0
    last_err_msg = None

    # Pre-download media file into memory buffer if broadcasting via userbot
    cached_media_bytes: Optional[bytes] = None
    if campaign.sender_type == "userbot" and campaign.file_id:
        try:
            logger.info(f"📥 [Campaign #{campaign.id}] Downloading media file ({campaign.content_type}) for userbot...")
            media_buf = io.BytesIO()
            await bot.download(campaign.file_id, destination=media_buf)
            media_buf.seek(0)
            cached_media_bytes = media_buf.getvalue()
            logger.info(f"📥 [Campaign #{campaign.id}] Media file downloaded successfully ({len(cached_media_bytes)} bytes).")
        except Exception as dl_err:
            logger.error(f"❌ [Campaign #{campaign.id}] Failed to download media file: {str(dl_err)}")

    try:
        for iteration in range(1, campaign.repeat_count + 1):
            async with async_session_factory() as session:
                stmt = select(Campaign).where(Campaign.id == campaign_id)
                res = await session.execute(stmt)
                camp = res.scalar_one()

                # Check if paused or cancelled externally
                if camp.status in ("cancelled", "paused"):
                    logger.info(f"Campaign #{campaign_id} stopped with status: {camp.status}")
                    break

                camp.current_iteration = iteration
                await session.commit()

            # Iterate over targets
            for target in targets:
                # Check status again
                async with async_session_factory() as session:
                    stmt = select(Campaign).where(Campaign.id == campaign_id)
                    res = await session.execute(stmt)
                    camp = res.scalar_one()
                    if camp.status in ("cancelled", "paused"):
                        break

                # Resolve target destination: either chat_id or username
                dest = target.chat_id
                if (not dest or dest == 0) and target.username:
                    dest = target.username

                account_session_str = None
                if campaign.sender_type == "userbot" and campaign.sender_account_id:
                    async with async_session_factory() as session:
                        acc = await session.get(Account, campaign.sender_account_id)
                        if acc and acc.session_string:
                            account_session_str = acc.session_string

                logger.info(
                    f"📤 [Campaign #{campaign.id}] [Cycle {iteration}/{campaign.repeat_count}] "
                    f"Sending to target '{dest}' (Title: '{target.title}') via {campaign.sender_type}..."
                )

                if account_session_str:
                    media_payload = None
                    if cached_media_bytes:
                        media_payload = io.BytesIO(cached_media_bytes)
                        if campaign.content_type == "photo":
                            media_payload.name = "photo.jpg"
                        elif campaign.content_type == "video":
                            media_payload.name = "video.mp4"
                        else:
                            media_payload.name = "document.dat"

                    success, err_msg, retry_after = await send_via_userbot(
                        session_str=account_session_str,
                        target_identifier=dest,
                        content_type=campaign.content_type,
                        text_content=campaign.text_content,
                        file_path_or_bytes=media_payload,
                    )
                else:
                    success, err_msg, retry_after = await send_single_message(
                        bot=bot,
                        chat_id=dest,
                        content_type=campaign.content_type,
                        text_content=campaign.text_content,
                        file_id=campaign.file_id,
                    )

                if success:
                    total_success += 1
                    logger.info(f"✅ [Campaign #{campaign.id}] Successfully sent to '{dest}'!")
                else:
                    total_failed += 1
                    last_err_msg = err_msg
                    logger.error(f"❌ [Campaign #{campaign.id}] FAILED to send to '{dest}': {err_msg}")

                # Log result
                async with async_session_factory() as session:
                    log_entry = MessageLog(
                        campaign_id=campaign.id,
                        target_id=target.id,
                        chat_id=target.chat_id,
                        target_title=target.title,
                        iteration=iteration,
                        status="success" if success else "failed",
                        error_message=err_msg,
                        retry_after=retry_after,
                        sent_at=datetime.utcnow(),
                    )
                    session.add(log_entry)
                    await session.commit()

                # Delay between targets
                if campaign.delay_between_targets > 0:
                    logger.info(f"⏳ [Campaign #{campaign.id}] Waiting {campaign.delay_between_targets}s...")
                    await asyncio.sleep(campaign.delay_between_targets)

            # Check if we need to pause/sleep before next iteration
            if iteration < campaign.repeat_count and campaign.interval_seconds > 0:
                logger.info(f"Campaign #{campaign_id}: sleeping {campaign.interval_seconds}s for next iteration.")
                await asyncio.sleep(campaign.interval_seconds)

        # Mark campaign completed
        end_time = datetime.now()
        duration_seconds = int((end_time - start_time).total_seconds())
        duration_str = f"{duration_seconds // 60} دقيقة و {duration_seconds % 60} ثانية"

        async with async_session_factory() as session:
            stmt = select(Campaign).where(Campaign.id == campaign_id)
            res = await session.execute(stmt)
            camp = res.scalar_one()
            if camp.status == "running":
                camp.status = "completed"
                camp.finished_at = end_time
                await session.commit()

        await notify_campaign_finished(
            bot=bot,
            user_id=campaign.owner_id,
            campaign_id=campaign.id,
            success_count=total_success,
            failed_count=total_failed,
            duration_str=duration_str,
            last_error=last_err_msg,
        )

    except Exception as e:
        logger.exception(f"Unhandled error in campaign #{campaign_id}: {str(e)}")
        async with async_session_factory() as session:
            stmt = select(Campaign).where(Campaign.id == campaign_id)
            res = await session.execute(stmt)
            camp = res.scalar_one_or_none()
            if camp:
                camp.status = "failed"
                camp.error_summary = str(e)
                await session.commit()
        await notify_campaign_error(bot, campaign.owner_id, campaign.id, f"خطأ غير متوقع: {str(e)}")

    finally:
        # Always release locks
        await release_target_locks(target_chat_ids)
