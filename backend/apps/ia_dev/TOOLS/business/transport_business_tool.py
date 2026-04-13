from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.ia_dev.services.tool_transport_service import TransportToolService


@dataclass(frozen=True, slots=True)
class TransportPeriod:
    day: date
    label: str = "hoy"
    source: str = "rules"


class TransportBusinessTool:
    """
    Capa tipada de negocio para transporte.
    Encapsula TransportToolService y evita SQL directo desde orchestration/routing.
    """

    def __init__(self, *, service: TransportToolService | None = None):
        self.service = service or TransportToolService()

    @property
    def table(self) -> str:
        return str(getattr(self.service, "table", "") or "")

    @property
    def date_column(self) -> str:
        return str(getattr(self.service, "date_column", "") or "fecha_salida")

    def source_status(self) -> dict[str, Any]:
        return self.service.source_status()

    def get_departures_summary(self, *, period: TransportPeriod) -> dict[str, Any]:
        return self.service.get_departures_summary(period.day)
