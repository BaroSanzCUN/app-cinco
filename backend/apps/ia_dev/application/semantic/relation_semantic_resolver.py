from __future__ import annotations

from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    RelationSemanticResolution,
)


class RelationSemanticResolver:
    """
    Resolver de relaciones/joins permitidos usando dd_relaciones y relaciones de dominio.
    """

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        return str(value or "").strip().lower()

    def build_relation_profiles(
        self,
        *,
        runtime_relationships: list[dict[str, Any]] | None = None,
        dictionary_relations: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        profiles: list[dict[str, Any]] = []

        for row in list(runtime_relationships or []):
            if not isinstance(row, dict):
                continue
            join_sql = str(row.get("condicion") or row.get("condicion_join_sql") or "").strip()
            if not join_sql:
                continue
            profiles.append(
                {
                    "relation_name": str(row.get("nombre_relacion") or "").strip(),
                    "join_sql": join_sql,
                    "cardinality": str(row.get("cardinalidad") or "").strip(),
                    "confidence": 0.78,
                }
            )

        for row in list(dictionary_relations or []):
            if not isinstance(row, dict):
                continue
            join_sql = str(row.get("join_sql") or "").strip()
            if not join_sql:
                continue
            profiles.append(
                {
                    "relation_name": str(row.get("nombre_relacion") or "").strip(),
                    "join_sql": join_sql,
                    "cardinality": str(row.get("cardinalidad") or "").strip(),
                    "confidence": 0.92,
                }
            )
        return profiles

    def resolve_required_relations(
        self,
        *,
        semantic_context: dict[str, Any],
        requested_terms: list[str] | None = None,
    ) -> list[RelationSemanticResolution]:
        relations = list(semantic_context.get("relation_profiles") or [])
        if not relations:
            return []

        requested = {self._normalize_text(item) for item in list(requested_terms or []) if self._normalize_text(item)}
        resolved: list[RelationSemanticResolution] = []
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            name = str(relation.get("relation_name") or "").strip()
            join_sql = str(relation.get("join_sql") or "").strip()
            if not join_sql:
                continue
            lower_join = self._normalize_text(join_sql)
            if requested and not any(term in lower_join for term in requested):
                # Conservador: si hay requested_terms, solo relaciones que ayuden a esos terminos.
                continue
            resolved.append(
                RelationSemanticResolution(
                    from_entity="",
                    to_entity="",
                    relation_name=name,
                    join_sql=join_sql,
                    cardinality=str(relation.get("cardinality") or ""),
                    valid=True,
                    confidence=float(relation.get("confidence") or 0.0),
                )
            )
        return resolved
