from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.ia_dev.services.tool_attendance_service import AttendanceToolService


@dataclass(frozen=True, slots=True)
class AttendancePeriod:
    start: date
    end: date
    label: str = "hoy"
    source: str = "rules"


class AttendanceBusinessTool:
    """
    Capa tipada de negocio para attendance.
    Encapsula AttendanceToolService y evita acceso SQL desde orchestration/routing.
    """

    def __init__(self, *, service: AttendanceToolService | None = None):
        self.service = service or AttendanceToolService()

    @property
    def attendance_table(self) -> str:
        return str(getattr(self.service, "table", "") or "")

    @property
    def attendance_table_source(self) -> str:
        return str(getattr(self.service, "table_source", "") or "env")

    @property
    def personal_table(self) -> str:
        return str(getattr(self.service, "personal_table", "") or "")

    @property
    def personal_table_source(self) -> str:
        return str(getattr(self.service, "personal_table_source", "") or "env")

    def get_unjustified_summary(self, *, period: AttendancePeriod) -> dict[str, Any]:
        return self.service.get_summary(period.start, period.end)

    def get_unjustified_table(
        self,
        *,
        period: AttendancePeriod,
        include_personal: bool,
        personal_status: str = "all",
        limit: int = 150,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 500))
        if include_personal:
            return self.service.get_unjustified_with_personal(
                period.start,
                period.end,
                limit=safe_limit,
                personal_status=personal_status,
            )
        return self.service.get_unjustified_table(
            period.start,
            period.end,
            limit=safe_limit,
        )

    def get_recurrence_grouped(
        self,
        *,
        period: AttendancePeriod,
        threshold: int = 2,
        personal_status: str = "all",
        limit: int = 150,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 500))
        safe_threshold = max(1, int(threshold))
        recurrence = self.service.get_recurrent_unjustified_with_supervisor(
            period.start,
            period.end,
            threshold=safe_threshold,
            limit=safe_limit,
            personal_status=personal_status,
        )
        return {
            **recurrence,
            "rows_grouped": self.shape_grouped_rows(recurrence.get("rows") or []),
        }

    def get_recurrence_itemized(
        self,
        *,
        period: AttendancePeriod,
        grouped_result: dict[str, Any] | None = None,
        personal_status: str = "all",
        detail_limit: int = 500,
    ) -> dict[str, Any]:
        grouped = grouped_result or self.get_recurrence_grouped(
            period=period,
            threshold=2,
            personal_status=personal_status,
            limit=150,
        )
        grouped_rows = list(grouped.get("rows") or [])
        recurrent_ids = {
            self._normalize_identifier(row.get("cedula"))
            for row in grouped_rows
            if row.get("cedula")
        }
        if not recurrent_ids:
            return {
                "periodo_inicio": grouped.get("periodo_inicio"),
                "periodo_fin": grouped.get("periodo_fin"),
                "threshold": int(grouped.get("threshold") or 2),
                "rowcount": 0,
                "rows": [],
                "recurrent_count": int(grouped.get("rowcount") or 0),
            }

        detail = self.service.get_unjustified_with_personal(
            period.start,
            period.end,
            limit=max(1, min(int(detail_limit), 500)),
            personal_status=personal_status,
        )
        detail_rows = list(detail.get("rows") or [])
        itemized_rows: list[dict[str, Any]] = []
        for row in detail_rows:
            if self._normalize_identifier(row.get("cedula")) not in recurrent_ids:
                continue
            itemized_rows.append({k: v for k, v in row.items() if k != "personal_match"})

        return {
            "periodo_inicio": grouped.get("periodo_inicio"),
            "periodo_fin": grouped.get("periodo_fin"),
            "threshold": int(grouped.get("threshold") or 2),
            "rowcount": len(itemized_rows),
            "rows": itemized_rows,
            "recurrent_count": int(grouped.get("rowcount") or 0),
            "source_grouped": grouped,
        }

    @staticmethod
    def shape_grouped_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped_rows: list[dict[str, Any]] = []
        for row in rows:
            grouped_rows.append(
                {
                    "cedula": row.get("cedula", ""),
                    "empleado": row.get("empleado", ""),
                    "supervisor": row.get("supervisor", ""),
                    "cantidad_injustificados": row.get("cantidad_incidencias", 0),
                    "fechas_ausentismo": row.get("fechas", ""),
                }
            )
        return grouped_rows

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        raw = str(value or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits or raw.lower()
