from __future__ import annotations

from pathlib import Path
from typing import Any


class PolicyLoader:
    def __init__(self, *, base_dir: str | Path | None = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[2] / "POLICIES"
        self.base_dir = Path(base_dir)

    def load(self, policy_name: str) -> dict[str, Any]:
        path = self.base_dir / policy_name
        if not path.exists():
            return {}
        content = path.read_text(encoding="utf-8", errors="ignore")
        parsed = self._parse_yaml_if_available(content)
        if isinstance(parsed, dict):
            return parsed
        return {}

    @staticmethod
    def _parse_yaml_if_available(raw: str) -> dict[str, Any] | None:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(raw)
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            # Fallback safe: no yaml dependency required for runtime.
            return None
