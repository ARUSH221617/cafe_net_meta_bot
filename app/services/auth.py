from app.core.config import Settings
from app.core.enums import Platform, UserRole, UserStatus
from app.database.models import User
from app.database.repositories.users import UserRepository


def is_env_admin(platform: Platform, platform_user_id: str, settings: Settings) -> bool:
    return (platform == Platform.TELEGRAM and int(platform_user_id) in settings.admin_telegram_ids) or (platform == Platform.BALE and int(platform_user_id) in settings.admin_bale_ids)


def is_admin(user: User, platform: Platform | None = None, platform_user_id: str | None = None, settings: Settings | None = None) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if platform is not None and platform_user_id is not None and settings is not None:
        return is_env_admin(platform, platform_user_id, settings)
    return False


def ensure_active(user: User) -> None:
    if user.status == UserStatus.BANNED:
        raise PermissionError("User is banned")
    if user.status == UserStatus.RESTRICTED:
        raise PermissionError("User is restricted")


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self.users = users
        self.settings = settings

    def sync_platform_user(
        self,
        platform: Platform,
        platform_user_id: str,
        chat_id: str,
        username: str | None,
        display_name: str | None,
    ) -> User:
        return self.users.upsert_platform_user(
            platform=platform,
            platform_user_id=platform_user_id,
            chat_id=chat_id,
            username=username,
            display_name=display_name,
            is_env_admin=is_env_admin(platform, platform_user_id, self.settings),
        )
