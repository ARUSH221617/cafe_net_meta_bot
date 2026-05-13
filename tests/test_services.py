from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings
from app.core.enums import DueStatus, PaymentStatus, Platform, TicketStatus, UserRole
from app.database.repositories.dues import DueRepository
from app.database.repositories.payments import PaymentRepository
from app.database.repositories.tickets import TicketRepository
from app.database.repositories.users import UserRepository
from app.services.auth import AuthService, is_admin
from app.services.dues import DueService
from app.services.payments import PaymentService
from app.services.tickets import TicketService


def make_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_register_user_without_username_uses_platform_identity() -> None:
    with make_session() as session:
        settings = Settings(telegram_bot_token="token", admin_telegram_ids=[])
        user = AuthService(UserRepository(session), settings).sync_platform_user(
            Platform.TELEGRAM, "42", "42", None, "Test User"
        )
        assert user.identity_key == "telegram:42"
        assert user.username is None


def test_env_admin_is_promoted() -> None:
    with make_session() as session:
        settings = Settings(telegram_bot_token="token", admin_telegram_ids=[42])
        user = AuthService(UserRepository(session), settings).sync_platform_user(
            Platform.TELEGRAM, "42", "42", "admin", "Admin"
        )
        assert user.role == UserRole.ADMIN
        assert is_admin(user)


def test_payment_approval_marks_due_paid() -> None:
    with make_session() as session:
        settings = Settings(telegram_bot_token="token")
        auth = AuthService(UserRepository(session), settings)
        user = auth.sync_platform_user(Platform.TELEGRAM, "1", "1", "user", "User")
        admin = auth.sync_platform_user(Platform.TELEGRAM, "2", "2", "admin", "Admin")
        admin.role = UserRole.ADMIN
        session.add(admin)
        session.commit()
        due_repo = DueRepository(session)
        payment_service = PaymentService(PaymentRepository(session), due_repo)
        due = DueService(due_repo).create_due(user.id, "Internet", 1000, admin)
        payment = payment_service.submit_receipt(due.id, user, "file-id")
        reviewed = payment_service.approve(payment.id, admin)
        assert reviewed.status == PaymentStatus.APPROVED
        assert due_repo.get(due.id).status == DueStatus.PAID


def test_payment_rejection_leaves_due_pending() -> None:
    with make_session() as session:
        settings = Settings(telegram_bot_token="token")
        auth = AuthService(UserRepository(session), settings)
        user = auth.sync_platform_user(Platform.TELEGRAM, "1", "1", "user", "User")
        admin = auth.sync_platform_user(Platform.TELEGRAM, "2", "2", "admin", "Admin")
        due_repo = DueRepository(session)
        payment_service = PaymentService(PaymentRepository(session), due_repo)
        due = DueService(due_repo).create_due(user.id, "Internet", 1000, admin)
        payment = payment_service.submit_receipt(due.id, user, "file-id")
        reviewed = payment_service.reject(payment.id, admin, "bad receipt")
        assert reviewed.status == PaymentStatus.REJECTED
        assert due_repo.get(due.id).status == DueStatus.PENDING


def test_ticket_lifecycle() -> None:
    with make_session() as session:
        settings = Settings(telegram_bot_token="token")
        user = AuthService(UserRepository(session), settings).sync_platform_user(
            Platform.TELEGRAM, "1", "1", "user", "User"
        )
        service = TicketService(TicketRepository(session))
        ticket = service.create_ticket(user, "Help", "Need support")
        assert ticket.status == TicketStatus.OPEN
        service.add_user_message(ticket.id, user, "More info")
        closed = service.close(ticket.id)
        assert closed.status == TicketStatus.CLOSED
        assert closed.closed_at is not None
