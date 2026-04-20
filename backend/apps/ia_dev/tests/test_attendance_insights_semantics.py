from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.domains.attendance.handler import AttendanceHandler


class AttendanceInsightsSemanticsTests(SimpleTestCase):
    def test_build_probable_causes_insights_includes_top_group_hint(self):
        insights = AttendanceHandler._build_probable_causes_insights(
            rows=[
                {"grupo": "I&M", "total_injustificados": 366, "porcentaje": 73.2},
                {"grupo": "IMPLEMENTACION FO", "total_injustificados": 51, "porcentaje": 10.2},
            ],
            group_label="Area",
        )
        joined = " ".join(insights).lower()
        self.assertIn("i&m", joined)
        self.assertIn("73.2%", joined)
        self.assertTrue(any("posibles causas" in item.lower() for item in insights))

    def test_message_requests_probable_causes_detects_suggestion_prompt(self):
        handler = AttendanceHandler()
        self.assertTrue(
            handler._message_requests_probable_causes(
                "Que areas concentran mas ausentismos y que causas probables sugieres?"
            )
        )
