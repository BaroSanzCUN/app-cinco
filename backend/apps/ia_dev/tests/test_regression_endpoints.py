from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.ia_dev.application.contracts.chat_contracts import build_chat_response_snapshot
from apps.ia_dev.views import chat_view as chat_view_module
from apps.ia_dev.views.chat_view import IADevChatView, IADevKnowledgeApproveView


class IADevRegressionEndpointsTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(
            id=77,
            username="regression-user",
            is_authenticated=True,
            is_staff=False,
            is_superuser=False,
        )

    def test_chat_endpoint_keeps_contract_shape(self):
        snapshot = build_chat_response_snapshot()
        snapshot["session_id"] = "sess-123"
        snapshot["reply"] = "ok"

        with patch.object(chat_view_module.orchestrator_service, "run", return_value=snapshot):
            request = self.factory.post(
                "/ia-dev/chat/",
                {"message": "hola", "session_id": "sess-123"},
                format="json",
            )
            force_authenticate(request, user=self.user)
            response = IADevChatView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), set(snapshot.keys()))
        self.assertEqual(response.data["session_id"], "sess-123")
        self.assertIn("observability", response.data)

    def test_knowledge_approve_sync_flow_still_works(self):
        result = {"ok": True, "applied": True, "proposal": {"proposal_id": "KPRO-01"}}
        with patch.object(chat_view_module.async_job_service, "mode", "sync"):
            with patch.object(
                chat_view_module.knowledge_governance_service,
                "apply_proposal",
                return_value=result,
            ) as mock_apply:
                request = self.factory.post(
                    "/ia-dev/knowledge/proposals/approve/",
                    {
                        "proposal_id": "KPRO-01",
                        "idempotency_key": "idem-knowledge-01",
                    },
                    format="json",
                )
                force_authenticate(request, user=self.user)
                response = IADevKnowledgeApproveView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("ok"))
        mock_apply.assert_called_once_with(
            proposal_id="KPRO-01",
            auth_key=None,
            idempotency_key="idem-knowledge-01",
        )

