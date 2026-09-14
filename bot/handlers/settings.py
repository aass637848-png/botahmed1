from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.setting import Setting
from bot.models.user import User
from bot.utils.states import SettingsStates
from bot.utils.validators import validate_float_range
from bot.keyboards.inline_menu import get_back_to_menu_keyboard
from config import settings

router = Router(name="settings_router")


def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ تعديل السرعة الافتراضية", callback_data="settings_change_delay")],
            [InlineKeyboardButton(text="🔙 العودة للوحة التحكم", callback_data="menu_main")],
        ]
    )


@router.callback_query(F.data == "menu_settings")
async def cb_settings(call: CallbackQuery, session: AsyncSession) -> None:
    """عرض إعدادات البوت للمستخدم"""
    # Check if custom delay is set
    stmt = select(Setting).where(Setting.user_id == call.from_user.id, Setting.key == "default_delay")
    res = await session.execute(stmt)
    custom_delay = res.scalar_one_or_none()

    current_delay = float(custom_delay.value) if custom_delay else settings.DEFAULT_DELAY_BETWEEN_TARGETS

    text = (
        "⚙️ <b>إعدادات البوت والتحكم</b>\n\n"
        f"🌍 <b>المنطقة الزمنية:</b> <code>{settings.DEFAULT_TIMEZONE}</code>\n"
        f"⚡ <b>الفاصل الزمني الافتراضي بين الأهداف:</b> <code>{current_delay}</code> ثانية\n"
        f"🛡 <b>أقصى محاولات عند الخطأ:</b> <code>{settings.MAX_RETRY_ATTEMPTS}</code>\n\n"
        "يمكنك ضبط سرعة الإرسال الافتراضية عبر الزر أدناه:"
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "settings_change_delay")
async def cb_change_delay(call: CallbackQuery, state: FSMContext) -> None:
    """طلب إدخال السرعة الافتراضية"""
    await state.set_state(SettingsStates.waiting_for_default_delay)
    await call.message.edit_text(
        text="⚡ <b>تعديل السرعة الافتراضية للإرسال</b>\n\n"
             "أرسل الفاصل الزمني الجديد بالثواني بين كل هدف والآخر (مثال: <code>1.5</code> أو <code>2.0</code>):",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(SettingsStates.waiting_for_default_delay)
async def process_new_delay(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """حفظ السرعة الافتراضية الجديدة"""
    is_valid, val, err = validate_float_range(message.text or "", min_val=0.1, max_val=30.0)
    if not is_valid:
        await message.answer(f"⚠️ {err}\nأعد المحاولة:", reply_markup=get_back_to_menu_keyboard())
        return

    stmt = select(Setting).where(Setting.user_id == message.from_user.id, Setting.key == "default_delay")
    res = await session.execute(stmt)
    setting_row = res.scalar_one_or_none()

    if not setting_row:
        setting_row = Setting(
            user_id=message.from_user.id,
            key="default_delay",
            value=str(val),
            description="Default delay between targets in seconds",
        )
        session.add(setting_row)
    else:
        setting_row.value = str(val)

    await session.commit()
    await state.clear()

    await message.answer(
        text=f"✅ <b>تم تحديث السرعة الافتراضية بنجاح إلى:</b> <code>{val}</code> ثانية.",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu_admin_stats")
async def cb_admin_stats(call: CallbackQuery, session: AsyncSession) -> None:
    """لوحة إحصائيات المشرف العام للنظام بالكامل"""
    from sqlalchemy import func
    from bot.models.campaign import Campaign
    from bot.models.message_log import MessageLog
    from bot.models.target import Target

    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_targets = await session.scalar(select(func.count(Target.id))) or 0
    total_campaigns = await session.scalar(select(func.count(Campaign.id))) or 0
    total_logs = await session.scalar(select(func.count(MessageLog.id))) or 0

    text = (
        "👑 <b>لوحة المشرف العام (إحصائيات النظام الشاملة)</b>\n\n"
        f"👥 <b>إجمالي المستخدمين المسجلين:</b> {total_users}\n"
        f"🎯 <b>إجمالي الأهداف في النظام:</b> {total_targets}\n"
        f"🚀 <b>إجمالي الحملات التي تم إنشاؤها:</b> {total_campaigns}\n"
        f"📨 <b>إجمالي عمليات الإرسال المنفذة:</b> {total_logs}\n\n"
        "<i>هذه البيانات مجمعة على مستوى كامل النظام.</i>"
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()
