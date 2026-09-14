import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.account import Account
from bot.services.userbot_service import (
    start_phone_login,
    verify_login_code,
    verify_2fa_password,
)
from bot.keyboards.inline_menu import get_back_to_menu_keyboard

router = Router(name="accounts_router")


class AccountLoginStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()


def get_accounts_menu_keyboard(accounts: list[Account]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ ربط حساب تيليجرام جديد (يوزر)", callback_data="account_add_prompt")]
    ]
    for acc in accounts:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {acc.first_name} ({acc.phone})",
                callback_data=f"account_view_{acc.id}",
            ),
            InlineKeyboardButton(
                text="🗑 حذف",
                callback_data=f"account_del_{acc.id}",
            ),
        ])
    buttons.append([InlineKeyboardButton(text="🔙 العودة للوحة التحكم", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "menu_accounts")
async def cb_accounts_menu(call: CallbackQuery, session: AsyncSession) -> None:
    """عرض قائمة الحسابات المتصلة المشتركة"""
    stmt = select(Account).where(Account.is_active == True)
    res = await session.execute(stmt)
    accounts = res.scalars().all()

    text = (
        "📱 <b>الحسابات المتصلة (Sender Userbots)</b>\n\n"
        f"عدد الحسابات المتاحة حاليًا: <b>{len(accounts)}</b>\n\n"
        "💡 <b>ملاحظة:</b> أي حساب تقوم أنت أو صديقك بربطه هنا يصبح متاحًا للجميع لاستخدامه في إرسال الحملات كبديل للبوت الرسمي."
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_accounts_menu_keyboard(accounts),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "account_add_prompt")
async def cb_add_account_prompt(call: CallbackQuery, state: FSMContext) -> None:
    """بدء خطوات ربط حساب جديد"""
    await state.set_state(AccountLoginStates.waiting_for_phone)
    text = (
        "📱 <b>ربط حساب تيليجرام جديد</b>\n\n"
        "أرسل الآن رقم الهاتف الخاص بالحساب مع مفتاح الدولة الدولي.\n"
        "مثال: <code>+201012345678</code> أو <code>+966512345678</code>\n\n"
        "⚠️ سيصلك كود تسجيل الدخول في تطبيق تيليجرام على هذا الرقم."
    )
    await call.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AccountLoginStates.waiting_for_phone)
async def process_account_phone(message: Message, state: FSMContext) -> None:
    """إرسال كود التحقق لرقم الهاتف"""
    phone = message.text or ""
    wait_msg = await message.answer("⏳ جاري الاتصال بتيليجرام وإرسال كود التحقق...")

    success, msg = await start_phone_login(message.from_user.id, phone)
    if not success:
        await wait_msg.edit_text(
            text=f"❌ {msg}\n\nيرجى التأكد من صحة الرقم ومحاولة الإرسال مجددًا أو الضغط على رجوع:",
            reply_markup=get_back_to_menu_keyboard(),
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(AccountLoginStates.waiting_for_code)

    await wait_msg.edit_text(
        text=f"📨 <b>تم إرسال كود التحقق إلى حسابك في تيليجرام!</b>\n\n"
             f"الرقم: <code>{phone}</code>\n"
             f"أرسل الآن الكود المكون من 5 أرقام كما وصلك (مثال: <code>12345</code>):",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(AccountLoginStates.waiting_for_code)
async def process_account_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """التحقق من الكود المدخل"""
    code = (message.text or "").strip()
    data = await state.get_data()
    phone = data.get("phone", "")

    wait_msg = await message.answer("⏳ جاري التحقق وتسجيل الدخول...")
    success, needs_2fa, session_str, msg = await verify_login_code(message.from_user.id, code)

    if needs_2fa:
        await state.set_state(AccountLoginStates.waiting_for_2fa)
        await wait_msg.edit_text(
            text="🔐 <b>الحساب محمي بكلمة سر التحقق بخطوتين (2FA)</b>\n\n"
                 "يرجى إرسال كلمة السر الخاصة بالحساب الآن لإتمام تسجيل الدخول:",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    if not success or not session_str:
        await wait_msg.edit_text(
            text=f"❌ {msg}\n\nأعد المحاولة أو اضغط رجوع:",
            reply_markup=get_back_to_menu_keyboard(),
        )
        return

    # Save account to DB
    account = Account(
        phone=phone,
        session_string=session_str,
        first_name="حساب متصل",
        added_by=message.from_user.id,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await state.clear()

    await wait_msg.edit_text(
        text=f"✅ <b>تم ربط الحساب بنجاح!</b>\n\n"
             f"الرقم: <code>{phone}</code>\n"
             f"أصبح الحساب الآن متاحًا لك ولأصدقائك لاستخدامه في إرسال الحملات مباشرة من لوحة التحكم.",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(AccountLoginStates.waiting_for_2fa)
async def process_account_2fa(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """التحقق من كلمة سر 2FA"""
    password = (message.text or "").strip()
    data = await state.get_data()
    phone = data.get("phone", "")

    wait_msg = await message.answer("⏳ جاري التحقق من كلمة السر...")
    success, session_str, msg = await verify_2fa_password(message.from_user.id, password)

    if not success or not session_str:
        await wait_msg.edit_text(
            text=f"❌ {msg}\n\nأعد المحاولة أو اضغط رجوع:",
            reply_markup=get_back_to_menu_keyboard(),
        )
        return

    account = Account(
        phone=phone,
        session_string=session_str,
        first_name="حساب متصل",
        added_by=message.from_user.id,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await state.clear()

    await wait_msg.edit_text(
        text=f"✅ <b>تم ربط الحساب وتجاوز 2FA بنجاح!</b>\n\n"
             f"الرقم: <code>{phone}</code>\n"
             f"أصبح الحساب متاحًا الآن للجميع في لوحة التحكم.",
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("account_del_"))
async def cb_delete_account(call: CallbackQuery, session: AsyncSession) -> None:
    """حذف أو فصل حساب متصل"""
    acc_id = int(call.data.split("_")[2])
    acc = await session.get(Account, acc_id)
    if acc:
        await session.delete(acc)
        await session.commit()
        await call.answer("🗑 تم فصل الحساب بنجاح.", show_alert=True)
    else:
        await call.answer("الحساب غير موجود.", show_alert=True)
    await cb_accounts_menu(call, session)
