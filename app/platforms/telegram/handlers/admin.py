from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session

from app.core import text
from app.core.enums import Platform, PaymentStatus, TicketStatus, UserStatus
from app.database.repositories.dues import DueRepository
from app.database.repositories.payments import PaymentRepository
from app.database.repositories.tickets import TicketRepository
from app.database.repositories.users import UserRepository
from app.database.session import engine
from app.platforms.telegram.keyboards import admin_menu_keyboard, ticket_actions_keyboard
from app.platforms.telegram.utils import get_current_user
from app.services.admin import AdminService
from app.services.dues import DueService
from app.services.payments import PaymentService
from app.services.tickets import TicketService
from app.services.users import UserService
from app.utils.money import format_irr


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.application.bot_data["state"]
    user = get_current_user(update, state)
    try:
        AdminService(state.settings).ensure_admin(user, Platform.TELEGRAM, str(update.effective_user.id))
    except PermissionError:
        await update.effective_message.reply_text(text.NOT_ADMIN)
        return
    await update.effective_message.reply_text(text.ADMIN_MENU, reply_markup=admin_menu_keyboard())


async def ensure_admin_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.application.bot_data["state"]
    user = get_current_user(update, state)
    AdminService(state.settings).ensure_admin(user, Platform.TELEGRAM, str(update.effective_user.id))
    return user


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    query = update.callback_query
    if query is None:
        return False
    try:
        admin = await ensure_admin_update(update, context)
    except PermissionError:
        await query.answer(text.NOT_ADMIN, show_alert=True)
        return True
    action = parts[1]
    with Session(engine) as session:
        if action == "users":
            users = UserService(UserRepository(session)).list_users(int(parts[2]))
            body = "\n".join(f"#{item.id} @{item.username or '-'} {item.status.value}" for item in users) or "کاربری یافت نشد."
            await query.edit_message_text(body)
        elif action == "payments":
            payments = PaymentService(PaymentRepository(session), DueRepository(session)).list_submitted()
            body = "\n".join(f"#{item.id} user:{item.user_id} {format_irr(item.amount_irr)}" for item in payments) or "پرداختی در انتظار بررسی نیست."
            await query.edit_message_text(body)
        elif action == "tickets":
            tickets = TicketService(TicketRepository(session)).list_all()[:10]
            if not tickets:
                await query.edit_message_text("تیکتی یافت نشد.")
            else:
                await query.edit_message_text("\n".join(f"#{item.id} user:{item.user_id} {item.status.value} - {item.title}" for item in tickets))
        elif action == "ticket" and parts[2] == "reply":
            context.application.bot_data["state"].admin_ticket_reply_by_chat[update.effective_chat.id] = int(parts[3])
            await query.edit_message_text("پاسخ مدیر را ارسال کنید.")
        elif action == "due" and parts[2] == "new":
            await query.edit_message_text("برای ایجاد بدهی از دستور زیر استفاده کنید:\n/admin_due USER_ID AMOUNT_IRR TITLE")
        else:
            return False
    await query.answer()
    return True


async def admin_due_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.application.bot_data["state"]
    admin = get_current_user(update, state)
    try:
        AdminService(state.settings).ensure_admin(admin, Platform.TELEGRAM, str(update.effective_user.id))
    except PermissionError:
        await update.effective_message.reply_text(text.NOT_ADMIN)
        return
    if len(context.args) < 3:
        await update.effective_message.reply_text("فرمت: /admin_due USER_ID AMOUNT_IRR TITLE")
        return
    user_id = int(context.args[0])
    amount = int(context.args[1])
    title = " ".join(context.args[2:])
    with Session(engine) as session:
        due = DueService(DueRepository(session)).create_due(user_id, title, amount, admin)
    await update.effective_message.reply_text(f"بدهی #{due.id} ثبت شد.")


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    if chat_id not in state.admin_ticket_reply_by_chat:
        return False
    ticket_id = state.admin_ticket_reply_by_chat.pop(chat_id)
    admin = get_current_user(update, state)
    with Session(engine) as session:
        TicketService(TicketRepository(session)).add_admin_message(ticket_id, admin, update.message.text)
    await update.effective_message.reply_text("پاسخ مدیر ثبت شد.")
    return True


async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    query = update.callback_query
    if query is None:
        return False
    try:
        admin = await ensure_admin_update(update, context)
    except PermissionError:
        await query.answer(text.NOT_ADMIN, show_alert=True)
        return True
    payment_id = int(parts[2])
    with Session(engine) as session:
        service = PaymentService(PaymentRepository(session), DueRepository(session))
        if parts[1] == "approve":
            payment = service.approve(payment_id, admin)
            await query.edit_message_text(f"پرداخت #{payment.id} تأیید شد.")
        elif parts[1] == "reject":
            payment = service.reject(payment_id, admin)
            await query.edit_message_text(f"پرداخت #{payment.id} رد شد.")
        else:
            return False
    await query.answer()
    return True


async def handle_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    query = update.callback_query
    if query is None or parts[1] != "close":
        return False
    await ensure_admin_update(update, context)
    with Session(engine) as session:
        TicketService(TicketRepository(session)).close(int(parts[2]))
    await query.edit_message_text(text.TICKET_CLOSED)
    await query.answer()
    return True
