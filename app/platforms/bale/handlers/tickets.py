from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session

from app.core import text
from app.database.repositories.tickets import TicketRepository
from app.database.session import engine
from app.platforms.bale.keyboards import ticket_actions_keyboard
from app.platforms.bale.utils import get_current_user
from app.services.tickets import TicketService


async def prompt_ticket_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(text.TICKET_TITLE_PROMPT)
    context.application.bot_data["state"].ticket_title_by_chat[update.effective_chat.id] = ""


async def handle_ticket_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    if chat_id in state.ticket_reply_by_chat:
        ticket_id = state.ticket_reply_by_chat.pop(chat_id)
        user = get_current_user(update, state)
        with Session(engine) as session:
            TicketService(TicketRepository(session)).add_user_message(ticket_id, user, update.message.text)
        await update.effective_message.reply_text("پیام شما ثبت شد.")
        return True
    if chat_id not in state.ticket_title_by_chat:
        return False
    title = state.ticket_title_by_chat[chat_id]
    if not title:
        state.ticket_title_by_chat[chat_id] = update.message.text
        await update.effective_message.reply_text(text.TICKET_MESSAGE_PROMPT)
        return True
    user = get_current_user(update, state)
    with Session(engine) as session:
        ticket = TicketService(TicketRepository(session)).create_ticket(user, title, update.message.text)
    state.ticket_title_by_chat.pop(chat_id, None)
    await update.effective_message.reply_text(f"{text.TICKET_CREATED}\nشماره تیکت: {ticket.id}")
    await notify_admins_of_ticket(context, state, ticket.id, user.id, title)
    return True


async def notify_admins_of_ticket(context: ContextTypes.DEFAULT_TYPE, state, ticket_id: int, user_id: int, title: str) -> None:
    for admin_id in state.settings.admin_telegram_ids:
        try:
            await context.bot.send_message(
                admin_id,
                f"تیکت جدید #{ticket_id}\nکاربر: {user_id}\nعنوان: {title}",
                reply_markup=ticket_actions_keyboard(ticket_id),
            )
        except Exception:
            continue
