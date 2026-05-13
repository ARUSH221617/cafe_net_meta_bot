from telegram import Update
from telegram.ext import ContextTypes
from sqlmodel import Session

from app.core import text
from app.core.enums import PaymentStatus
from app.database.repositories.dues import DueRepository
from app.database.repositories.payments import PaymentRepository
from app.database.session import engine
from app.platforms.telegram.keyboards import due_actions_keyboard
from app.platforms.telegram.utils import get_current_user
from app.services.dues import DueService
from app.services.payments import PaymentService
from app.utils.money import format_irr


async def show_dues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.application.bot_data["state"]
    user = get_current_user(update, state)
    with Session(engine) as session:
        dues = DueService(DueRepository(session)).list_pending_for_user(user)
    if not dues:
        await update.effective_message.reply_text(text.NO_DUES)
        return
    for due in dues:
        body = f"#{due.id} - {due.title}\nمبلغ: {format_irr(due.amount_irr)}\nوضعیت: {due.status.value}"
        await update.effective_message.reply_text(body, reply_markup=due_actions_keyboard(due.id))


async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, due_id: int) -> None:
    context.application.bot_data["state"].payment_due_by_chat[update.effective_chat.id] = due_id
    await update.effective_message.reply_text(text.UPLOAD_RECEIPT)


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    due_id = state.payment_due_by_chat.get(chat_id)
    if due_id is None:
        return False
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    if file_id is None:
        await update.effective_message.reply_text(text.UPLOAD_RECEIPT)
        return True
    user = get_current_user(update, state)
    with Session(engine) as session:
        payment = PaymentService(PaymentRepository(session), DueRepository(session)).submit_receipt(
            due_id, user, file_id, update.message.caption
        )
    state.payment_due_by_chat.pop(chat_id, None)
    await update.effective_message.reply_text(text.PAYMENT_SUBMITTED)
    await notify_admins(context, state, f"رسید جدید #{payment.id}\nکاربر: {user.id}\nمبلغ: {format_irr(payment.amount_irr)}", payment.id)
    return True


async def notify_admins(context: ContextTypes.DEFAULT_TYPE, state, message: str, payment_id: int) -> None:
    from app.platforms.telegram.keyboards import payment_review_keyboard

    for admin_id in state.settings.admin_telegram_ids:
        try:
            await context.bot.send_message(admin_id, message, reply_markup=payment_review_keyboard(payment_id))
        except Exception:
            continue


async def show_payment_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = context.application.bot_data["state"]
    user = get_current_user(update, state)
    with Session(engine) as session:
        payments = PaymentService(PaymentRepository(session), DueRepository(session)).list_for_user(user)
    if not payments:
        await update.effective_message.reply_text(text.NO_PAYMENTS)
        return
    lines = []
    for payment in payments[:10]:
        status = {
            PaymentStatus.SUBMITTED: "در انتظار بررسی",
            PaymentStatus.APPROVED: "تأیید شده",
            PaymentStatus.REJECTED: "رد شده",
        }[payment.status]
        lines.append(f"#{payment.id} - {format_irr(payment.amount_irr)} - {status}")
    await update.effective_message.reply_text("\n".join(lines))
