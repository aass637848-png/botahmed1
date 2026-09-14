import csv
import io
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.models.campaign import Campaign
from bot.models.target import Target
from bot.models.message_log import MessageLog


async def get_user_statistics(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """Calculate overall statistics for a specific user."""
    # Total targets
    t_count = await session.scalar(
        select(func.count(Target.id)).where(Target.owner_id == user_id)
    )

    # Active campaigns count
    active_c_count = await session.scalar(
        select(func.count(Campaign.id)).where(
            Campaign.owner_id == user_id,
            Campaign.status.in_(["running", "scheduled"])
        )
    )

    # Total campaigns count
    total_c_count = await session.scalar(
        select(func.count(Campaign.id)).where(Campaign.owner_id == user_id)
    )

    # Message logs stats for campaigns owned by this user
    user_campaigns_subquery = select(Campaign.id).where(Campaign.owner_id == user_id)

    success_count = await session.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.campaign_id.in_(user_campaigns_subquery),
            MessageLog.status == "success"
        )
    ) or 0

    failed_count = await session.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.campaign_id.in_(user_campaigns_subquery),
            MessageLog.status == "failed"
        )
    ) or 0

    return {
        "targets_count": t_count or 0,
        "active_campaigns": active_c_count or 0,
        "total_campaigns": total_c_count or 0,
        "success_messages": success_count,
        "failed_messages": failed_count,
        "total_messages": success_count + failed_count,
    }


async def generate_user_report_csv(session: AsyncSession, user_id: int, campaign_id: Optional[int] = None) -> str:
    """
    Generate CSV file of message logs with utf-8-sig encoding for Arabic support.
    Returns path to created temporary file.
    """
    os.makedirs("exports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"exports/report_user_{user_id}_{timestamp}.csv" if not campaign_id else f"exports/report_camp_{campaign_id}_{timestamp}.csv"

    query = (
        select(MessageLog, Campaign.name)
        .join(Campaign, MessageLog.campaign_id == Campaign.id)
        .where(Campaign.owner_id == user_id)
        .order_by(MessageLog.sent_at.desc())
    )
    if campaign_id:
        query = query.where(MessageLog.campaign_id == campaign_id)

    res = await session.execute(query)
    rows = res.all()

    with open(filename, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        # Write headers
        writer.writerow([
            "معرف السجل",
            "رقم الحملة",
            "اسم الحملة",
            "معرف الهدف (Chat ID)",
            "اسم القناة / الجروب",
            "دورة التكرار",
            "حالة الإرسال",
            "سبب الفشل إن وجد",
            "مدة الانتظار (ثواني)",
            "توقيت الإرسال (UTC)",
        ])

        for log_entry, camp_name in rows:
            writer.writerow([
                log_entry.id,
                log_entry.campaign_id,
                camp_name or f"حملة #{log_entry.campaign_id}",
                log_entry.chat_id,
                log_entry.target_title or "",
                log_entry.iteration,
                "نجاح" if log_entry.status == "success" else "فشل",
                log_entry.error_message or "-",
                log_entry.retry_after or 0,
                log_entry.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])

    return filename
