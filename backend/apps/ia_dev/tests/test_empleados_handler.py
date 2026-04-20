from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.domains.empleados.handler import EmpleadosHandler


class _FakeEmpleadoService:
    def __init__(self):
        self.last_group_query_params = None
        self.last_group_by_field = None
        self.last_list_query_params = None

    def contar_agrupado_runtime(self, *, query_params, group_by_field, limit=100):
        self.last_group_query_params = dict(query_params or {})
        self.last_group_by_field = list(group_by_field) if isinstance(group_by_field, list) else str(group_by_field or "")
        if isinstance(group_by_field, list) and len(group_by_field) > 1:
            return [
                {"tipo_labor": "HFC", "area": "Operaciones", "total_empleados": 4},
                {"tipo_labor": "FTTH", "area": "Operaciones", "total_empleados": 3},
                {"tipo_labor": "", "area": "Implementacion", "total_empleados": 1},
            ]
        return [
            {"cargo": "Tecnico", "total_empleados": 7},
            {"cargo": "", "total_empleados": 2},
        ]

    def listar(self, query_params):
        self.last_list_query_params = dict(query_params or {})
        return _FakeListadoQuerySet()


class _FakeListadoQuerySet:
    def values(self, *fields):
        return [
            {
                "id": 11,
                "cedula": "98711054",
                "nombre": "Ana",
                "apellido": "Rios",
                "movil": "TIRAN462",
                "cargo": "Tecnico",
                "area": "Operaciones",
                "supervisor": "10203040",
                "carpeta": "N1",
                "tipo_labor": "HFC",
                "estado": "ACTIVO",
                "codigo_sap": "SAP-11",
                "sede": "Bogota",
                "link_foto": "",
            },
            {
                "id": 12,
                "cedula": "99887766",
                "nombre": "Luis",
                "apellido": "Diaz",
                "movil": "TIRAN462",
                "cargo": "Auxiliar",
                "area": "Operaciones",
                "supervisor": "10203040",
                "carpeta": "N2",
                "tipo_labor": "FTTH",
                "estado": "ACTIVO",
                "codigo_sap": "SAP-12",
                "sede": "Bogota",
                "link_foto": "",
            },
        ]


class EmpleadosHandlerTests(SimpleTestCase):
    def test_handle_resuelve_conteo_agrupado_por_cargo_desde_semantica(self):
        handler = EmpleadosHandler(service=_FakeEmpleadoService())
        intent = StructuredQueryIntent(
            raw_query="cantidad de empleados activos con el cargo por cargo",
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={"estado": "ACTIVO"},
            group_by=["cargo"],
            metrics=["count"],
            confidence=0.92,
            source="rules",
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context={
                "resolved_semantic": {
                    "group_by": [
                        {
                            "requested_term": "cargo",
                            "canonical_term": "cargo",
                            "column_name": "cargo",
                        }
                    ]
                },
                "aliases": {"cargo": "cargo"},
            },
            normalized_filters={"estado": "ACTIVO"},
            normalized_period={},
            mapped_columns={"estado": "estado"},
        )
        execution_plan = QueryExecutionPlan(
            strategy="capability",
            reason="capability_selected_from_query_intelligence",
            domain_code="empleados",
            capability_id="empleados.count.active.v1",
            constraints={
                "filters": {"estado": "ACTIVO"},
                "group_by": ["cargo"],
                "result_shape": "table",
            },
        )

        with patch("apps.ia_dev.domains.empleados.handler.SessionMemoryStore.get_or_create", return_value=("sid-1", {})), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.update_context"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.append_turn"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.status",
            return_value={"used_messages": 0},
        ):
            result = handler.handle(
                capability_id="empleados.count.active.v1",
                message=intent.raw_query,
                session_id="sid-1",
                reset_memory=False,
                run_context=RunContext.create(message=intent.raw_query, session_id="sid-1"),
                planned_capability={"capability_id": "empleados.count.active.v1"},
                resolved_query=resolved_query,
                execution_plan=execution_plan,
            )

        self.assertTrue(result.ok)
        response = dict(result.response or {})
        rows = list(((response.get("data") or {}).get("table") or {}).get("rows") or [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"cargo": "Tecnico", "cantidad": 7})
        self.assertEqual(rows[1], {"cargo": "SIN_DATO", "cantidad": 2})
        self.assertEqual(int(((response.get("data") or {}).get("kpis") or {}).get("total_empleados") or 0), 9)
        self.assertIn("por cargo", str(response.get("reply") or "").lower())
        self.assertEqual(handler.service.last_group_query_params, {"estado": "ACTIVO"})
        self.assertEqual(handler.service.last_group_by_field, ["cargo"])

    def test_handle_resuelve_conteo_agrupado_por_tipo_labor_y_area(self):
        handler = EmpleadosHandler(service=_FakeEmpleadoService())
        intent = StructuredQueryIntent(
            raw_query="cantidad de tipo de labor por area",
            domain_code="empleados",
            operation="count",
            template_id="aggregate_by_group_and_period",
            filters={"estado": "ACTIVO"},
            group_by=["tipo_labor", "area"],
            metrics=["count"],
            confidence=0.93,
            source="rules",
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context={
                "resolved_semantic": {
                    "group_by": [
                        {
                            "requested_term": "tipo_labor",
                            "canonical_term": "tipo_labor",
                            "column_name": "tipo_labor",
                        },
                        {
                            "requested_term": "area",
                            "canonical_term": "area",
                            "column_name": "area",
                        },
                    ]
                },
                "aliases": {"tipo_labor": "tipo_labor", "area": "area"},
            },
            normalized_filters={"estado": "ACTIVO"},
            normalized_period={},
            mapped_columns={"estado": "estado", "tipo_labor": "tipo_labor", "area": "area"},
        )
        execution_plan = QueryExecutionPlan(
            strategy="capability",
            reason="capability_selected_from_query_intelligence",
            domain_code="empleados",
            capability_id="empleados.count.active.v1",
            constraints={
                "filters": {"estado": "ACTIVO"},
                "group_by": ["tipo_labor", "area"],
                "result_shape": "table",
            },
        )

        with patch("apps.ia_dev.domains.empleados.handler.SessionMemoryStore.get_or_create", return_value=("sid-1", {})), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.update_context"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.append_turn"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.status",
            return_value={"used_messages": 0},
        ):
            result = handler.handle(
                capability_id="empleados.count.active.v1",
                message=intent.raw_query,
                session_id="sid-1",
                reset_memory=False,
                run_context=RunContext.create(message=intent.raw_query, session_id="sid-1"),
                planned_capability={"capability_id": "empleados.count.active.v1"},
                resolved_query=resolved_query,
                execution_plan=execution_plan,
            )

        self.assertTrue(result.ok)
        response = dict(result.response or {})
        table = (response.get("data") or {}).get("table") or {}
        rows = list(table.get("rows") or [])
        self.assertEqual(list(table.get("columns") or []), ["tipo_labor", "area", "cantidad"])
        self.assertEqual(rows[0], {"tipo_labor": "HFC", "area": "Operaciones", "cantidad": 4})
        self.assertEqual(rows[2], {"tipo_labor": "SIN_DATO", "area": "Implementacion", "cantidad": 1})
        self.assertIn("por tipo_labor y area", str(response.get("reply") or "").lower())
        self.assertEqual(handler.service.last_group_by_field, ["tipo_labor", "area"])

    def test_extract_after_keyword_ignora_placeholder_de_group_by(self):
        value = EmpleadosHandler._extract_after_keyword(
            "cantidad de empleados activos con el cargo por cargo",
            keyword="cargo",
        )
        self.assertEqual(value, "")

    def test_extract_after_keyword_ignora_por_suelto_como_placeholder_de_group_by(self):
        value = EmpleadosHandler._extract_after_keyword(
            "cantidad de tipo de labor por area",
            keyword="labor",
        )
        self.assertEqual(value, "")

    def test_handle_resuelve_detalle_por_movil(self):
        handler = EmpleadosHandler(service=_FakeEmpleadoService())
        intent = StructuredQueryIntent(
            raw_query="informacion de TIRAN462",
            domain_code="empleados",
            operation="detail",
            template_id="detail_by_entity_and_period",
            entity_type="movil",
            entity_value="TIRAN462",
            filters={"movil": "TIRAN462"},
            period={},
            group_by=[],
            metrics=[],
            confidence=0.88,
            source="rules",
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context={},
            normalized_filters={"movil": "TIRAN462"},
            normalized_period={},
            mapped_columns={"movil": "movil"},
        )
        execution_plan = QueryExecutionPlan(
            strategy="capability",
            reason="capability_selected_from_query_intelligence",
            domain_code="empleados",
            capability_id="empleados.detail.v1",
            constraints={
                "filters": {"movil": "TIRAN462"},
                "result_shape": "table",
            },
        )

        with patch("apps.ia_dev.domains.empleados.handler.SessionMemoryStore.get_or_create", return_value=("sid-1", {})), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.update_context"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.append_turn"
        ), patch(
            "apps.ia_dev.domains.empleados.handler.SessionMemoryStore.status",
            return_value={"used_messages": 0},
        ):
            result = handler.handle(
                capability_id="empleados.detail.v1",
                message=intent.raw_query,
                session_id="sid-1",
                reset_memory=False,
                run_context=RunContext.create(message=intent.raw_query, session_id="sid-1"),
                planned_capability={"capability_id": "empleados.detail.v1"},
                resolved_query=resolved_query,
                execution_plan=execution_plan,
            )

        self.assertTrue(result.ok)
        response = dict(result.response or {})
        table = (response.get("data") or {}).get("table") or {}
        rows = list(((response.get("data") or {}).get("table") or {}).get("rows") or [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(str(rows[0].get("movil") or ""), "TIRAN462")
        self.assertEqual(
            list(table.get("columns") or []),
            ["cedula", "nombre", "apellido", "cargo", "area", "carpeta", "tipo_labor", "movil"],
        )
        self.assertIn("integrantes de la movil tiran462", str(response.get("reply") or "").lower())
        self.assertIn("si deseas conocer algo especifico adicional de esta movil", str(response.get("reply") or "").lower())
        self.assertEqual(handler.service.last_list_query_params, {"movil": "TIRAN462"})
