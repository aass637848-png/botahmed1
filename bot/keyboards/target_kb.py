from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.target import Target


def get_targets_menu_keyboard(targets: List[Target]) -> InlineKeyboardMarkup:
    """أزرار واجهة إدارة الأهداف"""
    keyboard = [
        [InlineKeyboardButton(text="➕ إضافة قناة / جروب جديد", callback_data="target_add")],
        [InlineKeyboardButton(text="🔄 تحديث صلاحيات كل الأهداف", callback_data="target_refresh_all")],
    ]

    # Show list of targets with edit/delete options
    for target in targets:
        status_emoji = "✅" if target.can_post_messages else "⚠️"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {target.title[:20]} ({target.chat_type})",
                callback_data=f"target_view_{target.id}",
            ),
            InlineKeyboardButton(
                text="🗑 حذف",
                callback_data=f"target_del_{target.id}",
            ),
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 العودة للوحة التحكم", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_target_detail_keyboard(target_id: int) -> InlineKeyboardMarkup:
    """أزرار معاينة هدف محدد"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 إعادة فحص الصلاحيات", callback_data=f"target_check_{target_id}"),
                InlineKeyboardButton(text="🗑 حذف الهدف", callback_data=f"target_del_{target_id}"),
            ],
            [InlineKeyboardButton(text="🔙 رجوع لقائمة الأهداف", callback_data="menu_targets")],
        ]
    )


def get_cancel_keyboard(back_callback: str = "menu_targets") -> InlineKeyboardMarkup:
    """زر إلغاء العملية والرجوع"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data=back_callback)]
        ]
    )
