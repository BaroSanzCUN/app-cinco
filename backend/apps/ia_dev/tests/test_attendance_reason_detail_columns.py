from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.services.tool_attendance_service import AttendanceToolService


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed: list[tuple[str, list[object]]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.executed.append((str(query), list(params)))

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)


class AttendanceReasonDetailColumnsTests(SimpleTestCase):
    def _build_service(self) -> AttendanceToolService:
        service = AttendanceToolService.__new__(AttendanceToolService)
        service.table = "cincosas_cincosas.gestionh_ausentismo"
        service.personal_table = "cincosas_cincosas.cinco_base_de_personal"
        service.db_alias = "default"
        service.table_source = "env"
        service.personal_table_source = "env"
        return service

    def test_detail_with_personal_adds_ini_y_fin_incapa_for_justified_reason(self):
        service = self._build_service()
        attendance_rows = [
            ("1001", "2026-04-20", "SI", "VACACIONES", "2026-04-20", "2026-04-25"),
        ]
        employee_catalog = {
            "by_cedula": {
                "1001": {
                    "cedula": "1001",
                    "nombre": "ANA",
                    "apellido": "PEREZ",
                    "supervisor": "",
                    "area": "I&M",
                    "cargo": "TECNICO",
                    "carpeta": "FTTH",
                }
            },
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 1,
        }
        empty_supervisors = {
            "by_cedula": {},
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 0,
        }

        with patch("apps.ia_dev.services.tool_attendance_service.connections", {"default": _FakeConnection(attendance_rows)}):
            with patch.object(AttendanceToolService, "_get_attendance_columns", return_value={"ini_incapa", "fin_incapa"}):
                with patch.object(
                    AttendanceToolService,
                    "get_data_employers",
                    side_effect=[employee_catalog, empty_supervisors],
                ):
                    result = service.get_detail_with_personal(
                        start_date=date(2026, 4, 20),
                        end_date=date(2026, 4, 20),
                        justificacion_filter="VACACIONES",
                        focus="all",
                    )

        row = dict((result.get("rows") or [{}])[0])
        self.assertEqual(row.get("ini_incapa"), "2026-04-20")
        self.assertEqual(row.get("fin_incapa"), "2026-04-25")
        self.assertEqual(row.get("estado_justificacion"), "JUSTIFICADO")

    def test_detail_with_personal_omits_ini_y_fin_incapa_without_reason_filter(self):
        service = self._build_service()
        attendance_rows = [
            ("1001", "2026-04-20", "SI", ""),
        ]
        employee_catalog = {
            "by_cedula": {
                "1001": {
                    "cedula": "1001",
                    "nombre": "ANA",
                    "apellido": "PEREZ",
                    "supervisor": "",
                    "area": "I&M",
                    "cargo": "TECNICO",
                    "carpeta": "FTTH",
                }
            },
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 1,
        }
        empty_supervisors = {
            "by_cedula": {},
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 0,
        }

        with patch("apps.ia_dev.services.tool_attendance_service.connections", {"default": _FakeConnection(attendance_rows)}):
            with patch.object(AttendanceToolService, "_get_attendance_columns", return_value={"ini_incapa", "fin_incapa"}):
                with patch.object(
                    AttendanceToolService,
                    "get_data_employers",
                    side_effect=[employee_catalog, empty_supervisors],
                ):
                    result = service.get_detail_with_personal(
                        start_date=date(2026, 4, 20),
                        end_date=date(2026, 4, 20),
                        focus="all",
                    )

        row = dict((result.get("rows") or [{}])[0])
        self.assertNotIn("ini_incapa", row)
        self.assertNotIn("fin_incapa", row)

    def test_detail_with_personal_adds_incapacity_reference_columns_for_incapacidad(self):
        service = self._build_service()
        attendance_rows = [
            (
                "1001",
                "2026-04-20",
                "SI",
                "INCAPACIDAD",
                "2026-04-20",
                "2026-04-25",
                "ACCIDENTE",
                "Inicial",
                "COMUN",
                "S934",
                "Lumbalgia no especificada",
            ),
        ]
        employee_catalog = {
            "by_cedula": {
                "1001": {
                    "cedula": "1001",
                    "nombre": "ANA",
                    "apellido": "PEREZ",
                    "supervisor": "",
                    "area": "I&M",
                    "cargo": "TECNICO",
                    "carpeta": "FTTH",
                }
            },
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 1,
        }
        empty_supervisors = {
            "by_cedula": {},
            "status_filter": "all",
            "status_column": "estado",
            "catalog_count": 0,
        }

        with patch("apps.ia_dev.services.tool_attendance_service.connections", {"default": _FakeConnection(attendance_rows)}):
            with patch.object(
                AttendanceToolService,
                "_get_attendance_columns",
                return_value={"ini_incapa", "fin_incapa", "causa_aus", "ini_inca", "tipo_inca", "codigo_inca", "desc_inca"},
            ):
                with patch.object(
                    AttendanceToolService,
                    "get_data_employers",
                    side_effect=[employee_catalog, empty_supervisors],
                ):
                    result = service.get_detail_with_personal(
                        start_date=date(2026, 4, 20),
                        end_date=date(2026, 4, 20),
                        justificacion_filter="INCAPACIDAD",
                        focus="all",
                    )

        row = dict((result.get("rows") or [{}])[0])
        self.assertEqual(row.get("ini_incapa"), "2026-04-20")
        self.assertEqual(row.get("fin_incapa"), "2026-04-25")
        self.assertEqual(row.get("causa_aus"), "ACCIDENTE")
        self.assertEqual(row.get("ini_inca"), "Inicial")
        self.assertEqual(row.get("tipo_inca"), "COMUN")
        self.assertEqual(row.get("codigo_inca"), "S934")
        self.assertEqual(row.get("desc_inca"), "Lumbalgia no especificada")
