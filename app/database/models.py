from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.enums import DueStatus, PaymentStatus, Platform, TicketStatus, UserRole, UserStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: int | None = Field(default=None, primary_key=True)
    identity_key: str = Field(index=True, unique=True)
    username: str | None = Field(default=None, index=True)
    display_name: str | None = None
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    registered_at: datetime = Field(default_factory=utc_now)
    last_activity_at: datetime | None = None

    platform_accounts: list["PlatformAccount"] = Relationship(back_populates="user")
    phone_numbers: list["PhoneNumber"] = Relationship(back_populates="user")


class PlatformAccount(SQLModel, table=True):
    __tablename__ = "platform_account"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    platform: Platform = Field(index=True)
    platform_user_id: str = Field(index=True)
    chat_id: str = Field(index=True)
    username: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    user: User = Relationship(back_populates="platform_accounts")


class PhoneNumber(SQLModel, table=True):
    __tablename__ = "phone_number"
    __table_args__ = (UniqueConstraint("user_id", "phone_number"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    phone_number: str = Field(index=True)
    is_primary: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    user: User = Relationship(back_populates="phone_numbers")


class Due(SQLModel, table=True):
    __tablename__ = "due"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    description: str | None = None
    amount_irr: int = Field(gt=0)
    deadline_at: datetime | None = None
    status: DueStatus = Field(default=DueStatus.PENDING, index=True)
    created_by_admin_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    
    id: int | None = Field(default=None, primary_key=True)
    due_id: int = Field(foreign_key="due.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount_irr: int = Field(gt=0)
    status: PaymentStatus = Field(default=PaymentStatus.SUBMITTED, index=True)
    telegram_file_id: str
    receipt_caption: str | None = None
    reviewed_by_admin_id: int | None = Field(default=None, foreign_key="user.id")
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    admin_note: str | None = None


class Ticket(SQLModel, table=True):
    __tablename__ = "ticket"
    
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    status: TicketStatus = Field(default=TicketStatus.OPEN, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    closed_at: datetime | None = None


class TicketMessage(SQLModel, table=True):
    __tablename__ = "ticket_message"
    
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    sender_user_id: int = Field(foreign_key="user.id", index=True)
    is_admin_message: bool = Field(default=False)
    body: str
    created_at: datetime = Field(default_factory=utc_now)
