from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard(is_admin: bool = True) -> InlineKeyboardMarkup:
    """لوحة التحكم الرئيسية - متاحة للجميع بكامل الصلاحيات"""
    buttons = [
        [
            InlineKeyboardButton(text="🚀 إنشاء حملة إرسال", callback_data="menu_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🎯 إدارة الأهداف", callback_data="menu_targets"),
            InlineKeyboardButton(text="📊 التقارير والإحصائيات", callback_data="menu_reports"),
        ],
        [
            InlineKeyboardButton(text="📡 حالة البوت والصلاحيات", callback_data="menu_status"),
            InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="menu_settings"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """زر الرجوع للرئيسية"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 العودة للوحة التحكم", callback_data="menu_main")]
        ]
    )
