from app.core.enums import TicketStatus
from app.database.models import Ticket, TicketMessage, User
from app.database.repositories.tickets import TicketRepository


class TicketService:
    def __init__(self, tickets: TicketRepository) -> None:
        self.tickets = tickets

    def create_ticket(self, user: User, title: str, first_message: str) -> Ticket:
        if not title.strip():
            raise ValueError("Ticket title is required")
        if not first_message.strip():
            raise ValueError("Ticket message is required")
        return self.tickets.create(user.id, title.strip(), first_message.strip())

    def add_user_message(self, ticket_id: int, user: User, body: str) -> TicketMessage:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            raise ValueError("Ticket not found")
        if ticket.user_id != user.id:
            raise PermissionError("Ticket belongs to another user")
        return self.tickets.add_message(ticket_id, user.id, body.strip())

    def add_admin_message(self, ticket_id: int, admin: User, body: str) -> TicketMessage:
        self.tickets.set_status(ticket_id, TicketStatus.IN_PROGRESS)
        return self.tickets.add_message(ticket_id, admin.id, body.strip(), is_admin_message=True)

    def list_for_user(self, user: User) -> list[Ticket]:
        return self.tickets.list_for_user(user.id)

    def list_all(self) -> list[Ticket]:
        return self.tickets.list_all()

    def list_messages(self, ticket_id: int) -> list[TicketMessage]:
        return self.tickets.list_messages(ticket_id)

    def close(self, ticket_id: int) -> Ticket:
        return self.tickets.set_status(ticket_id, TicketStatus.CLOSED)
