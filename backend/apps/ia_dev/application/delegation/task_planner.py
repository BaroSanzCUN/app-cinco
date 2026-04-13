from __future__ import annotations

from typing import Any

from apps.ia_dev.application.delegation.domain_registry import DomainDescriptor, DomainRegistry
from apps.ia_dev.application.delegation.task_contracts import (
    DelegationTask,
    EntityScope,
    build_task_id,
)
from apps.ia_dev.services.period_service import resolve_period_from_text


class TaskPlanner:
    def __init__(self, *, domain_registry: DomainRegistry | None = None):
        self.domain_registry = domain_registry or DomainRegistry()

    def plan_tasks(
        self,
        *,
        message: str,
        classification: dict[str, Any],
        planned_candidates: list[dict[str, Any]] | None,
        run_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        domains = self.domain_registry.resolve_domains_for_message(
            message=message,
            classification=classification,
            planned_candidates=planned_candidates,
        )
        if not domains:
            return {
                "should_delegate": False,
                "reason": "no_registered_domain_detected",
                "selected_domains": [],
                "tasks": [],
                "warnings": ["No se encontraron dominios habilitados para delegacion."],
            }

        primary = self._resolve_primary_domain(domains=domains)
        if primary is None:
            return {
                "should_delegate": False,
                "reason": "no_primary_domain_for_delegation",
                "selected_domains": [item.as_dict() for item in domains],
                "tasks": [],
                "warnings": ["No fue posible determinar dominio primario para delegacion."],
            }

        is_multi_domain = len(domains) > 1
        employee_domain = self._find_domain(domains=domains, code="empleados")
        employees_tasks = self._plan_empleados_tasks(
            domain=employee_domain,
            message=message,
            run_id=run_id,
            trace_id=trace_id,
        )

        if primary.domain_code == "ausentismo":
            tasks = self._plan_ausentismo_tasks(
                domain=primary,
                message=message,
                run_id=run_id,
                trace_id=trace_id,
                dependencies=[item.task_id for item in employees_tasks],
            )
            all_tasks = [*employees_tasks, *tasks]
            if primary.domain_status in {"partial", "planned"}:
                warnings.append(
                    f"Dominio {primary.domain_code} en estado {primary.domain_status}; se aplicara degradacion controlada."
                )
            return {
                "should_delegate": bool(all_tasks),
                "reason": "ausentismo_analytics_delegation_plan",
                "selected_domains": [item.as_dict() for item in domains],
                "tasks": all_tasks,
                "primary_domain": primary.as_dict(),
                "is_multi_domain": is_multi_domain,
                "warnings": warnings,
            }

        if primary.domain_status in {"planned", "partial"}:
            exploratory = self._plan_sql_assisted_task(
                domain=primary,
                message=message,
                run_id=run_id,
                trace_id=trace_id,
            )
            return {
                "should_delegate": bool(exploratory),
                "reason": "planned_or_partial_domain_sql_assisted_candidate",
                "selected_domains": [item.as_dict() for item in domains],
                "tasks": [*employees_tasks, *([exploratory] if exploratory else [])],
                "primary_domain": primary.as_dict(),
                "is_multi_domain": is_multi_domain,
                "warnings": [
                    *warnings,
                    f"Dominio {primary.domain_code} en estado {primary.domain_status}; se habilita ruta SQL asistida restringida.",
                ],
            }

        return {
            "should_delegate": False,
            "reason": "delegation_not_required_for_domain_state",
            "selected_domains": [item.as_dict() for item in domains],
            "tasks": [],
            "primary_domain": primary.as_dict(),
            "is_multi_domain": is_multi_domain,
            "warnings": warnings,
        }

    @staticmethod
    def _resolve_primary_domain(*, domains: list[DomainDescriptor]) -> DomainDescriptor | None:
        if not domains:
            return None
        for item in domains:
            if item.domain_code != "empleados":
                return item
        return domains[0]

    def _plan_ausentismo_tasks(
        self,
        *,
        domain: DomainDescriptor,
        message: str,
        run_id: str,
        trace_id: str,
        dependencies: list[str] | None = None,
    ) -> list[DelegationTask]:
        if not self._is_analytics_request(message):
            return []

        period = resolve_period_from_text(message)
        scope = EntityScope(
            entity_type="supervisor" if "supervisor" in message.lower() else "empresa",
            period_start=period.get("start").isoformat() if period.get("start") else None,
            period_end=period.get("end").isoformat() if period.get("end") else None,
            period_label=str(period.get("label") or ""),
            group_by=["supervisor"] if "supervisor" in message.lower() else [],
            metric_targets=["total_injustificados", "porcentaje"],
        )
        wants_chart = self._wants_chart(message)
        wants_trend = self._wants_trend(message)
        prefers_monthly = self._prefers_monthly(message)

        tasks: list[DelegationTask] = [
            DelegationTask(
                task_id=build_task_id("del"),
                run_id=run_id,
                domain_code=domain.domain_code,
                domain_status=domain.domain_status,
                task_type="resumen_supervisor",
                capability_id="attendance.summary.by_supervisor.v1",
                business_method="obtener_resumen_por_supervisor",
                priority=90,
                depends_on=list(dependencies or []),
                requested_outputs=["kpis", "table"],
                business_objective="Comparar ausentismo por supervisor.",
                entity_scope=scope,
                trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan"},
            ),
            DelegationTask(
                task_id=build_task_id("del"),
                run_id=run_id,
                domain_code=domain.domain_code,
                domain_status=domain.domain_status,
                task_type="tabla_supervisor",
                capability_id="attendance.summary.by_supervisor.v1",
                business_method="obtener_tabla_por_supervisor",
                priority=85,
                depends_on=list(dependencies or []),
                requested_outputs=["table"],
                business_objective="Construir tabla comparativa de ausentismo por supervisor.",
                entity_scope=scope,
                trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan"},
            ),
        ]

        if wants_chart:
            tasks.append(
                DelegationTask(
                    task_id=build_task_id("del"),
                    run_id=run_id,
                    domain_code=domain.domain_code,
                    domain_status=domain.domain_status,
                    task_type="tendencia_mensual" if prefers_monthly else "tendencia_diaria",
                    capability_id="attendance.trend.monthly.v1" if prefers_monthly else "attendance.trend.daily.v1",
                    business_method="obtener_tendencia_mensual" if prefers_monthly else "obtener_tendencia_diaria",
                    priority=80,
                    depends_on=list(dependencies or []),
                    requested_outputs=["series", "labels", "chart"],
                    business_objective="Generar visualizacion de tendencia de ausentismo.",
                    entity_scope=scope,
                    trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan"},
                )
            )

        tasks.append(
            DelegationTask(
                task_id=build_task_id("del"),
                run_id=run_id,
                domain_code=domain.domain_code,
                domain_status=domain.domain_status,
                task_type="insights_basicos",
                capability_id="attendance.summary.by_supervisor.v1",
                business_method="construir_insights_basicos",
                priority=70,
                depends_on=list(dependencies or []),
                requested_outputs=["insights"],
                business_objective="Sugerir posibles causas iniciales de variacion.",
                entity_scope=scope,
                trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan"},
            )
        )

        if not wants_trend:
            for item in tasks:
                if item.task_type.startswith("tendencia_"):
                    item.priority = 60
        return tasks

    @staticmethod
    def _plan_sql_assisted_task(
        *,
        domain: DomainDescriptor,
        message: str,
        run_id: str,
        trace_id: str,
    ) -> DelegationTask | None:
        if not str(message or "").strip():
            return None
        return DelegationTask(
            task_id=build_task_id("del"),
            run_id=run_id,
            domain_code=domain.domain_code,
            domain_status=domain.domain_status,
            task_type="exploracion_sql_asistida",
            business_method="consulta_exploratoria_restringida",
            priority=40,
            requested_outputs=["table", "kpis"],
            business_objective=f"Exploracion analitica controlada para dominio {domain.domain_code}.",
            entity_scope=EntityScope(entity_type="empresa"),
            constraints={
                "sql_mode": "read_only_restricted",
                "allow_only_select": True,
                "require_limit": True,
                "max_limit": 500,
            },
            trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan"},
            execution_strategy="sql_assisted_read_only",
        )

    def _plan_empleados_tasks(
        self,
        *,
        domain: DomainDescriptor | None,
        message: str,
        run_id: str,
        trace_id: str,
    ) -> list[DelegationTask]:
        if domain is None:
            return []
        if not any(token in str(message or "").lower() for token in ("empleado", "supervisor", "area", "cargo", "carpeta")):
            return []
        return [
            DelegationTask(
                task_id=build_task_id("del"),
                run_id=run_id,
                domain_code="empleados",
                domain_status=domain.domain_status,
                task_type="resolver_entidad_objetivo",
                capability_id="empleados.entity.resolve.v1",
                capability="empleados.entity.resolve.v1",
                business_method="resolver_entidad_objetivo",
                priority=95,
                requested_outputs=["entity_scope", "table", "kpis"],
                business_objective="Resolver entidad objetivo para enriquecer dominios relacionados.",
                entity_scope=EntityScope(entity_type="empresa"),
                trace_context={"trace_id": trace_id, "origin_phase": "delegation_plan", "message": message},
            )
        ]

    @staticmethod
    def _find_domain(*, domains: list[DomainDescriptor], code: str) -> DomainDescriptor | None:
        normalized = str(code or "").strip().lower()
        for item in domains:
            if str(item.domain_code or "").strip().lower() == normalized:
                return item
        return None

    @staticmethod
    def _is_analytics_request(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(
            token in normalized
            for token in (
                "compar",
                "grafica",
                "grafico",
                "chart",
                "tendencia",
                "por supervisor",
                "resumen",
            )
        )

    @staticmethod
    def _wants_chart(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(token in normalized for token in ("grafica", "grafico", "chart", "barras", "linea", "line"))

    @staticmethod
    def _wants_trend(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(token in normalized for token in ("tendencia", "evolucion", "historico", "historica"))

    @staticmethod
    def _prefers_monthly(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(token in normalized for token in ("mensual", "por mes", "mes a mes", "ultimo mes", "ultimos meses"))
