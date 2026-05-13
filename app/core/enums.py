from enum import Enum


class Platform(str, Enum):
    TELEGRAM = "telegram"
    BALE = "bale"


class UserStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"
    RESTRICTED = "restricted"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class DueStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class PaymentStatus(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class RunMode(str, Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"
