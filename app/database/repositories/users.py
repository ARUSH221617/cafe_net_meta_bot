from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import Platform, UserRole, UserStatus
from app.database.models import PhoneNumber, PlatformAccount, User


def normalize_phone_number(phone_number: str) -> str:
    return "".join(phone_number.strip().split())

class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_identity_key(self, identity_key: str) -> User | None:
        return self.session.exec(select(User).where(User.identity_key == identity_key)).first()

    def get_by_username(self, username: str) -> User | None:
        return self.session.exec(select(User).where(User.username == username)).first()

    def list_users(self, offset: int = 0, limit: int = 50) -> list[User]:
        return list(self.session.exec(select(User).offset(offset).limit(limit)).all())

    def upsert_platform_user(
        self,
        platform: Platform,
        platform_user_id: str,
        chat_id: str,
        username: str | None,
        display_name: str | None,
        is_env_admin: bool = False,
    ) -> User:
        identity_key = f"{platform.value}:{platform_user_id}"
        user = self.get_by_identity_key(identity_key)
        now = datetime.now(timezone.utc)
        if user is None:
            user = User(
                identity_key=identity_key,
                username=username,
                display_name=display_name,
                role=UserRole.ADMIN if is_env_admin else UserRole.USER,
                last_activity_at=now,
            )
            self.session.add(user)
            self.session.flush()
        else:
            user.username = username
            user.display_name = display_name
            user.last_activity_at = now
            if is_env_admin:
                user.role = UserRole.ADMIN
            self.session.add(user)
            self.session.flush()

        account = self.session.exec(
            select(PlatformAccount).where(
                PlatformAccount.platform == platform,
                PlatformAccount.platform_user_id == platform_user_id,
            )
        ).first()
        if account is None:
            account = PlatformAccount(
                user_id=user.id,
                platform=platform,
                platform_user_id=platform_user_id,
                chat_id=chat_id,
                username=username,
            )
        else:
            account.chat_id = chat_id
            account.username = username
            account.updated_at = now
        self.session.add(account)
        self.session.commit()
        self.session.refresh(user)
        return user

    def add_phone_number(self, user_id: int, phone_number: str) -> PhoneNumber:
        normalized = normalize_phone_number(phone_number)
        existing = self.session.exec(
            select(PhoneNumber).where(PhoneNumber.user_id == user_id, PhoneNumber.phone_number == normalized)
        ).first()
        if existing is not None:
            return existing
        has_phone = self.session.exec(select(PhoneNumber).where(PhoneNumber.user_id == user_id)).first() is not None
        phone = PhoneNumber(user_id=user_id, phone_number=normalized, is_primary=not has_phone)
        self.session.add(phone)
        self.session.commit()
        self.session.refresh(phone)
        return phone

    def has_phone_number(self, user_id: int) -> bool:
        return self.session.exec(select(PhoneNumber).where(PhoneNumber.user_id == user_id)).first() is not None

    def set_status(self, user_id: int, status: UserStatus) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.status = status
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
