from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from apps.ia_dev.application.policies.policy_loader import PolicyLoader


@dataclass(frozen=True, slots=True)
class RuntimePolicyDecision:
    action: str
    policy_id: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PolicyRuntime:
    """
    Runtime declarativo para evaluar reglas YAML con fail-safe seguro.
    """

    def __init__(
        self,
        *,
        loader: PolicyLoader | None = None,
        cache_ttl_seconds: int | None = None,
    ):
        self.loader = loader or PolicyLoader()
        self.cache_ttl_seconds = max(
            5,
            int(
                cache_ttl_seconds
                if cache_ttl_seconds is not None
                else os.getenv("IA_DEV_POLICY_RUNTIME_CACHE_SECONDS", "30")
            ),
        )
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def evaluate(
        self,
        *,
        policy_name: str,
        context: dict[str, Any],
        fallback_action: str = "allow",
        fallback_policy_id: str = "policy.runtime.fallback",
        fallback_reason: str = "policy_runtime_fallback",
    ) -> RuntimePolicyDecision:
        policy = self._load_policy(policy_name)
        if not policy:
            return RuntimePolicyDecision(
                action=fallback_action,
                policy_id=fallback_policy_id,
                reason=f"{fallback_reason}:policy_not_found",
                metadata={
                    "policy_name": policy_name,
                    "fallback": True,
                },
            )

        version = str(policy.get("version") or "unknown")
        default_action = str(policy.get("default_action") or fallback_action).strip().lower() or fallback_action
        rules = list(policy.get("rules") or [])
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            when = rule.get("when")
            if when is None:
                when = {k: v for k, v in rule.items() if k not in {"id", "action", "reason", "metadata"}}
            if not isinstance(when, dict):
                continue
            if not self._matches(when=when, context=context):
                continue

            action = str(rule.get("action") or default_action).strip().lower() or default_action
            policy_id = str(rule.get("id") or f"{policy_name}.rule_{idx + 1}")
            reason = str(rule.get("reason") or f"Matched policy rule {policy_id}")
            metadata = dict(rule.get("metadata") or {})
            metadata.update(
                {
                    "policy_name": policy_name,
                    "policy_version": version,
                    "rule_index": idx,
                    "default_action": default_action,
                }
            )
            return RuntimePolicyDecision(
                action=action,
                policy_id=policy_id,
                reason=reason,
                metadata=metadata,
            )

        return RuntimePolicyDecision(
            action=default_action,
            policy_id=f"{policy_name}.default",
            reason=f"No rule matched. Default action={default_action}",
            metadata={
                "policy_name": policy_name,
                "policy_version": version,
                "fallback": False,
            },
        )

    def _load_policy(self, policy_name: str) -> dict[str, Any]:
        now = time.time()
        cached = self._cache.get(policy_name)
        if cached and (now - cached[0]) <= self.cache_ttl_seconds:
            return dict(cached[1])
        data = self.loader.load(policy_name)
        payload = dict(data or {})
        self._cache[policy_name] = (now, payload)
        return payload

    def _matches(self, *, when: dict[str, Any], context: dict[str, Any]) -> bool:
        for key, expected in when.items():
            if key == "all":
                if not isinstance(expected, list):
                    return False
                if not all(self._matches(when=item, context=context) for item in expected if isinstance(item, dict)):
                    return False
                continue
            if key == "any":
                if not isinstance(expected, list):
                    return False
                if not any(self._matches(when=item, context=context) for item in expected if isinstance(item, dict)):
                    return False
                continue
            if key == "flag_enabled":
                if not self._all_flags_enabled(expected):
                    return False
                continue
            if key == "flag_disabled":
                if not self._all_flags_disabled(expected):
                    return False
                continue
            if key == "capability_prefix_in":
                capability_id = str(context.get("capability_id") or "").strip().lower()
                prefixes = self._to_list(expected)
                if not any(capability_id.startswith(str(prefix).strip().lower()) for prefix in prefixes):
                    return False
                continue
            if key.endswith("_in"):
                field = key[:-3]
                actual = self._normalize_value(context.get(field))
                values = {self._normalize_value(item) for item in self._to_list(expected)}
                if actual not in values:
                    return False
                continue
            if key.endswith("_any"):
                field = key[:-4]
                actual_list = {self._normalize_value(item) for item in self._to_list(context.get(field))}
                expected_list = {self._normalize_value(item) for item in self._to_list(expected)}
                if not (actual_list & expected_list):
                    return False
                continue

            actual_value = context.get(key)
            if isinstance(expected, bool):
                if bool(actual_value) != expected:
                    return False
                continue
            if self._normalize_value(actual_value) != self._normalize_value(expected):
                return False

        return True

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @staticmethod
    def _to_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _is_flag_enabled(name: str, default: str = "0") -> bool:
        raw = os.getenv(str(name).strip(), default)
        return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}

    def _all_flags_enabled(self, value: Any) -> bool:
        names = [str(item).strip() for item in self._to_list(value) if str(item).strip()]
        if not names:
            return True
        return all(self._is_flag_enabled(name, "0") for name in names)

    def _all_flags_disabled(self, value: Any) -> bool:
        names = [str(item).strip() for item in self._to_list(value) if str(item).strip()]
        if not names:
            return True
        return all(not self._is_flag_enabled(name, "0") for name in names)
