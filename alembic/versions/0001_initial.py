"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identity_key", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "BANNED", "RESTRICTED", name="userstatus"), nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_identity_key"), "user", ["identity_key"], unique=True)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=False)
    op.create_table(
        "due",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("amount_irr", sa.Integer(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "PAID", "CANCELLED", "OVERDUE", name="duestatus"), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_due_created_by_admin_id"), "due", ["created_by_admin_id"], unique=False)
    op.create_index(op.f("ix_due_status"), "due", ["status"], unique=False)
    op.create_index(op.f("ix_due_user_id"), "due", ["user_id"], unique=False)
    op.create_table(
        "phone_number",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "phone_number"),
    )
    op.create_index(op.f("ix_phone_number_phone_number"), "phone_number", ["phone_number"], unique=False)
    op.create_index(op.f("ix_phone_number_user_id"), "phone_number", ["user_id"], unique=False)
    op.create_table(
        "platform_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.Enum("TELEGRAM", "BALE", name="platform"), nullable=False),
        sa.Column("platform_user_id", sa.String(), nullable=False),
        sa.Column("chat_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "platform_user_id"),
    )
    op.create_index(op.f("ix_platform_account_chat_id"), "platform_account", ["chat_id"], unique=False)
    op.create_index(op.f("ix_platform_account_platform"), "platform_account", ["platform"], unique=False)
    op.create_index(op.f("ix_platform_account_platform_user_id"), "platform_account", ["platform_user_id"], unique=False)
    op.create_index(op.f("ix_platform_account_user_id"), "platform_account", ["user_id"], unique=False)
    op.create_table(
        "ticket",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "PENDING", "IN_PROGRESS", "CLOSED", name="ticketstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_status"), "ticket", ["status"], unique=False)
    op.create_index(op.f("ix_ticket_user_id"), "ticket", ["user_id"], unique=False)
    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("due_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount_irr", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("SUBMITTED", "APPROVED", "REJECTED", name="paymentstatus"), nullable=False),
        sa.Column("telegram_file_id", sa.String(), nullable=False),
        sa.Column("receipt_caption", sa.String(), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("admin_note", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["due_id"], ["due.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_admin_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_due_id"), "payment", ["due_id"], unique=False)
    op.create_index(op.f("ix_payment_status"), "payment", ["status"], unique=False)
    op.create_index(op.f("ix_payment_user_id"), "payment", ["user_id"], unique=False)
    op.create_table(
        "ticket_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("is_admin_message", sa.Boolean(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["ticket.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_message_sender_user_id"), "ticket_message", ["sender_user_id"], unique=False)
    op.create_index(op.f("ix_ticket_message_ticket_id"), "ticket_message", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_table("ticket_message")
    op.drop_table("payment")
    op.drop_table("ticket")
    op.drop_table("platform_account")
    op.drop_table("phone_number")
    op.drop_table("due")
    op.drop_table("user")
