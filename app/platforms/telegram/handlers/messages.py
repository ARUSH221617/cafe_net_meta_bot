from telegram import Update
from telegram.ext import ContextTypes

from app.platforms.telegram.handlers.admin import handle_admin_text
from app.platforms.telegram.handlers.dues import handle_receipt
from app.platforms.telegram.handlers.search import handle_github_query
from app.platforms.telegram.handlers.tickets import handle_ticket_text
from app.platforms.telegram.handlers.user_menu import handle_menu_text


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    if await handle_receipt(update, context):
        return
    if update.message.text and await handle_admin_text(update, context):
        return
    if update.message.text and await handle_ticket_text(update, context):
        return
    if update.message.text and await handle_github_query(update, context):
        return
    if update.message.text:
        await handle_menu_text(update, context)
