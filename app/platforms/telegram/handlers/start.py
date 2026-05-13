from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session

from app.core import text
from app.core.enums import UserStatus
from app.database.repositories.users import UserRepository
from app.database.session import engine
from app.platforms.telegram.context import RuntimeState
from app.platforms.telegram.keyboards import contact_keyboard, main_menu_keyboard
from app.platforms.telegram.utils import get_current_user
from app.services.users import UserService


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state: RuntimeState = context.application.bot_data["state"]
    user = get_current_user(update, state)
    if user.status == UserStatus.BANNED:
        await update.effective_message.reply_text(text.BANNED)
        return
    with Session(engine) as session:
        registered = UserService(UserRepository(session)).is_registered(user)
    if not registered:
        await update.effective_message.reply_text(f"{text.WELCOME}\n{text.REQUEST_CONTACT}", reply_markup=contact_keyboard())
        return
    await update.effective_message.reply_text(text.MAIN_MENU, reply_markup=main_menu_keyboard())
