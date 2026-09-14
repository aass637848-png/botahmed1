from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import settings
from bot.keyboards.inline_menu import get_main_menu_keyboard
from bot.models.user import User

router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User) -> None:
    """معالج أمر البدء /start"""
    await state.clear()
    is_admin = settings.is_admin(message.from_user.id) or (db_user and db_user.is_admin)

    welcome_text = (
        f"👋 مرحبًا بك <b>{message.from_user.first_name}</b> في لوحة تحكم بوت الإرسال والجدولة!\n\n"
        "⚡ <b>الميزات المتاحة:</b>\n"
        "• إرسال نصوص، صور، فيديوهات، وملفات لكافة القنوات والجروبات.\n"
        "• فحص صلاحيات البوت تلقائيًا في كل قناة/جروب.\n"
        "• إمكانية التكرار وتحديد الفواصل الزمنية وسرعة الإرسال.\n"
        "• جدولة الحملات لتبدأ في وقت محدد.\n"
        "• تقارير تفصيلية وتصديرها بصيغة CSV.\n\n"
        "اختر من القائمة أدناه للبدء:"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu_main")
async def cb_main_menu(call: CallbackQuery, state: FSMContext, db_user: User) -> None:
    """الرجوع للوحة التحكم الرئيسية"""
    await state.clear()
    is_admin = settings.is_admin(call.from_user.id) or (db_user and db_user.is_admin)

    text = (
        "🎛 <b>لوحة التحكم الرئيسية</b>\n\n"
        "يرجى اختيار القسم الذي ترغب بإدارته:"
    )

    try:
        await call.message.edit_text(
            text=text,
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="HTML",
        )
    except Exception:
        await call.message.answer(
            text=text,
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="HTML",
        )
    await call.answer()
