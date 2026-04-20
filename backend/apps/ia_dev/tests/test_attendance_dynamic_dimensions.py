from __future__ import annotations

from datetime import date

from django.test import SimpleTestCase

from apps.ia_dev.TOOLS.business.attendance_business_tool import (
    AttendanceBusinessTool,
    AttendancePeriod,
)


class _FakeAttendanceService:
    def __init__(self):
        self.last_detail_kwargs: dict[str, object] | None = None

    def get_unjustified_with_personal(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100,
        *,
        personal_status: str = "all",
        cedula: str | None = None,
        extra_personal_columns: list[str] | None = None,
    ) -> dict:
        return {
            "periodo_inicio": start_date.isoformat(),
            "periodo_fin": end_date.isoformat(),
            "rowcount": 3,
            "rows": [
                {"cedula": "1", "sede": "BOGOTA", "estado_justificacion": "INJUSTIFICADO"},
                {"cedula": "2", "sede": "BOGOTA", "estado_justificacion": "INJUSTIFICADO"},
                {"cedula": "3", "sede": "MEDELLIN", "estado_justificacion": "INJUSTIFICADO"},
            ],
            "truncated": False,
            "requested_extra_columns": list(extra_personal_columns or []),
        }

    def get_detail_with_personal(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int = 150,
        personal_status: str = "all",
        cedula: str | None = None,
        extra_personal_columns: list[str] | None = None,
        justificacion_filter: str | None = None,
        focus: str = "all",
    ) -> dict:
        self.last_detail_kwargs = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "personal_status": personal_status,
            "cedula": cedula,
            "extra_personal_columns": list(extra_personal_columns or []),
            "justificacion_filter": justificacion_filter,
            "focus": focus,
        }
        return self.get_unjustified_with_personal(
            start_date,
            end_date,
            limit=limit,
            personal_status=personal_status,
            cedula=cedula,
            extra_personal_columns=extra_personal_columns,
        )


class AttendanceDynamicDimensionsTests(SimpleTestCase):
    def test_attendance_business_tool_resolves_tipo_labor_dimension(self):
        self.assertEqual(
            AttendanceBusinessTool._resolve_group_by("tipo_labor"),
            ("tipo_labor", "Tipo Labor"),
        )
        self.assertEqual(
            AttendanceBusinessTool._resolve_group_by("labor"),
            ("tipo_labor", "Tipo Labor"),
        )

    def test_attendance_business_tool_supports_dynamic_group_dimension(self):
        tool = AttendanceBusinessTool(service=_FakeAttendanceService())
        result = tool.get_attendance_aggregation(
            period=AttendancePeriod(start=date(2026, 4, 1), end=date(2026, 4, 19)),
            group_by="sede",
            personal_status="all",
            top_n=10,
            chart_type="bar",
            focus="unjustified",
        )
        self.assertEqual(str(result.get("group_key") or ""), "sede")
        self.assertEqual(str(result.get("group_label") or ""), "Sede")
        rows = list(result.get("rows") or [])
        self.assertEqual(str(rows[0].get("sede") or ""), "BOGOTA")
        self.assertEqual(int(rows[0].get("total_injustificados") or 0), 2)

    def test_attendance_business_tool_passes_reason_filter_for_vacaciones(self):
        service = _FakeAttendanceService()
        tool = AttendanceBusinessTool(service=service)
        result = tool.get_attendance_aggregation(
            period=AttendancePeriod(start=date(2026, 4, 1), end=date(2026, 4, 19)),
            group_by="sede",
            personal_status="all",
            top_n=10,
            chart_type="bar",
            focus="all",
            justificacion_filter="VACACIONES",
        )
        self.assertEqual(str(result.get("justificacion_filter") or ""), "VACACIONES")
        self.assertIsNotNone(service.last_detail_kwargs)
        self.assertEqual(str((service.last_detail_kwargs or {}).get("justificacion_filter") or ""), "VACACIONES")
