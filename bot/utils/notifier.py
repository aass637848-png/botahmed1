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
    last_error: str | None = None,
) -> None:
    lines = [
        f"🏁 <b>اكتملت حملة الإرسال رقم #{campaign_id}!</b>\n",
        f"✅ الرسائل الناجحة: <b>{success_count}</b>",
        f"❌ الرسائل الفاشلة: <b>{failed_count}</b>",
        f"⏱ مدة التنفيذ: <b>{duration_str}</b>\n",
    ]

    if failed_count > 0 and last_error:
        lines.append(
            f"⚠️ <b>سبب فشل الإرسال من تيليجرام:</b>\n"
            f"<code>{html.escape(last_error)}</code>\n\n"
            f"💡 <i>نصيحة: تأكد من إضافة البوت أو الحساب في الجروب ومنحه صلاحية إرسال الرسائل.</i>"
        )
    else:
        lines.append("📊 يمكنك مراجعة وتصدير تقرير الحملة بصيغة CSV من قسم التقارير.")

    try:
        await bot.send_message(chat_id=user_id, text="\n".join(lines), parse_mode="HTML")
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
