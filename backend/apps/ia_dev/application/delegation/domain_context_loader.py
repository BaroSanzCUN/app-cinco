from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from apps.ia_dev.services.sql_store import IADevSqlStore


class DomainContextLoader:
    def __init__(
        self,
        *,
        registry_dir: str | Path | None = None,
        store: IADevSqlStore | None = None,
    ):
        if registry_dir is None:
            registry_dir = Path(__file__).resolve().parents[2] / "domains" / "registry"
        self.registry_dir = Path(registry_dir)
        self.store = store or IADevSqlStore()

    def load_all(self) -> dict[str, dict[str, Any]]:
        file_contexts = self.load_from_files()
        db_contexts = self.load_from_db()
        merged: dict[str, dict[str, Any]] = {}
        all_codes = set(file_contexts.keys()) | set(db_contexts.keys())
        for code in sorted(all_codes):
            merged[code] = self._merge_context(
                file_context=file_contexts.get(code),
                db_context=db_contexts.get(code),
            )
        return merged

    def load_from_files(self) -> dict[str, dict[str, Any]]:
        contexts: dict[str, dict[str, Any]] = {}
        if not self.registry_dir.exists():
            return contexts
        for path in sorted(self.registry_dir.glob("*.domain.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            normalized = self._normalize_file_context(raw=raw, source_path=path)
            code = str(normalized.get("domain_code") or "").strip().lower()
            if not code:
                continue
            contexts[code] = normalized
        return contexts

    def load_from_db(self) -> dict[str, dict[str, Any]]:
        contexts: dict[str, dict[str, Any]] = {}
        list_dominios = getattr(self.store, "list_dominios", None)
        if not callable(list_dominios):
            return contexts
        try:
            rows = list_dominios(limit=300)
        except Exception:
            return contexts
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("codigo_dominio") or row.get("domain_code") or "").strip().lower()
            if not code:
                continue
            domain_id = int(row.get("id") or 0)
            tables = self._load_domain_tables(domain_id=domain_id)
            columns = self._load_domain_columns(domain_id=domain_id)
            relationships = self._load_domain_relationships(domain_id=domain_id)
            capabilities = self._load_domain_capabilities(domain_id=domain_id)
            skills = self._load_domain_skills(domain_id=domain_id)
            contexts[code] = {
                "domain_code": code,
                "domain_name": str(row.get("nombre_dominio") or code),
                "business_goal": str(row.get("objetivo_negocio") or ""),
                "main_entity": str(row.get("entidad_principal") or ""),
                "domain_status": str(row.get("estado_dominio") or row.get("status") or "planned").strip().lower(),
                "maturity_level": str(row.get("nivel_madurez") or "initial").strip().lower(),
                "schema_confidence": float(row.get("nivel_confianza_esquema") or 0.0),
                "flags": dict(row.get("flags_json") or {}),
                "source_of_truth": "db",
                "source_ref": str(row.get("source_ref") or ""),
                "tables": tables,
                "columns": columns,
                "relationships": relationships,
                "capabilities": capabilities,
                "skills": skills,
            }
        return contexts

    @staticmethod
    def _normalize_file_context(*, raw: dict[str, Any], source_path: Path) -> dict[str, Any]:
        code = str(raw.get("dominio") or raw.get("domain_code") or source_path.stem.split(".", 1)[0]).strip().lower()
        return {
            "domain_code": code,
            "domain_name": str(raw.get("nombre_dominio") or raw.get("domain_name") or code),
            "business_goal": str(raw.get("objetivo_negocio") or raw.get("business_goal") or ""),
            "main_entity": str(raw.get("entidad_principal") or raw.get("main_entity") or ""),
            "domain_status": str(raw.get("estado_dominio") or raw.get("domain_status") or "planned").strip().lower(),
            "maturity_level": str(raw.get("nivel_madurez") or raw.get("maturity_level") or "initial").strip().lower(),
            "schema_confidence": float(raw.get("nivel_confianza_esquema") or raw.get("schema_confidence") or 0.0),
            "flags": dict(raw.get("flags") or {}),
            "source_of_truth": "file",
            "source_ref": str(source_path),
            "tables": list(raw.get("tablas_asociadas") or raw.get("tables") or []),
            "columns": list(raw.get("columnas_clave") or raw.get("columns") or []),
            "relationships": list(raw.get("joins_conocidos") or raw.get("relationships") or []),
            "capabilities": list(raw.get("capacidades") or raw.get("capabilities") or []),
            "skills": list(raw.get("skills_metadata") or raw.get("skills") or []),
            "filtros_soportados": list(raw.get("filtros_soportados") or []),
            "group_by_soportados": list(raw.get("group_by_soportados") or []),
            "metricas_soportadas": list(raw.get("metricas_soportadas") or []),
            "sensitividades": list(raw.get("sensitividades") or []),
        }

    @staticmethod
    def _merge_context(
        *,
        file_context: dict[str, Any] | None,
        db_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        file_payload = dict(file_context or {})
        db_payload = dict(db_context or {})
        if not file_payload:
            return db_payload
        if not db_payload:
            return file_payload

        merged = dict(file_payload)
        for key in (
            "domain_name",
            "business_goal",
            "main_entity",
            "domain_status",
            "maturity_level",
            "schema_confidence",
        ):
            if db_payload.get(key) not in (None, ""):
                merged[key] = db_payload.get(key)
        merged["flags"] = {**dict(file_payload.get("flags") or {}), **dict(db_payload.get("flags") or {})}
        if db_payload.get("tables"):
            merged["tables"] = list(db_payload.get("tables") or [])
        if db_payload.get("columns"):
            merged["columns"] = list(db_payload.get("columns") or [])
        if db_payload.get("relationships"):
            merged["relationships"] = list(db_payload.get("relationships") or [])
        if db_payload.get("capabilities"):
            merged["capabilities"] = list(db_payload.get("capabilities") or [])
        if db_payload.get("skills"):
            merged["skills"] = list(db_payload.get("skills") or [])
        merged["source_of_truth"] = "hybrid"
        merged["source_ref"] = str(db_payload.get("source_ref") or file_payload.get("source_ref") or "")
        return merged

    def _load_domain_tables(self, *, domain_id: int) -> list[dict[str, Any]]:
        if domain_id <= 0:
            return []
        getter = getattr(self.store, "list_tablas_dominio", None)
        if not callable(getter):
            return []
        try:
            return list(getter(dominio_id=domain_id, status="active", limit=200))
        except Exception:
            return []

    def _load_domain_columns(self, *, domain_id: int) -> list[dict[str, Any]]:
        if domain_id <= 0:
            return []
        getter = getattr(self.store, "list_columnas_dominio", None)
        if not callable(getter):
            return []
        try:
            return list(getter(dominio_id=domain_id, status="active", limit=1000))
        except Exception:
            return []

    def _load_domain_relationships(self, *, domain_id: int) -> list[dict[str, Any]]:
        if domain_id <= 0:
            return []
        getter = getattr(self.store, "list_relaciones_dominio", None)
        if not callable(getter):
            return []
        try:
            return list(getter(dominio_id=domain_id, status="active", limit=1000))
        except Exception:
            return []

    def _load_domain_capabilities(self, *, domain_id: int) -> list[dict[str, Any]]:
        if domain_id <= 0:
            return []
        getter = getattr(self.store, "list_capacidades_dominio", None)
        if not callable(getter):
            return []
        try:
            return list(getter(dominio_id=domain_id, status="active", limit=200))
        except Exception:
            return []

    def _load_domain_skills(self, *, domain_id: int) -> list[dict[str, Any]]:
        if domain_id <= 0:
            return []
        getter = getattr(self.store, "list_skills_dominio", None)
        if not callable(getter):
            return []
        try:
            return list(getter(dominio_id=domain_id, status="active", limit=200))
        except Exception:
            return []
