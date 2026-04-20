from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.ia_dev.interfaces.api.views.memory_view import (
    IADevMemoryAuditView,
    IADevMemoryProposalApproveView,
    IADevMemoryProposalRejectView,
    IADevMemoryProposalView,
    IADevUserMemoryView,
)


class _DummyGroupQuerySet:
    def __init__(self, exists_result: bool):
        self._exists_result = bool(exists_result)

    def exists(self) -> bool:
        return self._exists_result


class _DummyGroupManager:
    def __init__(self, names: list[str] | None = None):
        self._names = {str(name).lower() for name in (names or [])}

    def filter(self, **kwargs):
        expected_name = str(kwargs.get("name__iexact") or "").lower()
        return _DummyGroupQuerySet(expected_name in self._names)


def _build_user(
    *,
    user_id: int,
    username: str,
    is_staff: bool = False,
    is_superuser: bool = False,
    groups: list[str] | None = None,
):
    return SimpleNamespace(
        id=user_id,
        username=username,
        is_authenticated=True,
        is_staff=bool(is_staff),
        is_superuser=bool(is_superuser),
        groups=_DummyGroupManager(groups),
    )


class IADevMemoryApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = _build_user(user_id=11, username="memory-user")
        self.admin = _build_user(user_id=1, username="memory-admin", is_staff=True)
        self.governance = _build_user(
            user_id=2,
            username="memory-governance",
            groups=["governance"],
        )

    def _post(self, view_cls, *, user, path: str, data: dict):
        request = self.factory.post(path, data, format="json")
        force_authenticate(request, user=user)
        return view_cls.as_view()(request)

    def _get(self, view_cls, *, user, path: str):
        request = self.factory.get(path)
        force_authenticate(request, user=user)
        return view_cls.as_view()(request)

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.create_proposal")
    def test_create_proposal_returns_created(self, mock_create_proposal):
        mock_create_proposal.return_value = {
            "ok": True,
            "proposal": {"proposal_id": "LMP-0001", "status": "pending"},
            "idempotent": False,
        }

        response = self._post(
            IADevMemoryProposalView,
            user=self.user,
            path="/ia-dev/memory/proposals/",
            data={
                "scope": "user",
                "candidate_key": "attendance.output_mode",
                "candidate_value": {"value": "grouped"},
                "sensitivity": "low",
                "reason": "cuenta solicita formato agrupado",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("ok"))
        mock_create_proposal.assert_called_once()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.create_proposal")
    def test_create_proposal_rejects_invalid_candidate_key(self, mock_create_proposal):
        response = self._post(
            IADevMemoryProposalView,
            user=self.user,
            path="/ia-dev/memory/proposals/",
            data={
                "scope": "user",
                "candidate_key": "attendance bad key",
                "candidate_value": {"value": "grouped"},
                "sensitivity": "low",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("ok"))
        mock_create_proposal.assert_not_called()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.approve_proposal")
    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.get_proposal")
    def test_approve_business_scope_denies_non_admin(self, mock_get_proposal, mock_approve):
        mock_get_proposal.return_value = {"proposal_id": "LMP-0002", "scope": "business"}

        response = self._post(
            IADevMemoryProposalApproveView,
            user=self.user,
            path="/ia-dev/memory/proposals/approve/",
            data={"proposal_id": "LMP-0002", "comment": "approve"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get("ok"))
        mock_approve.assert_not_called()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.approve_proposal")
    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.get_proposal")
    def test_approve_business_scope_allows_governance_role(self, mock_get_proposal, mock_approve):
        mock_get_proposal.return_value = {"proposal_id": "LMP-0003", "scope": "business"}
        mock_approve.return_value = {
            "ok": True,
            "proposal": {"proposal_id": "LMP-0003", "status": "applied"},
        }

        response = self._post(
            IADevMemoryProposalApproveView,
            user=self.governance,
            path="/ia-dev/memory/proposals/approve/",
            data={"proposal_id": "LMP-0003", "comment": "approved"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("ok"))
        mock_approve.assert_called_once()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.reject_proposal")
    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.get_proposal")
    def test_reject_business_scope_denies_non_admin(self, mock_get_proposal, mock_reject):
        mock_get_proposal.return_value = {"proposal_id": "LMP-0004", "scope": "general"}

        response = self._post(
            IADevMemoryProposalRejectView,
            user=self.user,
            path="/ia-dev/memory/proposals/reject/",
            data={"proposal_id": "LMP-0004", "comment": "reject"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get("ok"))
        mock_reject.assert_not_called()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.get_audit_events")
    def test_audit_global_denied_for_non_admin(self, mock_get_audit):
        response = self._get(
            IADevMemoryAuditView,
            user=self.user,
            path="/ia-dev/memory/audit/?scope=general",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get("ok"))
        mock_get_audit.assert_not_called()

    @patch("apps.ia_dev.interfaces.api.views.memory_view.memory_governance_service.get_audit_events")
    def test_audit_user_scope_filters_to_requester(self, mock_get_audit):
        my_entity = f"user:{self.user.id}:attendance.mode"
        other_entity = f"user:{self.admin.id}:attendance.mode"
        mock_get_audit.return_value = [
            {"id": 1, "memory_scope": "user", "entity_key": my_entity},
            {"id": 2, "memory_scope": "user", "entity_key": other_entity},
        ]

        response = self._get(
            IADevMemoryAuditView,
            user=self.user,
            path="/ia-dev/memory/audit/?scope=user",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data["events"][0]["entity_key"], my_entity)

    def test_user_memory_cross_user_denied_for_non_admin(self):
        other_user_key = f"user:{self.admin.id}"

        response = self._get(
            IADevUserMemoryView,
            user=self.user,
            path=f"/ia-dev/memory/user/?user_key={other_user_key}",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get("ok"))
