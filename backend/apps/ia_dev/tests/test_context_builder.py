from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.semantic.context_builder import ContextBuilder


class _FakeRegistry:
    @staticmethod
    def normalize_domain_code(value: str | None) -> str:
        return str(value or "").strip().lower() or "general"


class _FakeSemanticBusinessResolver:
    def __init__(self):
        self.registry = _FakeRegistry()
        self.calls = 0

    def build_semantic_context(self, *, domain_code: str, include_dictionary: bool = True) -> dict:
        self.calls += 1
        return {
            "domain_code": domain_code,
            "tables": [{"table_name": "tabla_demo", "table_fqn": "public.tabla_demo"}],
            "columns": [{"column_name": "col_demo", "nombre_columna_logico": "demo"}],
            "relationships": [],
            "dictionary": {
                "fields": [],
                "relations": [],
                "rules": [],
                "synonyms": [],
                "field_profiles": [],
            },
        }


class ContextBuilderTests(SimpleTestCase):
    def test_uses_legacy_context_without_new_dictionary_fetch(self):
        resolver = _FakeSemanticBusinessResolver()
        builder = ContextBuilder(semantic_business_resolver=resolver)
        run_context = RunContext.create(message="hola", session_id="sess-a")
        legacy_context = resolver.build_semantic_context(domain_code="empleados", include_dictionary=True)

        payload = builder.build(
            domain_code="empleados",
            include_dictionary=True,
            run_context=run_context,
            legacy_context=legacy_context,
            active=False,
            shadow=True,
        )

        self.assertEqual(resolver.calls, 1)
        context = dict(payload.get("context") or {})
        meta = dict(payload.get("meta") or {})
        self.assertEqual(str((context.get("context_builder") or {}).get("source") or ""), "legacy_context_input")
        self.assertEqual(int(meta.get("differences_count") or 0), 0)

    def test_reuses_snapshot_on_second_build_within_same_run(self):
        resolver = _FakeSemanticBusinessResolver()
        builder = ContextBuilder(semantic_business_resolver=resolver)
        run_context = RunContext.create(message="consulta", session_id="sess-b")

        first = builder.build(
            domain_code="attendance",
            include_dictionary=True,
            run_context=run_context,
            active=True,
            shadow=False,
        )
        second = builder.build(
            domain_code="attendance",
            include_dictionary=True,
            run_context=run_context,
            active=True,
            shadow=False,
        )

        self.assertEqual(resolver.calls, 1)
        self.assertFalse(bool((dict(first.get("meta") or {})).get("reused_snapshot")))
        self.assertTrue(bool((dict(second.get("meta") or {})).get("reused_snapshot")))
