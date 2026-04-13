from __future__ import annotations

import re
from typing import Any

from apps.empleados.services.empleado_service import EmpleadoService
from apps.ia_dev.application.delegation.task_contracts import DelegationResult, DelegationTask


class EmpleadosHandler:
    def __init__(self, *, service: EmpleadoService | None = None):
        self.service = service or EmpleadoService()

    def resolver_entidad_objetivo(self, *, consulta: str, limite: int = 120) -> dict[str, Any]:
        filtros = self._extraer_filtros_desde_texto(consulta=consulta)
        empleados = self._buscar_empleados(filtros=filtros, limite=limite)
        entidad = self._resolver_tipo_entidad(filtros=filtros)
        return {
            "entity_type": entidad,
            "entity_ids": [str(item.get("cedula") or "") for item in empleados if item.get("cedula")],
            "entity_attributes": {
                "filtros_normalizados": filtros,
                "total_empleados": len(empleados),
            },
            "empleados": empleados,
        }

    def resolver_subtarea(self, *, task: DelegationTask, observability=None) -> DelegationResult:
        consulta = str(task.business_objective or "").strip() or str(
            (task.trace_context or {}).get("message") or ""
        )
        if not consulta:
            consulta = "resolver entidad objetivo de empleados"
        resolved = self.resolver_entidad_objetivo(
            consulta=consulta,
            limite=max(1, min(int(task.constraints.get("limit") or 200), 500)),
        )
        empleados = list(resolved.get("empleados") or [])
        table = {
            "columns": list(empleados[0].keys()) if empleados else [],
            "rows": empleados,
            "rowcount": len(empleados),
        }
        kpis = {
            "total_empleados_resueltos": len(empleados),
            "total_entidades_objetivo": len(list(resolved.get("entity_ids") or [])),
        }
        insights = [
            (
                f"Entidad objetivo resuelta como {resolved.get('entity_type') or 'empresa'} "
                f"con {kpis['total_empleados_resueltos']} empleados."
            )
        ]
        self._record_event(
            observability=observability,
            event_type="delegation_empleados_resolver_entidad",
            meta={
                "task_id": task.task_id,
                "entity_type": resolved.get("entity_type"),
                "total_empleados": kpis["total_empleados_resueltos"],
            },
        )
        return DelegationResult(
            task_id=task.task_id,
            domain_code=task.domain_code,
            status="ok" if empleados else "partial",
            reply_text="Entidad objetivo de empleados resuelta.",
            kpis=kpis,
            table=table,
            insights=insights,
            data_lineage={
                "tables_used": ["cinco_base_de_personal"],
                "filters_applied": dict((resolved.get("entity_attributes") or {}).get("filtros_normalizados") or {}),
                "rowcount": len(empleados),
            },
        )

    def obtener_empleados_por_supervisor(self, *, supervisor: str, limite: int = 200) -> dict[str, Any]:
        filtros = {"supervisor": str(supervisor or "").strip()}
        empleados = self._buscar_empleados(filtros=filtros, limite=limite)
        return {
            "supervisor": filtros["supervisor"],
            "total_empleados": len(empleados),
            "empleados": empleados,
            "cedulas": [str(item.get("cedula") or "") for item in empleados if item.get("cedula")],
        }

    def obtener_empleados_por_area(self, *, area: str, limite: int = 300) -> dict[str, Any]:
        filtros = {"area": str(area or "").strip()}
        empleados = self._buscar_empleados(filtros=filtros, limite=limite)
        return {
            "area": filtros["area"],
            "total_empleados": len(empleados),
            "empleados": empleados,
            "cedulas": [str(item.get("cedula") or "") for item in empleados if item.get("cedula")],
        }

    @staticmethod
    def _resolver_tipo_entidad(*, filtros: dict[str, str]) -> str:
        if filtros.get("cedula") or filtros.get("nombre"):
            return "empleado"
        if filtros.get("supervisor"):
            return "supervisor"
        if filtros.get("area"):
            return "area"
        if filtros.get("cargo"):
            return "cargo"
        if filtros.get("carpeta"):
            return "carpeta"
        return "empresa"

    def _buscar_empleados(self, *, filtros: dict[str, str], limite: int) -> list[dict[str, Any]]:
        query_params: dict[str, str] = {}
        for key in ("cedula", "nombre", "area", "cargo", "supervisor", "carpeta"):
            value = str(filtros.get(key) or "").strip()
            if value:
                query_params[key] = value
        if not query_params and filtros.get("search"):
            query_params["search"] = str(filtros["search"])

        try:
            queryset = self.service.listar(query_params=query_params)
            rows = list(
                queryset.values(
                    "id",
                    "cedula",
                    "nombre",
                    "apellido",
                    "area",
                    "cargo",
                    "supervisor",
                    "carpeta",
                    "estado",
                )[: max(1, min(int(limite), 500))]
            )
        except Exception:
            return []

        empleados: list[dict[str, Any]] = []
        for row in rows:
            nombre = str(row.get("nombre") or "").strip()
            apellido = str(row.get("apellido") or "").strip()
            empleados.append(
                {
                    "id": row.get("id"),
                    "cedula": str(row.get("cedula") or "").strip(),
                    "nombre": nombre,
                    "apellido": apellido,
                    "nombre_completo": f"{nombre} {apellido}".strip(),
                    "area": str(row.get("area") or "").strip(),
                    "cargo": str(row.get("cargo") or "").strip(),
                    "supervisor": str(row.get("supervisor") or "").strip(),
                    "carpeta": str(row.get("carpeta") or "").strip(),
                    "estado": str(row.get("estado") or "").strip(),
                }
            )
        return empleados

    @staticmethod
    def _extraer_filtros_desde_texto(*, consulta: str) -> dict[str, str]:
        text = str(consulta or "").strip()
        lowered = text.lower()
        filters: dict[str, str] = {}

        cedula_match = re.search(r"\b\d{6,13}\b", lowered)
        if cedula_match:
            filters["cedula"] = cedula_match.group(0)

        supervisor = EmpleadosHandler._extract_after_keyword(lowered, keyword="supervisor")
        if supervisor:
            filters["supervisor"] = supervisor

        area = EmpleadosHandler._extract_after_keyword(lowered, keyword="area")
        if area:
            filters["area"] = area

        cargo = EmpleadosHandler._extract_after_keyword(lowered, keyword="cargo")
        if cargo:
            filters["cargo"] = cargo

        carpeta = EmpleadosHandler._extract_after_keyword(lowered, keyword="carpeta")
        if carpeta:
            filters["carpeta"] = carpeta

        if "empleado " in lowered and "cedula" not in filters:
            maybe_name = lowered.split("empleado ", 1)[1].strip()
            if maybe_name and len(maybe_name) >= 3:
                filters["nombre"] = maybe_name[:80]

        if not filters:
            filters["search"] = lowered[:80]
        return filters

    @staticmethod
    def _extract_after_keyword(text: str, *, keyword: str) -> str:
        pattern = rf"{re.escape(keyword)}\s+([a-z0-9_ .-]{{2,80}})"
        match = re.search(pattern, text)
        if not match:
            return ""
        value = str(match.group(1) or "").strip()
        for token in (" y ", ",", ".", ";"):
            if token in value:
                value = value.split(token, 1)[0].strip()
        return value

    @staticmethod
    def _record_event(*, observability, event_type: str, meta: dict[str, Any]) -> None:
        if observability is None or not hasattr(observability, "record_event"):
            return
        observability.record_event(
            event_type=event_type,
            source="EmpleadosHandler",
            meta=dict(meta or {}),
        )
