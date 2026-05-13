from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session

from app.core import text
from app.database.repositories.users import UserRepository
from app.database.session import engine
from app.platforms.telegram.keyboards import contact_keyboard, main_menu_keyboard
from app.platforms.telegram.utils import get_current_user
from app.services.users import UserService


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.contact is None:
        await update.effective_message.reply_text(text.REQUEST_CONTACT, reply_markup=contact_keyboard())
        return
    state = context.application.bot_data["state"]
    user = get_current_user(update, state)
    contact = update.message.contact
    if contact.user_id and update.effective_user and contact.user_id != update.effective_user.id:
        await update.effective_message.reply_text("لطفاً شماره موبایل خودتان را ارسال کنید.", reply_markup=contact_keyboard())
        return
    with Session(engine) as session:
        UserService(UserRepository(session)).add_phone(user, contact.phone_number)
    await update.effective_message.reply_text(text.REGISTRATION_SUCCESS, reply_markup=main_menu_keyboard())
