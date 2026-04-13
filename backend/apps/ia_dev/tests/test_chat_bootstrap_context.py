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

    def test_bootstrap_classifies_rrhh_employee_queries_into_empleados_domain(self):
        classification = ChatApplicationService._bootstrap_classification(
            message="Cantidad empleados activos",
            session_context={},
        )
        self.assertEqual(classification.get("domain"), "empleados")
        self.assertEqual(classification.get("intent"), "empleados_query")
        self.assertEqual(classification.get("selected_agent"), "rrhh_agent")

    def test_bootstrap_sets_summary_for_grouped_count_attendance(self):
        classification = ChatApplicationService._bootstrap_classification(
            message="Cantidad de ausentismos por supervisor los ultimos 15 dias",
            session_context={},
        )
        self.assertEqual(classification.get("domain"), "attendance")
        self.assertEqual(classification.get("output_mode"), "summary")
