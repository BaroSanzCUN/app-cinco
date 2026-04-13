from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)


class AttendanceAnalyticsBridgeTests(SimpleTestCase):
    def setUp(self):
        self.bridge = IntentToCapabilityBridge()

    def test_maps_group_by_supervisor_to_analytics_capability(self):
        mapped = self.bridge.resolve(
            message="Cantidad de ausentismos del ultimo mes por supervisor en grafica",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": True,
            },
        )
        self.assertEqual(mapped.get("capability_id"), "attendance.summary.by_supervisor.v1")

    def test_maps_monthly_trend_to_analytics_capability(self):
        mapped = self.bridge.resolve(
            message="Quiero la tendencia mensual de ausentismos injustificados",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
        )
        self.assertEqual(mapped.get("capability_id"), "attendance.trend.monthly.v1")

    def test_maps_daily_trend_when_chart_requested(self):
        mapped = self.bridge.resolve(
            message="Dame grafica de tendencia diaria de ausentismo injustificado",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
        )
        self.assertEqual(mapped.get("capability_id"), "attendance.trend.daily.v1")

    def test_maps_contextual_chart_request_to_daily_trend(self):
        mapped = self.bridge.resolve(
            message="Grafica de este reporte",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
        )
        self.assertEqual(mapped.get("capability_id"), "attendance.trend.daily.v1")
