from telegram import Update
from telegram.ext import ContextTypes

from app.platforms.bale.handlers.admin import handle_admin_callback, handle_payment_callback, handle_ticket_callback
from app.platforms.bale.handlers.dues import start_payment
from app.platforms.bale.handlers.github import handle_github_callback
from app.platforms.bale.handlers.search_youtube import handle_youtube_callback


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    parts = query.data.split(":")
    namespace = parts[0]
    if namespace == "pay" and parts[1] == "start":
        await start_payment(update, context, int(parts[2]))
        await query.answer()
        return
    if namespace == "pay" and await handle_payment_callback(update, context, parts):
        return
    if namespace == "admin" and await handle_admin_callback(update, context, parts):
        return
    if namespace == "tickets" and await handle_ticket_callback(update, context, parts):
        return
    if namespace == "github" and await handle_github_callback(update, context, parts):
        return
    if namespace == "yt" and await handle_youtube_callback(update, context, parts):
        return
    await query.answer("درخواست نامعتبر است.", show_alert=True)
