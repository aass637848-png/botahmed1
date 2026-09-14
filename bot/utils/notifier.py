import html
from aiogram import Bot


async def notify_campaign_started(bot: Bot, user_id: int, campaign_id: int, total_targets: int, repeat_count: int) -> None:
    text = (
        f"🚀 <b>بدأت حملة الإرسال رقم #{campaign_id}</b>\n\n"
        f"🎯 عدد الأهداف: <b>{total_targets}</b>\n"
        f"🔁 عدد مرات التكرار: <b>{repeat_count}</b>\n"
        f"⏳ حالة المعالجة: جارية الآن..."
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        pass


async def notify_campaign_finished(
    bot: Bot,
    user_id: int,
    campaign_id: int,
    success_count: int,
    failed_count: int,
    duration_str: str,
) -> None:
    text = (
        f"🏁 <b>اكتملت حملة الإرسال رقم #{campaign_id} بنجاح!</b>\n\n"
        f"✅ الرسائل الناجحة: <b>{success_count}</b>\n"
        f"❌ الرسائل الفاشلة: <b>{failed_count}</b>\n"
        f"⏱ مدة التنفيذ: <b>{duration_str}</b>\n\n"
        f"📊 يمكنك مراجعة وتصدير تقرير الحملة بصيغة CSV من قسم التقارير."
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        pass


async def notify_campaign_error(bot: Bot, user_id: int, campaign_id: int, error_msg: str) -> None:
    text = (
        f"⚠️ <b>تنبيه بخصوص الحملة #{campaign_id}</b>\n\n"
        f"حدث خطأ أثناء تنفيذ الحملة:\n"
        f"<code>{html.escape(error_msg)}</code>"
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        pass
