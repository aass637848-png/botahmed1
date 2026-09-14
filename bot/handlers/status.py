import html
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.target import Target
from bot.keyboards.inline_menu import get_back_to_menu_keyboard

router = Router(name="status_router")


@router.callback_query(F.data == "menu_status")
async def cb_bot_status(call: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    """عرض معلومات getMe وصلاحيات البوت في كل هدف والتحذيرات"""
    bot_info = await bot.get_me()

    stmt = select(Target).where(Target.owner_id == call.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    total_targets = len(targets)
    healthy_targets = sum(1 for t in targets if t.can_post_messages)
    problem_targets = total_targets - healthy_targets

    lines = [
        "📡 <b>حالة البوت وصلاحيات الأهداف</b>\n",
        f"🤖 <b>اسم البوت:</b> {html.escape(bot_info.first_name)}",
        f"🆔 <b>معرف البوت (ID):</b> <code>{bot_info.id}</code>",
        f"👤 <b>يوزر البوت:</b> @{bot_info.username}",
        f"🌐 <b>يدعم الانضمام للمجموعات:</b> {'نعم' if bot_info.can_join_groups else 'لا'}\n",
        f"📊 <b>إجمالي الأهداف المسجلة:</b> {total_targets}",
        f"✅ <b>أهداف صالحة للنشر:</b> {healthy_targets}",
        f"⚠️ <b>أهداف بها قيود/مشاكل:</b> {problem_targets}\n",
        "📋 <b>تفاصيل أهدافك:</b>",
    ]

    if not targets:
        lines.append("<i>لا توجد أهداف مسجلة لديك حاليًا. يمكنك إضافة أهداف من لوحة الأهداف.</i>")
    else:
        for t in targets[:15]:  # Limit display to first 15 to avoid message size limits
            icon = "✅" if t.can_post_messages else "⚠️"
            warn_msg = f" - <i>({t.status_description})</i>" if not t.can_post_messages else ""
            lines.append(f"{icon} <b>{html.escape(t.title[:20])}</b> ({t.chat_type}){warn_msg}")

        if total_targets > 15:
            lines.append(f"\n<i>... وهناك {total_targets - 15} أهداف أخرى.</i>")

    if problem_targets > 0:
        lines.append(
            "\n⚠️ <b>تحذير:</b> لديك أهداف لا يمتلك البوت فيها صلاحية نشر الرسائل! "
            "يرجى التأكد من رفع البوت مشرفًا فيها وإعطائه الصلاحيات."
        )

    await call.message.edit_text(
        text="\n".join(lines),
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()
