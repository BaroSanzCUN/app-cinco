import json
import os
from typing import Any


class RedisCacheService:
    def __init__(self):
        self.enabled = (os.getenv("IA_DEV_USE_REDIS", "0").strip().lower() in ("1", "true", "yes", "on"))
        self.url = (os.getenv("IA_DEV_REDIS_URL", "") or "").strip()
        self.prefix = (os.getenv("IA_DEV_REDIS_PREFIX", "ia_dev") or "ia_dev").strip()
        self.default_ttl = max(30, int(os.getenv("IA_DEV_REDIS_TTL_SECONDS", "1800")))
        self._client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        if not self.enabled or not self.url:
            self._available = False
            return
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(self.url, decode_responses=True)
            client.ping()
            self._client = client
            self._available = True
        except Exception:
            self._client = None
            self._available = False

    @property
    def is_available(self) -> bool:
        return bool(self._available and self._client is not None)

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get_json(self, key: str, default: Any = None):
        if not self.is_available:
            return default
        try:
            raw = self._client.get(self._key(key))  # type: ignore[union-attr]
            if raw is None:
                return default
            return json.loads(raw)
        except Exception:
            return default

    def set_json(self, key: str, value: Any, *, ttl_seconds: int | None = None):
        if not self.is_available:
            return False
        try:
            ttl = int(ttl_seconds or self.default_ttl)
            self._client.setex(self._key(key), ttl, json.dumps(value, ensure_ascii=False))  # type: ignore[union-attr]
            return True
        except Exception:
            return False

    def delete(self, key: str):
        if not self.is_available:
            return False
        try:
            self._client.delete(self._key(key))  # type: ignore[union-attr]
            return True
        except Exception:
            return False
