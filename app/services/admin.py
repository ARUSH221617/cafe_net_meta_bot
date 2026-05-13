from app.core.enums import Platform
from app.database.models import User
from app.services.auth import is_admin
from app.core.config import Settings


class AdminService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_admin(self, user: User, platform: Platform, platform_user_id: str) -> None:
        if not is_admin(user, platform, platform_user_id, self.settings):
            raise PermissionError("Admin access required")
