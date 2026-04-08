import time
import uuid

from .sql_store import IADevSqlStore


class TicketService:
    _store = IADevSqlStore()

    @classmethod
    def create_ticket(
        cls,
        *,
        title: str,
        description: str,
        category: str = "general",
        session_id: str | None = None,
    ) -> dict:
        ticket_id = f"IA-{uuid.uuid4().hex[:8].upper()}"
        created_at = int(time.time())
        payload = {
            "ticket_id": ticket_id,
            "category": (category or "general").strip().lower(),
            "title": (title or "Solicitud IA DEV").strip(),
            "description": (description or "Sin detalle").strip(),
            "session_id": (session_id or "").strip() or None,
            "created_at": created_at,
        }
        cls._store.insert_ticket(**payload)
        return payload

    @classmethod
    def get_ticket(cls, ticket_id: str) -> dict | None:
        clean_id = (ticket_id or "").strip()
        if not clean_id:
            return None
        return cls._store.get_ticket(clean_id)
