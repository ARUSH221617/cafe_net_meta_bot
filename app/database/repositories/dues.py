from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import DueStatus
from app.database.models import Due


class DueRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, due_id: int) -> Due | None:
        return self.session.get(Due, due_id)

    def create(self, user_id: int, title: str, amount_irr: int, admin_id: int, description: str | None = None, deadline_at=None) -> Due:
        due = Due(
            user_id=user_id,
            title=title,
            description=description,
            amount_irr=amount_irr,
            deadline_at=deadline_at,
            created_by_admin_id=admin_id,
        )
        self.session.add(due)
        self.session.commit()
        self.session.refresh(due)
        return due

    def list_for_user(self, user_id: int, status: DueStatus | None = None) -> list[Due]:
        statement = select(Due).where(Due.user_id == user_id)
        if status is not None:
            statement = statement.where(Due.status == status)
        return list(self.session.exec(statement.order_by(Due.created_at.desc())).all())

    def list_pending(self) -> list[Due]:
        return list(self.session.exec(select(Due).where(Due.status == DueStatus.PENDING)).all())

    def set_status(self, due_id: int, status: DueStatus) -> Due:
        due = self.session.get(Due, due_id)
        if due is None:
            raise ValueError("Due not found")
        due.status = status
        due.updated_at = datetime.now(timezone.utc)
        self.session.add(due)
        self.session.commit()
        self.session.refresh(due)
        return due
