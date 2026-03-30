import time
import uuid
from dataclasses import dataclass, asdict
from threading import Lock


@dataclass
class Ticket:
    ticket_id: str
    category: str
    title: str
    description: str
    session_id: str | None
    created_at: float


class TicketService:
    _lock = Lock()
    _tickets: dict[str, Ticket] = {}

    @classmethod
    def create_ticket(
        cls,
        *,
        title: str,
        description: str,
        category: str = "general",
        session_id: str | None = None,
    ) -> dict:
        with cls._lock:
            ticket_id = f"IA-{uuid.uuid4().hex[:8].upper()}"
            ticket = Ticket(
                ticket_id=ticket_id,
                category=(category or "general").strip().lower(),
                title=(title or "Solicitud IA DEV").strip(),
                description=(description or "Sin detalle").strip(),
                session_id=(session_id or "").strip() or None,
                created_at=time.time(),
            )
            cls._tickets[ticket_id] = ticket
            payload = asdict(ticket)
            payload["created_at"] = int(ticket.created_at)
            return payload

    @classmethod
    def get_ticket(cls, ticket_id: str) -> dict | None:
        with cls._lock:
            ticket = cls._tickets.get(ticket_id)
            if not ticket:
                return None
            payload = asdict(ticket)
            payload["created_at"] = int(ticket.created_at)
            return payload
