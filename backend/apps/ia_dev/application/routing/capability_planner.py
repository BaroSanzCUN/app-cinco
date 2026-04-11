from __future__ import annotations

import os
from typing import Any

from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog
from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)


class CapabilityPlanner:
    def __init__(
        self,
        *,
        catalog: CapabilityCatalog | None = None,
        bridge: IntentToCapabilityBridge | None = None,
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()

    def plan_from_legacy(
        self,
        *,
        message: str,
        classification: dict[str, Any],
    ) -> dict[str, Any]:
        mapped = self.bridge.resolve(message=message, classification=classification)
        capability_id = str(mapped.get("capability_id") or "legacy.passthrough.v1")
        definition = self.catalog.get(capability_id)
        rollout_enabled = self._rollout_enabled(definition)
        dictionary_hints = self._dictionary_hints(classification.get("dictionary_context"))

        return {
            "capability_id": capability_id,
            "capability_exists": bool(definition),
            "rollout_enabled": rollout_enabled,
            "handler_key": definition.handler_key if definition else "legacy.passthrough",
            "policy_tags": list(definition.policy_tags) if definition else [],
            "legacy_intents": list(definition.legacy_intents) if definition else [],
            "reason": str(mapped.get("reason") or "unspecified"),
            "source": {
                "intent": str(mapped.get("source_intent") or ""),
                "domain": str(mapped.get("source_domain") or ""),
                "output_mode": str(mapped.get("output_mode") or "summary"),
                "needs_database": bool(mapped.get("needs_database")),
            },
            "dictionary_hints": dictionary_hints,
        }

    @staticmethod
    def _rollout_enabled(definition) -> bool:
        if not definition or not definition.rollout_flag:
            return True
        value = os.getenv(str(definition.rollout_flag), "1").strip().lower()
        return value in {"1", "true", "yes", "on"}

    @staticmethod
    def _dictionary_hints(raw_context: Any) -> dict[str, Any]:
        context = raw_context if isinstance(raw_context, dict) else {}
        tables = context.get("tables") if isinstance(context.get("tables"), list) else []
        fields = context.get("fields") if isinstance(context.get("fields"), list) else []
        relations = (
            context.get("relations")
            if isinstance(context.get("relations"), list)
            else []
        )
        domain = context.get("domain") if isinstance(context.get("domain"), dict) else {}
        return {
            "domain_code": str(domain.get("code") or ""),
            "table_count": len(tables),
            "field_count": len(fields),
            "relation_count": len(relations),
            "table_names": [
                str(item.get("table_name") or "")
                for item in tables[:8]
                if isinstance(item, dict) and item.get("table_name")
            ],
        }
