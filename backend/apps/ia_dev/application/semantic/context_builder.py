from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.semantic.semantic_business_resolver import (
    SemanticBusinessResolver,
)


class ContextBuilder:
    """
    Capa incremental para encapsular la construccion de contexto semantico.
    - Mantiene salida compatible con QueryIntentResolver.
    - Enriquecimiento no disruptivo en `context_builder`.
    - Reusa snapshot por run para evitar consultas duplicadas a ai_dictionary.
    """

    _SNAPSHOT_METADATA_KEY = "semantic_context_snapshots"

    def __init__(
        self,
        *,
        semantic_business_resolver: SemanticBusinessResolver | None = None,
    ):
        self.semantic_business_resolver = semantic_business_resolver or SemanticBusinessResolver()

    def build(
        self,
        *,
        domain_code: str,
        include_dictionary: bool,
        run_context: RunContext | None,
        observability=None,
        legacy_context: dict[str, Any] | None = None,
        active: bool = False,
        shadow: bool = False,
    ) -> dict[str, Any]:
        normalized_domain = self.semantic_business_resolver.registry.normalize_domain_code(domain_code)
        include_dictionary_flag = bool(include_dictionary)
        snapshot_key = self._snapshot_key(
            domain_code=normalized_domain,
            include_dictionary=include_dictionary_flag,
        )
        source = "semantic_business_resolver"
        reused_snapshot = False

        if isinstance(legacy_context, dict) and legacy_context:
            base_context = copy.deepcopy(legacy_context)
            source = "legacy_context_input"
        else:
            base_context = self._load_snapshot(
                run_context=run_context,
                snapshot_key=snapshot_key,
            )
            if base_context:
                source = "run_context_snapshot"
                reused_snapshot = True
            else:
                base_context = copy.deepcopy(
                    self.semantic_business_resolver.build_semantic_context(
                        domain_code=normalized_domain,
                        include_dictionary=include_dictionary_flag,
                    )
                )
                self._store_snapshot(
                    run_context=run_context,
                    snapshot_key=snapshot_key,
                    context=base_context,
                )

        enriched_context = copy.deepcopy(base_context)
        enriched_context["context_builder"] = {
            "active": bool(active),
            "shadow": bool(shadow),
            "domain_code": str(normalized_domain or ""),
            "include_dictionary": include_dictionary_flag,
            "source": source,
            "reused_snapshot": reused_snapshot,
            "snapshot_key": snapshot_key,
            "context_signature": self._signature(enriched_context),
        }

        differences = self._diff_against_legacy(
            legacy_context=legacy_context,
            candidate_context=enriched_context,
        )
        meta = {
            "active": bool(active),
            "shadow": bool(shadow),
            "domain_code": str(normalized_domain or ""),
            "include_dictionary": include_dictionary_flag,
            "source": source,
            "reused_snapshot": reused_snapshot,
            "snapshot_key": snapshot_key,
            "differences": differences,
            "differences_count": len(differences),
            "output": {
                "table_count": len(list(enriched_context.get("tables") or [])),
                "column_count": len(list(enriched_context.get("columns") or [])),
                "relationship_count": len(list(enriched_context.get("relationships") or [])),
                "dictionary_field_count": len(list((enriched_context.get("dictionary") or {}).get("fields") or [])),
                "dictionary_synonym_count": len(list((enriched_context.get("dictionary") or {}).get("synonyms") or [])),
            },
        }
        self._record_event(
            observability=observability,
            run_context=run_context,
            event_type="context_builder_resolved",
            meta={
                **meta,
                "input": {
                    "domain_code": str(domain_code or ""),
                    "normalized_domain_code": str(normalized_domain or ""),
                    "include_dictionary": include_dictionary_flag,
                    "has_legacy_context": bool(legacy_context),
                },
                "decision": {
                    "used_snapshot": reused_snapshot,
                    "selected_source": source,
                },
            },
        )
        return {
            "context": enriched_context,
            "meta": meta,
        }

    @classmethod
    def _snapshot_key(cls, *, domain_code: str, include_dictionary: bool) -> str:
        return f"{str(domain_code or '').strip().lower()}|dict:{int(bool(include_dictionary))}"

    @classmethod
    def _load_snapshot(
        cls,
        *,
        run_context: RunContext | None,
        snapshot_key: str,
    ) -> dict[str, Any]:
        if run_context is None:
            return {}
        snapshots = dict(run_context.metadata.get(cls._SNAPSHOT_METADATA_KEY) or {})
        value = snapshots.get(snapshot_key)
        if not isinstance(value, dict):
            return {}
        return copy.deepcopy(value)

    @classmethod
    def _store_snapshot(
        cls,
        *,
        run_context: RunContext | None,
        snapshot_key: str,
        context: dict[str, Any],
    ) -> None:
        if run_context is None:
            return
        snapshots = dict(run_context.metadata.get(cls._SNAPSHOT_METADATA_KEY) or {})
        snapshots[snapshot_key] = copy.deepcopy(dict(context or {}))
        run_context.metadata[cls._SNAPSHOT_METADATA_KEY] = snapshots

    @staticmethod
    def _signature(context: dict[str, Any]) -> str:
        sanitized = copy.deepcopy(dict(context or {}))
        sanitized.pop("context_builder", None)
        raw = json.dumps(sanitized, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]

    def _diff_against_legacy(
        self,
        *,
        legacy_context: dict[str, Any] | None,
        candidate_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not isinstance(legacy_context, dict) or not legacy_context:
            return []
        differences: list[dict[str, Any]] = []
        base_signature = self._signature(legacy_context)
        candidate_signature = self._signature(candidate_context)
        if base_signature != candidate_signature:
            differences.append(
                {
                    "type": "semantic_context_signature_mismatch",
                    "base_signature": base_signature,
                    "candidate_signature": candidate_signature,
                }
            )
        base_keys = sorted(list(dict(legacy_context).keys()))
        candidate_keys = sorted(
            [key for key in dict(candidate_context).keys() if str(key) != "context_builder"]
        )
        if base_keys != candidate_keys:
            differences.append(
                {
                    "type": "semantic_context_top_level_keys_mismatch",
                    "base_keys": base_keys,
                    "candidate_keys": candidate_keys,
                }
            )
        return differences

    @staticmethod
    def _record_event(
        *,
        observability,
        run_context: RunContext | None,
        event_type: str,
        meta: dict[str, Any],
    ) -> None:
        if observability is None or not hasattr(observability, "record_event"):
            return
        payload = {
            "run_id": getattr(run_context, "run_id", ""),
            "trace_id": getattr(run_context, "trace_id", ""),
            **dict(meta or {}),
        }
        observability.record_event(
            event_type=event_type,
            source="ContextBuilder",
            meta=payload,
        )
