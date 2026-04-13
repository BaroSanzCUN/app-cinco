from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)


class ChatBootstrapContextTests(SimpleTestCase):
    def test_followup_chart_message_keeps_attendance_domain_from_session_context(self):
        classification = ChatApplicationService._bootstrap_classification(
            message="grafica de este reporte",
            session_context={
                "last_domain": "attendance",
                "last_needs_database": True,
                "last_output_mode": "summary",
            },
        )
        self.assertEqual(classification.get("domain"), "attendance")
        self.assertEqual(classification.get("intent"), "attendance_query")
        self.assertTrue(classification.get("needs_database"))
