from app.core.enums import UserStatus
from app.database.models import PhoneNumber, User
from app.database.repositories.users import UserRepository


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def add_phone(self, user: User, phone_number: str) -> PhoneNumber:
        return self.users.add_phone_number(user.id, phone_number)

    def is_registered(self, user: User) -> bool:
        return self.users.has_phone_number(user.id)

    def list_users(self, page: int = 1, page_size: int = 5) -> list[User]:
        return self.users.list_users(offset=(page - 1) * page_size, limit=page_size)

    def set_status(self, user_id: int, status: UserStatus) -> User:
        return self.users.set_status(user_id, status)
