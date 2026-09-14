import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot
from sqlalchemy import select
from bot.database.session import async_session_factory
from bot.models.campaign import Campaign
from bot.services.broadcast_worker import execute_campaign
from config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.DEFAULT_TIMEZONE)


def start_scheduler() -> None:
    """Start APScheduler instance."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started.")


def shutdown_scheduler() -> None:
    """Shutdown APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")


def schedule_campaign(bot: Bot, campaign_id: int, run_date: datetime) -> None:
    """Schedule a campaign execution for a specific date and time."""
    job_id = f"campaign_{campaign_id}"
    # Remove existing job with same ID if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        func=execute_campaign,
        trigger=DateTrigger(run_date=run_date),
        args=[bot, campaign_id],
        id=job_id,
        name=f"Execute Campaign #{campaign_id}",
        replace_existing=True,
    )
    logger.info(f"Campaign #{campaign_id} scheduled for {run_date}.")


async def load_pending_campaigns(bot: Bot) -> None:
    """Load pending or scheduled campaigns on bot startup."""
    async with async_session_factory() as session:
        now = datetime.utcnow()
        stmt = select(Campaign).where(Campaign.status == "scheduled")
        res = await session.execute(stmt)
        campaigns = res.scalars().all()

        for camp in campaigns:
            if camp.scheduled_at:
                if camp.scheduled_at <= now:
                    # If scheduled time was in the past while bot was down, trigger immediately
                    logger.info(f"Triggering overdue campaign #{camp.id} immediately.")
                    scheduler.add_job(
                        func=execute_campaign,
                        trigger=DateTrigger(run_date=now),
                        args=[bot, camp.id],
                        id=f"campaign_{camp.id}",
                        replace_existing=True,
                    )
                else:
                    logger.info(f"Restoring scheduled campaign #{camp.id} for {camp.scheduled_at}.")
                    schedule_campaign(bot, camp.id, camp.scheduled_at)
