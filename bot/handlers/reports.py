import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.report_service import get_user_statistics, generate_user_report_csv
from bot.keyboards.inline_menu import get_back_to_menu_keyboard

router = Router(name="reports_router")


def get_reports_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 تصدير سجل الرسائل (CSV)", callback_data="report_export_csv")],
            [InlineKeyboardButton(text="🔄 تحديث الإحصائيات", callback_data="menu_reports")],
            [InlineKeyboardButton(text="🔙 العودة للوحة التحكم", callback_data="menu_main")],
        ]
    )


@router.callback_query(F.data == "menu_reports")
async def cb_reports_dashboard(call: CallbackQuery, session: AsyncSession) -> None:
    """عرض لوحة إحصائيات وتقارير المستخدم"""
    stats = await get_user_statistics(session, call.from_user.id)

    total_msg = stats["total_messages"]
    success_rate = (stats["success_messages"] / total_msg * 100) if total_msg > 0 else 0.0

    text = (
        "📊 <b>لوحة التقارير والإحصائيات</b>\n\n"
        f"🎯 <b>عدد الأهداف المسجلة:</b> {stats['targets_count']}\n"
        f"🚀 <b>إجمالي الحملات المنشأة:</b> {stats['total_campaigns']}\n"
        f"⏳ <b>الحملات الجارية أو المجدولة:</b> {stats['active_campaigns']}\n\n"
        "📈 <b>إحصائيات الإرسال:</b>\n"
        f"• الرسائل الناجحة: <b>{stats['success_messages']}</b> ✅\n"
        f"• الرسائل الفاشلة: <b>{stats['failed_messages']}</b> ❌\n"
        f"• إجمالي الرسائل: <b>{total_msg}</b>\n"
        f"• نسبة النجاح: <b>{success_rate:.1f}%</b>\n\n"
        "💡 يمكنك تحميل ملف CSV مفصل يحتوي على سجل الإرسال لكل هدف وسبب الفشل وأوقات الانتظار بدقة."
    )

    await call.message.edit_text(
        text=text,
        reply_markup=get_reports_menu_keyboard(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "report_export_csv")
async def cb_export_csv(call: CallbackQuery, session: AsyncSession) -> None:
    """تصدير وإرسال ملف تقرير CSV للمستخدم"""
    await call.answer("⏳ جاري إنشاء ملف التقرير...")

    csv_path = await generate_user_report_csv(session, call.from_user.id)

    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        await call.message.answer("⚠️ لا توجد أي بيانات أو سجلات إرسال لتصديرها حالياً.")
        return

    document = FSInputFile(
        path=csv_path,
        filename=os.path.basename(csv_path),
    )

    caption = (
        "📊 <b>تقرير نتائج وإحصائيات الإرسال</b>\n\n"
        "الملف بتنسيق CSV يدعم اللغة العربية بالكامل.\n"
        "يحتوي على: اسم الهدف، المعرف، النتيجة، سبب الفشل، التوقيت، ومدة الانتظار إن وجدت."
    )

    await call.message.answer_document(
        document=document,
        caption=caption,
        parse_mode="HTML",
    )
