from datetime import datetime

from app.core.enums import DueStatus
from app.database.models import Due, User
from app.database.repositories.dues import DueRepository


class DueService:
    def __init__(self, dues: DueRepository) -> None:
        self.dues = dues

    def create_due(
        self,
        user_id: int,
        title: str,
        amount_irr: int,
        admin: User,
        description: str | None = None,
        deadline_at: datetime | None = None,
    ) -> Due:
        if amount_irr <= 0:
            raise ValueError("Due amount must be positive")
        if not title.strip():
            raise ValueError("Due title is required")
        return self.dues.create(user_id, title.strip(), amount_irr, admin.id, description, deadline_at)

    def list_pending_for_user(self, user: User) -> list[Due]:
        return self.dues.list_for_user(user.id, DueStatus.PENDING)

    def list_for_user(self, user: User) -> list[Due]:
        return self.dues.list_for_user(user.id)
