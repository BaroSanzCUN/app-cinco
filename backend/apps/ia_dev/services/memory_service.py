import os
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class SessionMemory:
    messages: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    trim_events: int = 0
    updated_at: float = field(default_factory=time.time)


class SessionMemoryStore:
    _lock = Lock()
    _sessions: dict[str, SessionMemory] = {}
    _max_messages = max(4, int(os.getenv("IA_DEV_MAX_MESSAGES", "20")))

    @classmethod
    def _new_session_id(cls) -> str:
        return uuid.uuid4().hex

    @classmethod
    def get_or_create(cls, session_id: str | None = None) -> tuple[str, SessionMemory]:
        with cls._lock:
            sid = (session_id or "").strip() or cls._new_session_id()
            memory = cls._sessions.get(sid)
            if memory is None:
                memory = SessionMemory()
                cls._sessions[sid] = memory
            memory.updated_at = time.time()
            return sid, memory

    @classmethod
    def append_turn(cls, session_id: str, user_text: str, assistant_text: str):
        with cls._lock:
            memory = cls._sessions.setdefault(session_id, SessionMemory())
            memory.messages.append({"role": "user", "content": user_text})
            memory.messages.append({"role": "assistant", "content": assistant_text})
            overflow = len(memory.messages) - cls._max_messages
            if overflow > 0:
                memory.messages = memory.messages[overflow:]
                memory.trim_events += 1
            memory.updated_at = time.time()

    @classmethod
    def get_recent_messages(cls, session_id: str, limit: int = 8) -> list[dict]:
        with cls._lock:
            memory = cls._sessions.get(session_id)
            if not memory:
                return []
            safe_limit = max(1, min(int(limit), cls._max_messages))
            return [dict(m) for m in memory.messages[-safe_limit:]]

    @classmethod
    def get_context(cls, session_id: str) -> dict:
        with cls._lock:
            memory = cls._sessions.get(session_id)
            if not memory:
                return {}
            return dict(memory.context)

    @classmethod
    def update_context(cls, session_id: str, updates: dict):
        with cls._lock:
            memory = cls._sessions.setdefault(session_id, SessionMemory())
            memory.context.update(dict(updates or {}))
            memory.updated_at = time.time()

    @classmethod
    def reset(cls, session_id: str):
        with cls._lock:
            cls._sessions[session_id] = SessionMemory()

    @classmethod
    def status(cls, session_id: str) -> dict:
        with cls._lock:
            memory = cls._sessions.get(session_id) or SessionMemory()
            used = len(memory.messages)
            ratio = used / cls._max_messages if cls._max_messages else 0
            return {
                "used_messages": used,
                "capacity_messages": cls._max_messages,
                "usage_ratio": round(ratio, 3),
                "trim_events": memory.trim_events,
                "saturated": memory.trim_events > 0 or ratio >= 0.9,
            }
