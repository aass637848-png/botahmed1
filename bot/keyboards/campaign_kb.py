from typing import List, Set
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.target import Target


def get_target_selection_keyboard(targets: List[Target], selected_ids: Set[int]) -> InlineKeyboardMarkup:
    """أزرار تحديد واختيار الأهداف للحملة"""
    keyboard = []

    for target in targets:
        is_selected = target.id in selected_ids
        mark = "✅" if is_selected else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{mark} {target.title[:25]}",
                callback_data=f"sel_tgt_{target.id}",
            )
        ])

    # Select all / Deselect all
    keyboard.append([
        InlineKeyboardButton(text="☑️ تحديد الكل", callback_data="sel_all_targets"),
        InlineKeyboardButton(text="✖️ إلغاء الكل", callback_data="desel_all_targets"),
    ])

    # Next step
    count = len(selected_ids)
    keyboard.append([
        InlineKeyboardButton(
            text=f"التالي ➡️ ({count} هدف مختار)",
            callback_data="sel_targets_done",
        )
    ])

    keyboard.append([InlineKeyboardButton(text="❌ إلغاء الحملة", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_repeat_presets_keyboard() -> InlineKeyboardMarkup:
    """أزرار خيارات تكرار الرسالة"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 (مرة واحدة)", callback_data="repeat_1"),
                InlineKeyboardButton(text="3 مرات", callback_data="repeat_3"),
            ],
            [
                InlineKeyboardButton(text="5 مرات", callback_data="repeat_5"),
                InlineKeyboardButton(text="10 مرات", callback_data="repeat_10"),
            ],
            [
                InlineKeyboardButton(text="✏️ إدخال عدد مخصص", callback_data="repeat_custom"),
            ],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")],
        ]
    )


def get_interval_presets_keyboard() -> InlineKeyboardMarkup:
    """أزرار الفاصل الزمني بين دورات التكرار"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="بدون فاصل (فوراً)", callback_data="interval_0"),
                InlineKeyboardButton(text="5 دقائق", callback_data="interval_300"),
            ],
            [
                InlineKeyboardButton(text="15 دقيقة", callback_data="interval_900"),
                InlineKeyboardButton(text="1 ساعة", callback_data="interval_3600"),
            ],
            [
                InlineKeyboardButton(text="✏️ إدخال فاصل مخصص (بالدقائق)", callback_data="interval_custom"),
            ],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")],
        ]
    )


def get_delay_presets_keyboard() -> InlineKeyboardMarkup:
    """أزرار تحديد سرعة الإرسال (الفاصل بين كل هدف والتالي)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ سريع (0.5 ثانية)", callback_data="delay_0.5"),
                InlineKeyboardButton(text="🟢 قياسي (1.0 ثانية)", callback_data="delay_1.0"),
            ],
            [
                InlineKeyboardButton(text="🛡 آمن (2.0 ثانية)", callback_data="delay_2.0"),
                InlineKeyboardButton(text="🐢 هادئ (3.0 ثوانٍ)", callback_data="delay_3.0"),
            ],
            [
                InlineKeyboardButton(text="✏️ إدخال سرعة مخصصة", callback_data="delay_custom"),
            ],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")],
        ]
    )


def get_schedule_options_keyboard() -> InlineKeyboardMarkup:
    """أزرار خيارات الجدولة أو الإرسال الفوري"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ إرسال فوري الآن", callback_data="sched_now")],
            [InlineKeyboardButton(text="⏰ جدولة لوقت محدد", callback_data="sched_later")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")],
        ]
    )


def get_sender_choice_keyboard(accounts: list) -> InlineKeyboardMarkup:
    """أزرار اختيار جهة الإرسال (البوت أو حساب عادي متصل)"""
    keyboard = [
        [InlineKeyboardButton(text="🤖 البوت الرسمي (BotFather)", callback_data="sender_type_bot")]
    ]
    for acc in accounts:
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 حساب: {acc.phone}",
                callback_data=f"sender_type_acc_{acc.id}",
            )
        ])
    keyboard.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_campaign_confirm_keyboard() -> InlineKeyboardMarkup:
    """أزرار التأكيد النهائي لإطلاق الحملة"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 تأكيد وإطلاق الحملة", callback_data="campaign_confirm_launch")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="menu_main")],
        ]
    )
