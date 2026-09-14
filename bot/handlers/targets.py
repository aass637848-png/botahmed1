import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.target import Target
from bot.utils.states import TargetStates
from bot.utils.validators import validate_target_identifier
from bot.services.target_service import inspect_target, add_or_update_target, refresh_user_targets
from bot.keyboards.target_kb import (
    get_targets_menu_keyboard,
    get_target_detail_keyboard,
    get_cancel_keyboard,
)

router = Router(name="targets_router")


@router.callback_query(F.data == "menu_targets")
async def cb_list_targets(call: CallbackQuery, session: AsyncSession) -> None:
    """عرض قائمة الأهداف المشتركة"""
    stmt = select(Target).where(Target.is_active == True)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    text = (
        "🎯 <b>إدارة الأهداف المشتركة (القنوات والمجموعات)</b>\n\n"
        f"إجمالي الأهداف المسجلة: <b>{len(targets)}</b>\n\n"
        "💡 كافة الأهداف هنا مشتركة ويمكنك أنت وصديقك إطلاق الحملات إليها:"
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_targets_menu_keyboard(targets),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "target_add")
async def cb_add_target_prompt(call: CallbackQuery, state: FSMContext) -> None:
    """بدء إضافة هدف جديد"""
    await state.set_state(TargetStates.waiting_for_identifier)
    text = (
        "➕ <b>إضافة هدف جديد (قناة أو جروب)</b>\n\n"
        "أرسل الآن معرف الهدف:\n"
        "1. اسم المستخدم مثل: <code>@my_channel</code>\n"
        "2. أو المعرف الرقمي مثل: <code>-1001234567890</code>\n"
        "3. أو رابط القناة/الجروب مثل: <code>https://t.me/my_channel</code>\n\n"
        "أو اضغط إلغاء:"
    )
    await call.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(TargetStates.waiting_for_identifier)
async def process_target_identifier(message: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """معالجة معرف الهدف وإضافته مباشرة بدون قيود"""
    raw_input = message.text or ""
    is_valid, cleaned, err = validate_target_identifier(raw_input)

    if not is_valid:
        await message.answer(
            text=f"⚠️ {err}\n\nيرجى إعادة المحاولة أو الضغط على إلغاء:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    wait_msg = await message.answer("⏳ جاري إضافة الهدف...")
    success, info, status_msg = await inspect_target(bot, cleaned)

    target, is_new = await add_or_update_target(session, message.from_user.id, info)
    await state.clear()

    action_word = "إضافة" if is_new else "تحديث"

    result_text = (
        f"✅ <b>تم {action_word} الهدف بنجاح!</b>\n\n"
        f"🏷 <b>الاسم:</b> {html.escape(target.title)}\n"
        f"🆔 <b>المعرف:</b> <code>{target.chat_id}</code>\n"
        f"👤 <b>اليوزر:</b> {target.username or 'غير متاح'}\n"
        f"📂 <b>النوع:</b> {target.chat_type}\n"
        f"📊 <b>الحالة:</b> {target.status_description}\n"
    )

    await wait_msg.edit_text(
        text=result_text,
        reply_markup=get_target_detail_keyboard(target.id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("target_view_"))
async def cb_view_target(call: CallbackQuery, session: AsyncSession) -> None:
    """معاينة تفاصيل هدف محدد"""
    target_id = int(call.data.split("_")[2])
    stmt = select(Target).where(Target.id == target_id)
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if not target:
        await call.answer("❌ الهدف غير موجود!", show_alert=True)
        return

    text = (
        f"🎯 <b>تفاصيل الهدف</b>\n\n"
        f"🏷 <b>الاسم:</b> {html.escape(target.title)}\n"
        f"🆔 <b>المعرف:</b> <code>{target.chat_id}</code>\n"
        f"👤 <b>اليوزر:</b> {target.username or 'غير متاح'}\n"
        f"📂 <b>النوع:</b> {target.chat_type}\n"
        f"📊 <b>الحالة:</b> {target.status_description}\n"
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_target_detail_keyboard(target.id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("target_check_"))
async def cb_recheck_target(call: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    """تحديث هدف محدد"""
    target_id = int(call.data.split("_")[2])
    stmt = select(Target).where(Target.id == target_id)
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if not target:
        await call.answer("❌ الهدف غير موجود!", show_alert=True)
        return

    target.can_post_messages = True
    target.status_description = "جاهز للإرسال ✅"
    await session.commit()
    await call.answer("✅ الهدف جاهز للإرسال!", show_alert=True)
    await cb_view_target(call, session)


@router.callback_query(F.data.startswith("target_del_"))
async def cb_delete_target(call: CallbackQuery, session: AsyncSession) -> None:
    """حذف هدف من قائمة المستخدم"""
    target_id = int(call.data.split("_")[2])
    stmt = select(Target).where(Target.id == target_id)
    res = await session.execute(stmt)
    target = res.scalar_one_or_none()

    if target:
        await session.delete(target)
        await session.commit()
        await call.answer("🗑 تم حذف الهدف بنجاح.", show_alert=True)
    else:
        await call.answer("❌ الهدف غير موجود مسبقًا.", show_alert=True)

    await cb_list_targets(call, session)


@router.callback_query(F.data == "target_refresh_all")
async def cb_refresh_all_targets(call: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    """تحديث كافة الأهداف"""
    await call.answer("🔄 تم تحديث كافة الأهداف!")
    await refresh_user_targets(bot, session, call.from_user.id)
    await cb_list_targets(call, session)
