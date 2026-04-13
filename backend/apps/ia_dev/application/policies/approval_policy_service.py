from __future__ import annotations

from typing import Any

from apps.ia_dev.application.policies.policy_loader import PolicyLoader


class ApprovalPolicyService:
    def __init__(self, *, loader: PolicyLoader | None = None):
        self.loader = loader or PolicyLoader()
        self._policy = self.loader.load("approval_policy.yaml")

    @property
    def version(self) -> str:
        return str((self._policy or {}).get("version") or "unknown")

    def requires_approval_for_scope(self, scope: str | None) -> bool:
        normalized = str(scope or "").strip().lower()
        values = {
            str(item or "").strip().lower()
            for item in ((self._policy or {}).get("approval_required_for") or [])
        }
        if not values:
            values = {"business", "general"}
        return normalized in values

    def allowed_roles(self, *, action: str) -> set[str]:
        action_key = str(action or "approve").strip().lower()
        roles = (
            ((self._policy or {}).get("roles") or {}).get(action_key)
            if isinstance((self._policy or {}).get("roles"), dict)
            else None
        )
        values = {str(item or "").strip().lower() for item in (roles or []) if str(item or "").strip()}
        if values:
            return values
        return {"admin", "lead", "governance"}

    def can_review(self, *, scope: str | None, role: str | None, action: str) -> bool:
        if not self.requires_approval_for_scope(scope):
            return True
        role_value = str(role or "").strip().lower()
        return role_value in self.allowed_roles(action=action)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "approval_required_for": sorted(
                {
                    str(item or "").strip().lower()
                    for item in ((self._policy or {}).get("approval_required_for") or [])
                }
            ),
            "roles": {
                "approve": sorted(self.allowed_roles(action="approve")),
                "reject": sorted(self.allowed_roles(action="reject")),
            },
        }
