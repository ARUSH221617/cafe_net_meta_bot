from app.core.enums import DueStatus, PaymentStatus
from app.database.models import Payment, User
from app.database.repositories.dues import DueRepository
from app.database.repositories.payments import PaymentRepository


class PaymentService:
    def __init__(self, payments: PaymentRepository, dues: DueRepository) -> None:
        self.payments = payments
        self.dues = dues

    def submit_receipt(self, due_id: int, user: User, telegram_file_id: str, caption: str | None = None) -> Payment:
        due = self.dues.get(due_id)
        if due is None:
            raise ValueError("Due not found")
        if due.user_id != user.id:
            raise PermissionError("Due belongs to another user")
        if due.status != DueStatus.PENDING:
            raise ValueError("Due cannot accept payments")
        return self.payments.create_submission(due.id, user.id, due.amount_irr, telegram_file_id, caption)

    def list_for_user(self, user: User) -> list[Payment]:
        return self.payments.list_for_user(user.id)

    def list_submitted(self) -> list[Payment]:
        return self.payments.list_submitted()

    def approve(self, payment_id: int, admin: User) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        reviewed = self.payments.set_review(payment_id, PaymentStatus.APPROVED, admin.id)
        self.dues.set_status(payment.due_id, DueStatus.PAID)
        return reviewed

    def reject(self, payment_id: int, admin: User, note: str | None = None) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        self.dues.set_status(payment.due_id, DueStatus.PENDING)
        return self.payments.set_review(payment_id, PaymentStatus.REJECTED, admin.id, note)
