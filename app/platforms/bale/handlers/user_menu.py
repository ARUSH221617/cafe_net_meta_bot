from telegram import Update
from telegram.ext import ContextTypes

from app.core import text
from app.platforms.bale.handlers.search_youtube import prompt_youtube_search
from app.platforms.telegram.handlers.dues import show_dues, show_payment_history
from app.platforms.telegram.handlers.search import prompt_github_search
from app.platforms.telegram.handlers.tickets import prompt_ticket_title


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return
    message = update.message.text
    if message == "بدهی‌های من":
        await show_dues(update, context)
    elif message == "تاریخچه پرداخت‌ها":
        await show_payment_history(update, context)
    elif message == "ارسال تیکت پشتیبانی":
        await prompt_ticket_title(update, context)
    elif message == "جستجوی GitHub":
        await prompt_github_search(update, context)
    elif message == "جستجوی YouTube":
        await prompt_youtube_search(update, context)
    elif message == "راهنما":
        await update.effective_message.reply_text(
            "از منوی اصلی گزینه مورد نظر را انتخاب کنید."
        )
    else:
        await update.effective_message.reply_text(text.MAIN_MENU)
