from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.delegation.delegation_coordinator import DelegationCoordinator
from apps.ia_dev.application.delegation.task_contracts import DelegationResult


class DelegationActiveModeTests(SimpleTestCase):
    def test_active_mode_executes_multi_domain_tasks_and_aggregates(self):
        coordinator = DelegationCoordinator()
        run_context = RunContext.create(
            message="comparame ausentismo por supervisor, muestralo en grafica y sugiere causas"
        )

        coordinator.empleados_handler.resolver_subtarea = MagicMock(
            return_value=DelegationResult(
                task_id="del_emp_01",
                domain_code="empleados",
                status="ok",
                table={
                    "columns": ["cedula", "supervisor"],
                    "rows": [{"cedula": "101", "supervisor": "SUP-1"}],
                    "rowcount": 1,
                },
                kpis={"total_empleados_resueltos": 1},
            )
        )
        coordinator.ausentismo_handler.resolver_subtarea = MagicMock(
            return_value=DelegationResult(
                task_id="del_aus_01",
                domain_code="ausentismo",
                status="ok",
                kpis={"total_injustificados": 6, "total_grupos": 2},
                table={
                    "columns": ["supervisor", "total_injustificados"],
                    "rows": [
                        {"supervisor": "SUP-1", "total_injustificados": 4},
                        {"supervisor": "SUP-2", "total_injustificados": 2},
                    ],
                    "rowcount": 2,
                },
                labels=["SUP-1", "SUP-2"],
                series=[4, 2],
                chart={
                    "type": "bar",
                    "labels": ["SUP-1", "SUP-2"],
                    "series": [4, 2],
                },
                insights=["Insight de prueba"],
            )
        )

        with patch.dict(
            "os.environ",
            {
                "IA_DEV_DELEGATION_ENABLED": "1",
                "IA_DEV_DELEGATION_MODE": "active",
            },
            clear=False,
        ):
            result = coordinator.plan_and_maybe_execute(
                message="comparame ausentismo por supervisor, muestralo en grafica y sugiere causas",
                classification={
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "selected_agent": "attendance_agent",
                    "needs_database": True,
                    "output_mode": "summary",
                },
                planned_candidates=[
                    {
                        "capability_id": "attendance.summary.by_supervisor.v1",
                        "reason": "semantic",
                    }
                ],
                run_context=run_context,
                observability=None,
            )

        self.assertEqual(str(result.get("mode") or ""), "active")
        self.assertTrue(bool(result.get("executed")))
        response = dict(result.get("response") or {})
        data = dict(response.get("data") or {})
        self.assertTrue(bool(data.get("kpis")))
        self.assertTrue(bool(data.get("table")))
        self.assertTrue(bool(data.get("chart") or data.get("charts")))
        delegation_meta = dict((response.get("orchestrator") or {}).get("delegation") or {})
        self.assertTrue(bool(delegation_meta))
        self.assertTrue(bool(delegation_meta.get("is_multi_domain")))
