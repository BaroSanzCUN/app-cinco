from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from django.db import connections, transaction


class AIDictionaryRemediationService:
    """
    Remediacion idempotente de ai_dictionary para dominios empresariales
    priorizados sin eliminar compatibilidad.

    No elimina filas legacy; solo completa metadata estructural faltante para que
    el runtime pueda observar una fuente de verdad coherente con el esquema real.
    """

    DOMAIN_CODES = {
        "ausentismo": "AUSENTISMOS",
        "empleados": "EMPLEADOS",
        "transporte": "TRANSPORTE",
    }

    def __init__(self, *, db_alias: str | None = None, schema: str = "ai_dictionary") -> None:
        self.db_alias = str(db_alias or os.getenv("IA_DEV_DB_ALIAS", "default"))
        self.schema = str(schema or "ai_dictionary").strip() or "ai_dictionary"
        self.domains_dir = Path(__file__).resolve().parents[1] / "domains"

    def remediate(self, *, domain: str = "ausentismo", with_empleados: bool = False) -> dict[str, Any]:
        domains = [str(domain or "ausentismo").strip().lower() or "ausentismo"]
        if with_empleados and "empleados" not in domains:
            domains.append("empleados")

        summary = {
            "domains": list(domains),
            "domains_upserted": 0,
            "tables_upserted": 0,
            "fields_upserted": 0,
            "field_capabilities_upserted": 0,
            "relations_upserted": 0,
            "rules_upserted": 0,
            "synonyms_upserted": 0,
            "warnings": [],
        }

        with transaction.atomic(using=self.db_alias):
            with connections[self.db_alias].cursor() as cursor:
                physical_columns = self._load_physical_columns(cursor=cursor)
                for domain_code in domains:
                    manifest = self._build_domain_manifest(domain_code=domain_code)
                    domain_id, domain_changed = self._upsert_domain(
                        cursor=cursor,
                        domain_code=domain_code,
                        manifest=manifest,
                    )
                    if domain_changed:
                        summary["domains_upserted"] += 1

                    table_ids: dict[str, int] = {}
                    for table in list(manifest.get("tables") or []):
                        table_id, changed = self._upsert_table(
                            cursor=cursor,
                            domain_id=domain_id,
                            table=table,
                        )
                        if table_id > 0:
                            table_ids[str(table.get("table_name") or "").strip().lower()] = table_id
                        if changed:
                            summary["tables_upserted"] += 1

                    for field in list(manifest.get("fields") or []):
                        table_name = str(field.get("table_name") or "").strip().lower()
                        table_id = int(table_ids.get(table_name) or 0)
                        if table_id <= 0:
                            summary["warnings"].append(
                                f"missing_table_for_field:{domain_code}:{table_name}:{field.get('logical_name')}"
                            )
                            continue
                        column_name = str(field.get("column_name") or "").strip().lower()
                        schema_name = str(field.get("schema_name") or "").strip().lower()
                        if schema_name and column_name:
                            available_columns = physical_columns.get((schema_name, table_name), set())
                            if column_name not in available_columns:
                                summary["warnings"].append(
                                    f"missing_physical_column:{domain_code}:{table_name}.{column_name}"
                                )
                                continue
                        field_id, changed = self._upsert_field(
                            cursor=cursor,
                            table_id=table_id,
                            field=field,
                        )
                        if changed:
                            summary["fields_upserted"] += 1
                        if field_id > 0 and dict(field.get("capabilities") or {}):
                            if self._upsert_field_capabilities(
                                cursor=cursor,
                                field_id=field_id,
                                capabilities=dict(field.get("capabilities") or {}),
                            ):
                                summary["field_capabilities_upserted"] += 1

                    for relation in list(manifest.get("relations") or []):
                        source_table = str(relation.get("source_table") or "").strip().lower()
                        target_table = str(relation.get("target_table") or "").strip().lower()
                        source_table_id = int(table_ids.get(source_table) or 0)
                        target_table_id = int(table_ids.get(target_table) or 0)
                        if source_table_id <= 0 or target_table_id <= 0:
                            summary["warnings"].append(
                                f"missing_table_for_relation:{domain_code}:{relation.get('name')}"
                            )
                            continue
                        if self._upsert_relation(
                            cursor=cursor,
                            source_table_id=source_table_id,
                            target_table_id=target_table_id,
                            relation=relation,
                        ):
                            summary["relations_upserted"] += 1

                    for rule in list(manifest.get("rules") or []):
                        if self._upsert_rule(
                            cursor=cursor,
                            domain_id=domain_id,
                            rule=rule,
                        ):
                            summary["rules_upserted"] += 1

                    for synonym in list(manifest.get("synonyms") or []):
                        if self._upsert_synonym(
                            cursor=cursor,
                            domain_id=domain_id,
                            term=str(synonym[0]),
                            alias=str(synonym[1]),
                        ):
                            summary["synonyms_upserted"] += 1

        return summary

    def _build_domain_manifest(self, *, domain_code: str) -> dict[str, Any]:
        domain_file = self.domains_dir / domain_code / "dominio.yaml"
        rules_file = self.domains_dir / domain_code / "reglas.yaml"
        raw_domain = yaml.safe_load(domain_file.read_text(encoding="utf-8")) or {}
        raw_rules = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}

        fields = self._curated_fields(domain_code=domain_code)
        relations = self._curated_relations(domain_code=domain_code)
        synonyms = self._curated_synonyms(domain_code=domain_code)
        rules = [
            {
                "codigo": str(item.get("codigo") or "").strip().lower(),
                "nombre": str(item.get("codigo") or "").strip().replace("_", " "),
                "resultado_funcional": str(item.get("descripcion") or "").strip(),
                "prioridad": self._priority_value(str(item.get("prioridad") or "")),
            }
            for item in list(raw_rules.get("reglas_negocio") or [])
            if isinstance(item, dict) and str(item.get("codigo") or "").strip()
        ]
        return {
            "domain_name": str(raw_domain.get("nombre_dominio") or domain_code.title()).strip(),
            "description": str(raw_domain.get("objetivo_negocio") or f"Dominio {domain_code}").strip(),
            "tables": [
                {
                    "schema_name": str(item.get("schema_name") or "").strip().lower(),
                    "table_name": str(item.get("table_name") or "").strip().lower(),
                    "alias_negocio": str(item.get("nombre_tabla_logico") or item.get("table_name") or "").strip(),
                    "descripcion": f"Tabla estructural del dominio {domain_code}",
                    "clave_negocio": "cedula",
                }
                for item in list(raw_domain.get("tablas_asociadas") or [])
                if isinstance(item, dict) and str(item.get("table_name") or "").strip()
            ],
            "fields": fields,
            "relations": relations,
            "rules": rules,
            "synonyms": synonyms,
        }

    def _curated_fields(self, *, domain_code: str) -> list[dict[str, Any]]:
        if domain_code == "ausentismo":
            return [
                self._field("cincosas_cincosas", "gestionh_ausentismo", "cedula", "cedula", capabilities={"is_identifier": True}),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "fecha_edit", "fecha_ausentismo", capabilities={"is_date": True}),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "ausentismo", "ausentismo_flag", capabilities={"supports_filter": True}),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "justificacion", "justificacion", capabilities={"supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "causa_aus", "causa_aus"),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "ini_inca", "ini_inca"),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "tipo_inca", "tipo_inca"),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "codigo_inca", "codigo_inca"),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "desc_inca", "desc_inca"),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "ini_incapa", "ini_incapa", capabilities={"is_date": True}),
                self._field("cincosas_cincosas", "gestionh_ausentismo", "fin_incapa", "fin_incapa", capabilities={"is_date": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "cedula", "cedula_empleado", capabilities={"is_identifier": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "nombre", "nombre"),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "apellido", "apellido"),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "area", "area", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "cargo", "cargo", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "supervisor", "supervisor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "carpeta", "carpeta", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "movil", "movil"),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "tipo", "tipo_labor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "zona_nodo", "sede", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            ]
        if domain_code == "transporte":
            return [
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "cedula", "tecnico_cedula", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True, "is_identifier": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "cedula", "tecnico", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True, "is_identifier": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "fprogramacion", "fecha_programacion", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True, "is_date": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "fecha_edit", "fecha_actualizacion", capabilities={"supports_filter": True, "is_date": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "wp", "ruta", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "sitio", "sitio", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "estado", "estado", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "razon", "razon", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "proyecto", "proyecto", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "region", "region", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "ciudad", "ciudad", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "sv", "subvector", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "orden_compra", "orden_compra", capabilities={"supports_filter": True}),
                self._field("cincosas_cincosas", "nokia_base_ruta_programacion", "facturacion", "facturacion", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "cedula", "cedula_empleado", capabilities={"supports_filter": True, "is_identifier": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "nombre", "nombre_tecnico"),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "apellido", "apellido_tecnico"),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "supervisor", "supervisor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "area", "area", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "cargo", "cargo", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "carpeta", "carpeta", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "movil", "movil", capabilities={"supports_filter": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "tipo", "tipo_labor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "zona_nodo", "sede", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
                self._field("cincosas_cincosas", "cinco_base_de_personal", "estado", "estado_empleado", capabilities={"supports_filter": True}),
            ]
        return [
            self._field("cincosas_cincosas", "cinco_base_de_personal", "cedula", "cedula", capabilities={"supports_filter": True, "is_identifier": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "nombre", "nombre"),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "nombre", "nombre_empleado"),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "apellido", "apellido"),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "apellido", "apellido_empleado"),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "estado", "estado_empleado", capabilities={"supports_filter": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "supervisor", "supervisor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "area", "area", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "cargo", "cargo", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "carpeta", "carpeta", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "movil", "movil"),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "tipo", "tipo_labor", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "zona_nodo", "sede", capabilities={"supports_filter": True, "supports_group_by": True, "supports_dimension": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "fnacimiento", "fecha_nacimiento", capabilities={"is_date": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "fecha_ingreso", "fecha_ingreso", capabilities={"supports_filter": True, "is_date": True}),
            self._field("cincosas_cincosas", "cinco_base_de_personal", "fecha_egreso", "fecha_egreso", capabilities={"supports_filter": True, "is_date": True}),
        ]

    def _curated_relations(self, *, domain_code: str) -> list[dict[str, Any]]:
        if domain_code == "ausentismo":
            return [
                {
                    "name": "ausentismo_empleado",
                    "source_table": "gestionh_ausentismo",
                    "target_table": "cinco_base_de_personal",
                    "join_sql": "gestionh_ausentismo.cedula = cinco_base_de_personal.cedula",
                    "cardinality": "many_to_one",
                    "description": "Relacion oficial para enriquecer ausentismo con datos del empleado.",
                }
            ]
        if domain_code == "transporte":
            return [
                {
                    "name": "ruta_programada_empleado",
                    "source_table": "nokia_base_ruta_programacion",
                    "target_table": "cinco_base_de_personal",
                    "join_sql": "nokia_base_ruta_programacion.cedula = cinco_base_de_personal.cedula",
                    "cardinality": "many_to_one",
                    "description": "Relacion oficial para enriquecer programacion de rutas con estructura organizacional del tecnico.",
                }
            ]
        return [
            {
                "name": "empleado_supervisor",
                "source_table": "cinco_base_de_personal",
                "target_table": "cinco_base_de_personal",
                "join_sql": "cinco_base_de_personal.supervisor = cinco_base_de_personal.cedula",
                "cardinality": "many_to_one",
                "description": "Relacion jerarquica empleado -> supervisor.",
            }
        ]

    def _curated_synonyms(self, *, domain_code: str) -> list[tuple[str, str]]:
        base = [("area", "areas"), ("cargo", "cargos"), ("empleado", "empleados"), ("sede", "sedes")]
        if domain_code == "ausentismo":
            base.extend([("ausentismo", "ausencia"), ("justificacion", "motivo")])
        if domain_code == "transporte":
            base.extend(
                [
                    ("ruta", "wp"),
                    ("ruta", "rutas"),
                    ("programacion", "programación"),
                    ("programacion", "agenda"),
                    ("tecnico", "tecnicos"),
                    ("tecnico", "técnico"),
                    ("ciudad", "zona"),
                    ("estado", "estatus"),
                ]
            )
        return base

    def _upsert_domain(
        self,
        *,
        cursor,
        domain_code: str,
        manifest: dict[str, Any],
    ) -> tuple[int, bool]:
        expected = self.DOMAIN_CODES.get(domain_code, str(domain_code or "").strip().upper())
        expected_name = str(manifest.get("domain_name") or domain_code.title()).strip()
        expected_description = str(manifest.get("description") or f"Dominio {domain_code}").strip()
        cursor.execute(
            f"""
            SELECT id, codigo, nombre, descripcion, activo
            FROM {self.schema}.dd_dominios
            WHERE UPPER(COALESCE(codigo, '')) = %s
               OR UPPER(COALESCE(nombre, '')) = %s
            ORDER BY CASE WHEN UPPER(COALESCE(codigo, '')) = %s THEN 0 ELSE 1 END, id
            LIMIT 1
            """,
            [expected, expected_name.upper(), expected],
        )
        row = cursor.fetchone()
        if row:
            changed = (
                str(row[1] or "").strip().upper() != expected
                or str(row[2] or "").strip() != expected_name
                or str(row[3] or "").strip() != expected_description
                or int(row[4] or 0) != 1
            )
            if changed:
                cursor.execute(
                    f"""
                    UPDATE {self.schema}.dd_dominios
                    SET codigo = %s,
                        nombre = %s,
                        descripcion = %s,
                        activo = 1
                    WHERE id = %s
                    """,
                    [expected, expected_name, expected_description, int(row[0])],
                )
            return int(row[0]), bool(changed)

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_dominios (
                codigo,
                nombre,
                descripcion,
                activo,
                creado_en
            ) VALUES (%s, %s, %s, 1, NOW())
            """,
            [expected, expected_name, expected_description],
        )
        return int(getattr(cursor, "lastrowid", 0) or 0), True

    @staticmethod
    def _field(
        schema_name: str,
        table_name: str,
        column_name: str,
        logical_name: str,
        *,
        capabilities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_name": str(schema_name or "").strip().lower(),
            "table_name": str(table_name or "").strip().lower(),
            "column_name": str(column_name or "").strip().lower(),
            "logical_name": str(logical_name or "").strip().lower(),
            "capabilities": dict(capabilities or {}),
        }

    @staticmethod
    def _priority_value(raw: str) -> int:
        token = str(raw or "").strip().lower()
        if token == "alta":
            return 10
        if token == "media":
            return 50
        if token == "baja":
            return 90
        return 50

    def _load_physical_columns(self, *, cursor) -> dict[tuple[str, str], set[str]]:
        cursor.execute(
            """
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE table_schema IN ('cincosas_cincosas', 'ai_dictionary')
            """
        )
        payload: dict[tuple[str, str], set[str]] = {}
        for schema_name, table_name, column_name in cursor.fetchall():
            key = (
                str(schema_name or "").strip().lower(),
                str(table_name or "").strip().lower(),
            )
            payload.setdefault(key, set()).add(str(column_name or "").strip().lower())
        return payload

    def _upsert_table(self, *, cursor, domain_id: int, table: dict[str, Any]) -> tuple[int, bool]:
        schema_name = str(table.get("schema_name") or "").strip().lower()
        table_name = str(table.get("table_name") or "").strip().lower()
        cursor.execute(
            f"""
            SELECT id, schema_name, alias_negocio, descripcion, clave_negocio, activo
            FROM {self.schema}.dd_tablas
            WHERE dominio_id = %s
              AND LOWER(COALESCE(table_name, '')) = %s
            ORDER BY id
            LIMIT 1
            """,
            [int(domain_id), table_name],
        )
        row = cursor.fetchone()
        if row:
            changed = (
                str(row[1] or "").strip().lower() != schema_name
                or str(row[2] or "").strip() != str(table.get("alias_negocio") or "").strip()
                or str(row[3] or "").strip() != str(table.get("descripcion") or "").strip()
                or str(row[4] or "").strip() != str(table.get("clave_negocio") or "").strip()
                or int(row[5] or 0) != 1
            )
            if changed:
                cursor.execute(
                    f"""
                    UPDATE {self.schema}.dd_tablas
                    SET schema_name = %s,
                        alias_negocio = %s,
                        descripcion = %s,
                        clave_negocio = %s,
                        activo = 1
                    WHERE id = %s
                    """,
                    [
                        schema_name,
                        str(table.get("alias_negocio") or "").strip(),
                        str(table.get("descripcion") or "").strip(),
                        str(table.get("clave_negocio") or "").strip(),
                        int(row[0]),
                    ],
                )
            return int(row[0]), bool(changed)

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_tablas (
                dominio_id,
                schema_name,
                table_name,
                alias_negocio,
                descripcion,
                clave_negocio,
                nivel_confianza,
                activo,
                creado_en
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            [
                int(domain_id),
                schema_name,
                table_name,
                str(table.get("alias_negocio") or "").strip(),
                str(table.get("descripcion") or "").strip(),
                str(table.get("clave_negocio") or "").strip(),
                "ALTO",
            ],
        )
        return int(getattr(cursor, "lastrowid", 0) or 0), True

    def _upsert_field(self, *, cursor, table_id: int, field: dict[str, Any]) -> tuple[int, bool]:
        logical_name = str(field.get("logical_name") or "").strip().lower()
        column_name = str(field.get("column_name") or "").strip().lower()
        cursor.execute(
            f"""
            SELECT id, column_name, campo_logico, activo
            FROM {self.schema}.dd_campos
            WHERE tabla_id = %s
              AND (
                LOWER(COALESCE(campo_logico, '')) = %s
                OR LOWER(COALESCE(column_name, '')) = %s
              )
            ORDER BY CASE WHEN LOWER(COALESCE(campo_logico, '')) = %s THEN 0 ELSE 1 END, id
            LIMIT 1
            """,
            [int(table_id), logical_name, column_name, logical_name],
        )
        row = cursor.fetchone()
        if row:
            changed = (
                str(row[1] or "").strip().lower() != column_name
                or str(row[2] or "").strip().lower() != logical_name
                or int(row[3] or 0) != 1
            )
            if changed:
                cursor.execute(
                    f"""
                    UPDATE {self.schema}.dd_campos
                    SET campo_logico = %s,
                        column_name = %s,
                        activo = 1
                    WHERE id = %s
                    """,
                    [logical_name, column_name, int(row[0])],
                )
            return int(row[0]), bool(changed)

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_campos (
                tabla_id,
                campo_logico,
                column_name,
                tipo_campo,
                tipo_dato_tecnico,
                definicion_negocio,
                valores_permitidos,
                ejemplo_valor,
                es_clave,
                activo,
                creado_en
            ) VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, %s, 1, NOW())
            """,
            [
                int(table_id),
                logical_name,
                column_name,
                "LITERAL",
                "",
                f"Campo remediado para {logical_name}",
                1 if bool(field.get("capabilities", {}).get("is_identifier")) else 0,
            ],
        )
        return int(getattr(cursor, "lastrowid", 0) or 0), True

    def _upsert_field_capabilities(self, *, cursor, field_id: int, capabilities: dict[str, Any]) -> bool:
        payload = {
            "supports_filter": 1 if bool(capabilities.get("supports_filter")) else 0,
            "supports_group_by": 1 if bool(capabilities.get("supports_group_by")) else 0,
            "supports_metric": 1 if bool(capabilities.get("supports_metric")) else 0,
            "supports_dimension": 1 if bool(capabilities.get("supports_dimension")) else 0,
            "is_date": 1 if bool(capabilities.get("is_date")) else 0,
            "is_identifier": 1 if bool(capabilities.get("is_identifier")) else 0,
            "is_chart_dimension": 1 if bool(capabilities.get("supports_group_by") or capabilities.get("supports_dimension")) else 0,
            "is_chart_measure": 1 if bool(capabilities.get("supports_metric")) else 0,
            "allowed_operators_json": "[]",
            "allowed_aggregations_json": "[]",
            "normalization_strategy": "phase7_dictionary_remediation",
            "priority": 50,
            "active": 1,
        }
        cursor.execute(
            f"""
            SELECT id,
                   supports_filter,
                   supports_group_by,
                   supports_metric,
                   supports_dimension,
                   is_date,
                   is_identifier,
                   is_chart_dimension,
                   is_chart_measure,
                   normalization_strategy,
                   priority,
                   active
            FROM {self.schema}.ia_dev_capacidades_columna
            WHERE campo_id = %s
            LIMIT 1
            """,
            [int(field_id)],
        )
        row = cursor.fetchone()
        if row:
            current = {
                "supports_filter": int(row[1] or 0),
                "supports_group_by": int(row[2] or 0),
                "supports_metric": int(row[3] or 0),
                "supports_dimension": int(row[4] or 0),
                "is_date": int(row[5] or 0),
                "is_identifier": int(row[6] or 0),
                "is_chart_dimension": int(row[7] or 0),
                "is_chart_measure": int(row[8] or 0),
                "normalization_strategy": str(row[9] or ""),
                "priority": int(row[10] or 0),
                "active": int(row[11] or 0),
            }
            if current == payload:
                return False
            cursor.execute(
                f"""
                UPDATE {self.schema}.ia_dev_capacidades_columna
                SET supports_filter = %s,
                    supports_group_by = %s,
                    supports_metric = %s,
                    supports_dimension = %s,
                    is_date = %s,
                    is_identifier = %s,
                    is_chart_dimension = %s,
                    is_chart_measure = %s,
                    allowed_operators_json = %s,
                    allowed_aggregations_json = %s,
                    normalization_strategy = %s,
                    priority = %s,
                    active = %s,
                    updated_at = UNIX_TIMESTAMP()
                WHERE id = %s
                """,
                [
                    payload["supports_filter"],
                    payload["supports_group_by"],
                    payload["supports_metric"],
                    payload["supports_dimension"],
                    payload["is_date"],
                    payload["is_identifier"],
                    payload["is_chart_dimension"],
                    payload["is_chart_measure"],
                    payload["allowed_operators_json"],
                    payload["allowed_aggregations_json"],
                    payload["normalization_strategy"],
                    payload["priority"],
                    payload["active"],
                    int(row[0]),
                ],
            )
            return True

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.ia_dev_capacidades_columna (
                campo_id,
                supports_filter,
                supports_group_by,
                supports_metric,
                supports_dimension,
                is_date,
                is_identifier,
                is_chart_dimension,
                is_chart_measure,
                allowed_operators_json,
                allowed_aggregations_json,
                normalization_strategy,
                priority,
                active,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UNIX_TIMESTAMP(), UNIX_TIMESTAMP())
            """,
            [
                int(field_id),
                payload["supports_filter"],
                payload["supports_group_by"],
                payload["supports_metric"],
                payload["supports_dimension"],
                payload["is_date"],
                payload["is_identifier"],
                payload["is_chart_dimension"],
                payload["is_chart_measure"],
                payload["allowed_operators_json"],
                payload["allowed_aggregations_json"],
                payload["normalization_strategy"],
                payload["priority"],
                payload["active"],
            ],
        )
        return True

    def _upsert_relation(
        self,
        *,
        cursor,
        source_table_id: int,
        target_table_id: int,
        relation: dict[str, Any],
    ) -> bool:
        name = str(relation.get("name") or "").strip().lower()
        join_sql = str(relation.get("join_sql") or "").strip()
        cursor.execute(
            f"""
            SELECT id, nombre_relacion, join_sql, activa
            FROM {self.schema}.dd_relaciones
            WHERE LOWER(COALESCE(nombre_relacion, '')) = %s
               OR LOWER(COALESCE(join_sql, '')) = %s
            ORDER BY id
            LIMIT 1
            """,
            [name, join_sql.lower()],
        )
        row = cursor.fetchone()
        if row:
            changed = (
                str(row[1] or "").strip().lower() != name
                or str(row[2] or "").strip() != join_sql
                or int(row[3] or 0) != 1
            )
            if changed:
                cursor.execute(
                    f"""
                    UPDATE {self.schema}.dd_relaciones
                    SET tabla_origen_id = %s,
                        tabla_destino_id = %s,
                        nombre_relacion = %s,
                        join_sql = %s,
                        cardinalidad = %s,
                        descripcion = %s,
                        activa = 1
                    WHERE id = %s
                    """,
                    [
                        int(source_table_id),
                        int(target_table_id),
                        name,
                        join_sql,
                        str(relation.get("cardinality") or "").strip(),
                        str(relation.get("description") or "").strip(),
                        int(row[0]),
                    ],
                )
            return bool(changed)

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_relaciones (
                tabla_origen_id,
                tabla_destino_id,
                nombre_relacion,
                join_sql,
                cardinalidad,
                descripcion,
                activa,
                creado_en
            ) VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            [
                int(source_table_id),
                int(target_table_id),
                name,
                join_sql,
                str(relation.get("cardinality") or "").strip(),
                str(relation.get("description") or "").strip(),
            ],
        )
        return True

    def _upsert_rule(self, *, cursor, domain_id: int, rule: dict[str, Any]) -> bool:
        code = str(rule.get("codigo") or "").strip().lower()
        if not code:
            return False
        cursor.execute(
            f"""
            SELECT id, nombre, resultado_funcional, prioridad, activo
            FROM {self.schema}.dd_reglas
            WHERE dominio_id = %s
              AND LOWER(COALESCE(codigo, '')) = %s
            ORDER BY id
            LIMIT 1
            """,
            [int(domain_id), code],
        )
        row = cursor.fetchone()
        if row:
            changed = (
                str(row[1] or "").strip() != str(rule.get("nombre") or "").strip()
                or str(row[2] or "").strip() != str(rule.get("resultado_funcional") or "").strip()
                or int(row[3] or 0) != int(rule.get("prioridad") or 50)
                or int(row[4] or 0) != 1
            )
            if changed:
                cursor.execute(
                    f"""
                    UPDATE {self.schema}.dd_reglas
                    SET nombre = %s,
                        condicion_sql = %s,
                        resultado_funcional = %s,
                        tablas_relacionadas = %s,
                        agente_creador = %s,
                        estado = %s,
                        prioridad = %s,
                        activo = 1
                    WHERE id = %s
                    """,
                    [
                        str(rule.get("nombre") or "").strip(),
                        "1=1",
                        str(rule.get("resultado_funcional") or "").strip(),
                        "",
                        "phase7_dictionary_remediation",
                        "activa",
                        int(rule.get("prioridad") or 50),
                        int(row[0]),
                    ],
                )
            return bool(changed)

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_reglas (
                codigo,
                nombre,
                dominio_id,
                condicion_sql,
                resultado_funcional,
                tablas_relacionadas,
                agente_creador,
                estado,
                prioridad,
                activo,
                creado_en
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            [
                code,
                str(rule.get("nombre") or "").strip(),
                int(domain_id),
                "1=1",
                str(rule.get("resultado_funcional") or "").strip(),
                "",
                "phase7_dictionary_remediation",
                "activa",
                int(rule.get("prioridad") or 50),
            ],
        )
        return True

    def _upsert_synonym(self, *, cursor, domain_id: int, term: str, alias: str) -> bool:
        clean_term = str(term or "").strip().lower()
        clean_alias = str(alias or "").strip().lower()
        if not clean_term or not clean_alias:
            return False
        cursor.execute(
            f"""
            SELECT id, dominio_id, activo
            FROM {self.schema}.dd_sinonimos
            WHERE LOWER(COALESCE(termino, '')) = %s
              AND LOWER(COALESCE(sinonimo, '')) = %s
            LIMIT 1
            """,
            [clean_term, clean_alias],
        )
        row = cursor.fetchone()
        if row:
            changed = False
            if int(row[2] or 0) != 1:
                cursor.execute(
                    f"UPDATE {self.schema}.dd_sinonimos SET activo = 1 WHERE id = %s",
                    [int(row[0])],
                )
                changed = True
            if int(row[1] or 0) not in {0, int(domain_id)}:
                return changed
            cursor.execute(
                f"UPDATE {self.schema}.dd_sinonimos SET dominio_id = %s WHERE id = %s",
                [int(domain_id), int(row[0])],
            )
            return True

        cursor.execute(
            f"""
            INSERT INTO {self.schema}.dd_sinonimos (
                termino,
                sinonimo,
                dominio_id,
                activo,
                creado_en
            ) VALUES (%s, %s, %s, 1, NOW())
            """,
            [clean_term, clean_alias, int(domain_id)],
        )
        return True
