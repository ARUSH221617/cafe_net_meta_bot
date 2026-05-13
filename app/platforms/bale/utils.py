from telegram import Update

from app.core.enums import Platform
from app.database.session import engine
from app.database.repositories.users import UserRepository
from app.services.auth import AuthService
from app.platforms.bale.context import RuntimeState
from sqlmodel import Session


def bale_display_name(update: Update) -> str | None:
    user = update.effective_user
    if user is None:
        return None
    return " ".join(part for part in [user.first_name, user.last_name] if part) or None


def get_current_user(update: Update, state: RuntimeState):
    if update.effective_user is None or update.effective_chat is None:
        raise ValueError("Missing Bale user or chat")
    with Session(engine) as session:
        service = AuthService(UserRepository(session), state.settings)
        return service.sync_platform_user(
            Platform.BALE,
            str(update.effective_user.id),
            str(update.effective_chat.id),
            update.effective_user.username,
            bale_display_name(update),
        )
