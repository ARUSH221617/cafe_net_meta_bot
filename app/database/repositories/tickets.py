from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.enums import TicketStatus
from app.database.models import Ticket, TicketMessage


class TicketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, ticket_id: int) -> Ticket | None:
        return self.session.get(Ticket, ticket_id)

    def create(self, user_id: int, title: str, first_message: str) -> Ticket:
        ticket = Ticket(user_id=user_id, title=title)
        self.session.add(ticket)
        self.session.flush()
        self.session.add(TicketMessage(ticket_id=ticket.id, sender_user_id=user_id, body=first_message))
        self.session.commit()
        self.session.refresh(ticket)
        return ticket

    def add_message(self, ticket_id: int, sender_user_id: int, body: str, is_admin_message: bool = False) -> TicketMessage:
        ticket = self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise ValueError("Ticket not found")
        if ticket.status == TicketStatus.CLOSED:
            raise ValueError("Ticket is closed")
        ticket.updated_at = datetime.now(timezone.utc)
        message = TicketMessage(
            ticket_id=ticket_id,
            sender_user_id=sender_user_id,
            is_admin_message=is_admin_message,
            body=body,
        )
        self.session.add(ticket)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_for_user(self, user_id: int) -> list[Ticket]:
        return list(self.session.exec(select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())).all())

    def list_all(self) -> list[Ticket]:
        return list(self.session.exec(select(Ticket).order_by(Ticket.created_at.desc())).all())

    def list_messages(self, ticket_id: int) -> list[TicketMessage]:
        return list(self.session.exec(select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at)).all())

    def set_status(self, ticket_id: int, status: TicketStatus) -> Ticket:
        ticket = self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise ValueError("Ticket not found")
        ticket.status = status
        ticket.updated_at = datetime.now(timezone.utc)
        if status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.now(timezone.utc)
        self.session.add(ticket)
        self.session.commit()
        self.session.refresh(ticket)
        return ticket
