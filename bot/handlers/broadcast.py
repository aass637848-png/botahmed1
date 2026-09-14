import asyncio
import html
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.target import Target
from bot.models.campaign import Campaign
from bot.utils.states import BroadcastStates
from bot.utils.validators import (
    validate_positive_int,
    validate_float_range,
    parse_schedule_datetime,
)
from bot.keyboards.inline_menu import get_back_to_menu_keyboard
from bot.keyboards.campaign_kb import (
    get_target_selection_keyboard,
    get_repeat_presets_keyboard,
    get_interval_presets_keyboard,
    get_delay_presets_keyboard,
    get_schedule_options_keyboard,
    get_campaign_confirm_keyboard,
)
from bot.services.broadcast_worker import execute_campaign, is_any_target_locked
from bot.services.scheduler_service import schedule_campaign
from config import settings

router = Router(name="broadcast_router")


@router.callback_query(F.data == "menu_broadcast")
async def cb_start_broadcast_wizard(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """بدء معالج إنشاء حملة إرسال"""
    # Check if user has targets
    stmt = select(Target).where(Target.owner_id == call.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    if not targets:
        await call.message.edit_text(
            text="⚠️ <b>ليس لديك أي أهداف مضافة بعد!</b>\n\n"
                 "يرجى إضافة القنوات أو المجموعات أولاً من قسم <b>إدارة الأهداف</b> قبل إنشاء الحملة.",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    await state.clear()
    await state.set_state(BroadcastStates.waiting_for_content)
    text = (
        "✍️ <b>الخطوة 1: إعداد محتوى الرسالة</b>\n\n"
        "أرسل الآن الرسالة التي ترغب بنشرها:\n"
        "• <b>نص عادي:</b> (يدعم التنسيقات HTML / Markdown)\n"
        "• <b>صورة:</b> (مع كابشن اختياري)\n"
        "• <b>فيديو:</b> (مع كابشن اختياري)\n"
        "• <b>ملف / مستند:</b> (مع كابشن اختياري)\n\n"
        "أو اضغط على زر العودة للإلغاء:"
    )
    await call.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(BroadcastStates.waiting_for_content)
async def process_content_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """معالجة استلام محتوى الرسالة وتخزينه"""
    content_type = "text"
    text_content = None
    file_id = None

    if message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
        text_content = message.caption
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        text_content = message.caption
    elif message.document:
        content_type = "document"
        file_id = message.document.file_id
        text_content = message.caption
    elif message.text:
        content_type = "text"
        text_content = message.text
    else:
        await message.answer("⚠️ نوع المحتوى غير مدعوم. يرجى إرسال نص، صورة، فيديو، أو ملف.")
        return

    # Fetch user's active targets
    stmt = select(Target).where(Target.owner_id == message.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    target_ids = [t.id for t in targets]

    # Save to state
    await state.update_data(
        content_type=content_type,
        text_content=text_content,
        file_id=file_id,
        selected_target_ids=target_ids,  # Selected all by default
    )
    await state.set_state(BroadcastStates.selecting_targets)

    summary_type = {
        "text": "نص",
        "photo": "صورة",
        "video": "فيديو",
        "document": "ملف",
    }.get(content_type, content_type)

    text = (
        f"✅ <b>تم حفظ المحتوى بنجاح!</b> ({summary_type})\n\n"
        "🎯 <b>الخطوة 2: اختيار الأهداف</b>\n"
        "حدد القنوات والجروبات التي ترغب بالإرسال إليها عبر الضغط على اسمها (تم تحديد الكل افتراضياً):"
    )

    await message.answer(
        text=text,
        reply_markup=get_target_selection_keyboard(targets, set(target_ids)),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.selecting_targets, F.data.startswith("sel_tgt_"))
async def cb_toggle_target(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """تبديل تحديد الهدف"""
    target_id = int(call.data.split("_")[2])
    data = await state.get_data()
    selected_ids = set(data.get("selected_target_ids", []))

    if target_id in selected_ids:
        selected_ids.remove(target_id)
    else:
        selected_ids.add(target_id)

    await state.update_data(selected_target_ids=list(selected_ids))

    stmt = select(Target).where(Target.owner_id == call.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    await call.message.edit_reply_markup(
        reply_markup=get_target_selection_keyboard(targets, selected_ids)
    )
    await call.answer()


@router.callback_query(BroadcastStates.selecting_targets, F.data == "sel_all_targets")
async def cb_select_all_targets(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """تحديد كل الأهداف"""
    stmt = select(Target).where(Target.owner_id == call.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    all_ids = [t.id for t in targets]
    await state.update_data(selected_target_ids=all_ids)

    await call.message.edit_reply_markup(
        reply_markup=get_target_selection_keyboard(targets, set(all_ids))
    )
    await call.answer("تم تحديد الكل ✅")


@router.callback_query(BroadcastStates.selecting_targets, F.data == "desel_all_targets")
async def cb_deselect_all_targets(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """إلغاء تحديد كل الأهداف"""
    stmt = select(Target).where(Target.owner_id == call.from_user.id)
    res = await session.execute(stmt)
    targets = res.scalars().all()

    await state.update_data(selected_target_ids=[])

    await call.message.edit_reply_markup(
        reply_markup=get_target_selection_keyboard(targets, set())
    )
    await call.answer("تم إلغاء التحديد ✖️")


@router.callback_query(BroadcastStates.selecting_targets, F.data == "sel_targets_done")
async def cb_targets_done(call: CallbackQuery, state: FSMContext) -> None:
    """إتمام اختيار الأهداف والانتقال لخيارات التكرار"""
    data = await state.get_data()
    selected_ids = data.get("selected_target_ids", [])

    if not selected_ids:
        await call.answer("⚠️ يرجى تحديد هدف واحد على الأقل للمتابعة!", show_alert=True)
        return

    await state.set_state(BroadcastStates.waiting_for_repeat)
    text = (
        f"🎯 <b>تم اختيار {len(selected_ids)} هدف.</b>\n\n"
        "🔁 <b>الخطوة 3: عدد مرات التكرار</b>\n"
        "كم مرة ترغب في إرسال الرسالة إلى هذه الأهداف؟"
    )
    await call.message.edit_text(
        text=text,
        reply_markup=get_repeat_presets_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(BroadcastStates.waiting_for_repeat, F.data.startswith("repeat_"))
async def cb_repeat_preset(call: CallbackQuery, state: FSMContext) -> None:
    """معالجة اختيار أزرار التكرار الجاهزة"""
    val = call.data.split("_")[1]
    if val == "custom":
        await call.message.edit_text(
            "✏️ أرسل الآن عدد مرات التكرار كرقم صحيح (مثال: 7):",
            reply_markup=get_back_to_menu_keyboard(),
        )
        await call.answer()
        return

    repeat_count = int(val)
    await state.update_data(repeat_count=repeat_count)
    await call.answer()
    await proceed_after_repeat(call.message, state, repeat_count)


@router.message(BroadcastStates.waiting_for_repeat)
async def process_repeat_custom(message: Message, state: FSMContext) -> None:
    """معالجة إدخال عدد تكرار مخصص"""
    is_valid, val, err = validate_positive_int(message.text or "", min_val=1, max_val=500)
    if not is_valid:
        await message.answer(f"⚠️ {err}\nأعد المحاولة أو اضغط إلغاء:", reply_markup=get_back_to_menu_keyboard())
        return

    await state.update_data(repeat_count=val)
    await proceed_after_repeat(message, state, val)


async def proceed_after_repeat(message_or_call_msg: Message, state: FSMContext, repeat_count: int) -> None:
    """الانتقال للفاصل الزمني إذا كان التكرار > 1 أو مباشرة للسرعة"""
    if repeat_count > 1:
        await state.set_state(BroadcastStates.waiting_for_interval)
        text = (
            f"🔁 عدد التكرار المحدد: <b>{repeat_count} مرات</b>\n\n"
            "⏱ <b>الخطوة 4: الفاصل الزمني بين كل تكرار والآخر</b>\n"
            "حدد المدة الزمنية التي ينتظرها البوت قبل إرسال الدورة التالية:"
        )
        await message_or_call_msg.answer(
            text=text,
            reply_markup=get_interval_presets_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Repeat is 1, interval is 0
        await state.update_data(interval_seconds=0)
        await ask_delay_between_targets(message_or_call_msg, state)


@router.callback_query(BroadcastStates.waiting_for_interval, F.data.startswith("interval_"))
async def cb_interval_preset(call: CallbackQuery, state: FSMContext) -> None:
    """معالجة أزرار الفاصل الزمني للتكرار"""
    val = call.data.split("_")[1]
    if val == "custom":
        await call.message.edit_text(
            "✏️ أرسل الفاصل الزمني بالدقائق (مثال: 45):",
            reply_markup=get_back_to_menu_keyboard(),
        )
        await call.answer()
        return

    interval_sec = int(val)
    await state.update_data(interval_seconds=interval_sec)
    await call.answer()
    await ask_delay_between_targets(call.message, state)


@router.message(BroadcastStates.waiting_for_interval)
async def process_interval_custom(message: Message, state: FSMContext) -> None:
    """معالجة إدخال فاصل زمني مخصص بالدقائق"""
    is_valid, minutes, err = validate_positive_int(message.text or "", min_val=1, max_val=10080)
    if not is_valid:
        await message.answer(f"⚠️ {err}\nأعد المحاولة:", reply_markup=get_back_to_menu_keyboard())
        return

    await state.update_data(interval_seconds=minutes * 60)
    await ask_delay_between_targets(message, state)


async def ask_delay_between_targets(msg: Message, state: FSMContext) -> None:
    """سؤال المستخدم عن سرعة الإرسال (الفاصل بين كل هدف والتالي)"""
    await state.set_state(BroadcastStates.waiting_for_delay)
    text = (
        "⚡ <b>الخطوة 5: سرعة الإرسال (معدل التدفق)</b>\n\n"
        "حدد الفاصل الزمني بالثواني بين كل هدف والآخر لتجنب الحظر والسبام:"
    )
    await msg.answer(
        text=text,
        reply_markup=get_delay_presets_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.waiting_for_delay, F.data.startswith("delay_"))
async def cb_delay_preset(call: CallbackQuery, state: FSMContext) -> None:
    """معالجة اختيار سرعة الإرسال الجاهزة"""
    val = call.data.split("_")[1]
    if val == "custom":
        await call.message.edit_text(
            "✏️ أرسل السرعة بالثواني (مثال: 1.5):",
            reply_markup=get_back_to_menu_keyboard(),
        )
        await call.answer()
        return

    delay = float(val)
    await state.update_data(delay_between_targets=delay)
    await call.answer()
    await ask_schedule_options(call.message, state)


@router.message(BroadcastStates.waiting_for_delay)
async def process_delay_custom(message: Message, state: FSMContext) -> None:
    """معالجة سرعة مخصصة"""
    is_valid, val, err = validate_float_range(message.text or "", min_val=0.1, max_val=30.0)
    if not is_valid:
        await message.answer(f"⚠️ {err}\nأعد المحاولة:", reply_markup=get_back_to_menu_keyboard())
        return

    await state.update_data(delay_between_targets=val)
    await ask_schedule_options(message, state)


async def ask_schedule_options(msg: Message, state: FSMContext) -> None:
    """عرض خيارات الجدولة أو الإرسال الفوري"""
    await state.set_state(BroadcastStates.waiting_for_schedule)
    text = (
        "⏰ <b>الخطوة 6: وقت بدء الحملة</b>\n\n"
        "هل ترغب في إطلاق الحملة فورًا، أم جدولتها لوقت لاحق؟"
    )
    await msg.answer(
        text=text,
        reply_markup=get_schedule_options_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.waiting_for_schedule, F.data == "sched_now")
async def cb_sched_now(call: CallbackQuery, state: FSMContext) -> None:
    """اختيار الإرسال الفوري"""
    await state.update_data(scheduled_at=None)
    await call.answer()
    await show_campaign_confirmation(call.message, state)


@router.callback_query(BroadcastStates.waiting_for_schedule, F.data == "sched_later")
async def cb_sched_later_prompt(call: CallbackQuery) -> None:
    """طلب إدخال وقت وتاريخ الجدولة"""
    text = (
        "⏰ <b>إدخال موعد الجدولة</b>\n\n"
        "أرسل وقت البدء بإحدى الصيغ التالية:\n"
        "• توقيت اليوم أو الغد: <code>18:30</code>\n"
        "• تاريخ ووقت محدد: <code>2026-10-25 14:00</code>\n\n"
        f"<i>المنطقة الزمنية المعتمدة: {settings.DEFAULT_TIMEZONE}</i>"
    )
    await call.message.edit_text(text=text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
    await call.answer()


@router.message(BroadcastStates.waiting_for_schedule)
async def process_schedule_time(message: Message, state: FSMContext) -> None:
    """التحقق من وقت الجدولة"""
    is_valid, dt_utc, err = parse_schedule_datetime(message.text or "", settings.DEFAULT_TIMEZONE)
    if not is_valid:
        await message.answer(f"⚠️ {err}\nأعد المحاولة:", reply_markup=get_back_to_menu_keyboard())
        return

    await state.update_data(scheduled_at=dt_utc.isoformat())
    await show_campaign_confirmation(message, state)


async def show_campaign_confirmation(msg: Message, state: FSMContext) -> None:
    """عرض المراجعة النهائية للحملة قبل التأكيد"""
    data = await state.get_data()
    await state.set_state(BroadcastStates.confirming)

    c_type = data.get("content_type", "text")
    tgt_count = len(data.get("selected_target_ids", []))
    rep_count = data.get("repeat_count", 1)
    interval = data.get("interval_seconds", 0)
    delay = data.get("delay_between_targets", 1.5)
    sched = data.get("scheduled_at")

    sched_str = "فوري الآن ⚡" if not sched else f"{sched} (UTC) ⏰"
    interval_str = "بدون فاصل" if interval == 0 else f"{interval // 60} دقيقة"

    summary = (
        "📋 <b>المراجعة النهائية للحملة:</b>\n\n"
        f"📦 <b>نوع المحتوى:</b> {c_type}\n"
        f"🎯 <b>عدد الأهداف المختارة:</b> {tgt_count}\n"
        f"🔁 <b>مرات التكرار:</b> {rep_count}\n"
        f"⏱ <b>الفاصل بين التكرار:</b> {interval_str}\n"
        f"⚡ <b>السرعة بين الأهداف:</b> {delay} ثانية\n"
        f"⏰ <b>موعد الإطلاق:</b> {sched_str}\n\n"
        "هل أنت متأكد من بدء تشغيل هذه الحملة؟"
    )

    await msg.answer(
        text=summary,
        reply_markup=get_campaign_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.confirming, F.data == "campaign_confirm_launch")
async def cb_confirm_and_launch(call: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """حفظ الحملة وإطلاقها أو جدولتها"""
    data = await state.get_data()
    selected_target_ids = data.get("selected_target_ids", [])

    if not selected_target_ids:
        await call.answer("خطأ: لم يتم اختيار أهداف!", show_alert=True)
        return

    # Check target locks
    stmt = select(Target).where(Target.id.in_(selected_target_ids))
    res = await session.execute(stmt)
    targets = res.scalars().all()
    chat_ids = [t.chat_id for t in targets]

    if await is_any_target_locked(chat_ids):
        await call.answer(
            "⚠️ تعذر الإطلاق الآن: أحد الأهداف المختارة مشغول حالياً بحملة أخرى جارية!",
            show_alert=True,
        )
        return

    sched_iso = data.get("scheduled_at")
    sched_dt = datetime.fromisoformat(sched_iso) if sched_iso else None
    initial_status = "scheduled" if sched_dt else "pending"

    campaign = Campaign(
        owner_id=call.from_user.id,
        name=f"حملة {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        content_type=data.get("content_type", "text"),
        text_content=data.get("text_content"),
        file_id=data.get("file_id"),
        target_ids=selected_target_ids,
        repeat_count=data.get("repeat_count", 1),
        current_iteration=0,
        interval_seconds=data.get("interval_seconds", 0),
        delay_between_targets=data.get("delay_between_targets", 1.5),
        scheduled_at=sched_dt,
        status=initial_status,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)

    await state.clear()

    if sched_dt:
        schedule_campaign(bot, campaign.id, sched_dt)
        await call.message.edit_text(
            text=f"⏰ <b>تمت جدولة الحملة رقم #{campaign.id} بنجاح!</b>\n\n"
                 f"سيتم إطلاق الحملة تلقائيًا في الموعد المحدد: <code>{sched_iso}</code>.",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Launch immediate async background task
        asyncio.create_task(execute_campaign(bot, campaign.id))
        await call.message.edit_text(
            text=f"🚀 <b>تم إطلاق الحملة رقم #{campaign.id} بنجاح!</b>\n\n"
                 "يتم الآن الإرسال في الخلفية وفق السرعة المحددة، وستصلك إشعارات وتحديثات الحملة فور انتهائها.",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    await call.answer()
