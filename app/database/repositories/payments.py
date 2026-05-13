from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import PaymentStatus
from app.database.models import Payment


class PaymentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, payment_id: int) -> Payment | None:
        return self.session.get(Payment, payment_id)

    def create_submission(self, due_id: int, user_id: int, amount_irr: int, telegram_file_id: str, caption: str | None = None) -> Payment:
        payment = Payment(
            due_id=due_id,
            user_id=user_id,
            amount_irr=amount_irr,
            telegram_file_id=telegram_file_id,
            receipt_caption=caption,
        )
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def list_for_user(self, user_id: int) -> list[Payment]:
        return list(self.session.exec(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())).all())

    def list_submitted(self) -> list[Payment]:
        return list(self.session.exec(select(Payment).where(Payment.status == PaymentStatus.SUBMITTED)).all())

    def set_review(self, payment_id: int, status: PaymentStatus, admin_id: int, note: str | None = None) -> Payment:
        payment = self.session.get(Payment, payment_id)
        if payment is None:
            raise ValueError("Payment not found")
        payment.status = status
        payment.reviewed_by_admin_id = admin_id
        payment.reviewed_at = datetime.now(timezone.utc)
        payment.admin_note = note
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment
