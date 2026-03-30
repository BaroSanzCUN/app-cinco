import os
import re

from django.db import connections


_SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_.]+$")


class DictionaryToolService:
    def __init__(self):
        self.db_alias = os.getenv("IA_DEV_DB_ALIAS", "default")
        self.dictionary_table = os.getenv(
            "IA_DEV_DICTIONARY_TABLE", "ai_dictionary.dd_dominios"
        )
        self.base_schema = (
            self.dictionary_table.split(".", 1)[0]
            if "." in self.dictionary_table
            else "ai_dictionary"
        )

    def _safe_table(self) -> str:
        if not _SAFE_TABLE_RE.match(self.dictionary_table):
            raise ValueError("Invalid IA_DEV_DICTIONARY_TABLE value")
        return self.dictionary_table

    def check_connection(self) -> dict:
        table = self._safe_table()

        with connections[self.db_alias].cursor() as cursor:
            cursor.execute("SELECT 1")
            ping = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]

        return {
            "ok": bool(ping == 1),
            "table": table,
            "rows": int(count or 0),
            "db_alias": self.db_alias,
        }

    def get_dictionary_snapshot(self) -> dict:
        table = self._safe_table()
        schema = self.base_schema
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_dominios")
            domains = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_tablas")
            tables = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_campos")
            fields = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_reglas")
            rules = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_relaciones")
            relations = int(cursor.fetchone()[0] or 0)
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.dd_sinonimos")
            synonyms = int(cursor.fetchone()[0] or 0)

        return {
            "dictionary_table": table,
            "schema": schema,
            "counts": {
                "dd_dominios": domains,
                "dd_tablas": tables,
                "dd_campos": fields,
                "dd_reglas": rules,
                "dd_relaciones": relations,
                "dd_sinonimos": synonyms,
            },
        }

    def get_domain_context(self, domain: str, *, limit: int = 8) -> dict:
        table = self._safe_table()
        schema = self.base_schema
        safe_limit = max(1, min(int(limit), 20))
        domain_key = (domain or "general").strip().lower()
        code_map = {
            "attendance": "AUSENTISMOS",
            "rrhh": "USUARIOS",
            "transport": "TRANSPORTE",
            "operations": "OPERACIONES",
            "viatics": "VIATICOS",
            "payroll": "NOMINA",
            "audit": "AUDITORIA",
            "general": "GENERAL",
        }
        domain_code = code_map.get(domain_key, "GENERAL")

        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, codigo, nombre, descripcion
                FROM {schema}.dd_dominios
                WHERE activo = 1
                  AND (
                    UPPER(codigo) = %s
                    OR UPPER(nombre) LIKE %s
                  )
                ORDER BY CASE WHEN UPPER(codigo) = %s THEN 0 ELSE 1 END, id
                LIMIT 1
                """,
                [domain_code.upper(), f"%{domain_code.upper()}%", domain_code.upper()],
            )
            domain_row = cursor.fetchone()

            if not domain_row:
                return {
                    "dictionary_table": table,
                    "schema": schema,
                    "domain": {
                        "code": domain_code,
                        "matched": False,
                    },
                    "tables": [],
                    "fields": [],
                    "rules": [],
                    "relations": [],
                    "synonyms": [],
                }

            dominio_id, codigo, nombre, descripcion = domain_row

            cursor.execute(
                f"""
                SELECT id, schema_name, table_name, alias_negocio, clave_negocio, descripcion
                FROM {schema}.dd_tablas
                WHERE activo = 1 AND dominio_id = %s
                ORDER BY table_name
                LIMIT %s
                """,
                [dominio_id, safe_limit],
            )
            table_rows = cursor.fetchall()
            table_ids = [int(row[0]) for row in table_rows if row[0] is not None]

            cursor.execute(
                f"""
                SELECT codigo, nombre, resultado_funcional, prioridad
                FROM {schema}.dd_reglas
                WHERE activo = 1 AND dominio_id = %s
                ORDER BY prioridad, codigo
                LIMIT %s
                """,
                [dominio_id, safe_limit],
            )
            rule_rows = cursor.fetchall()

            field_rows = []
            relation_rows = []
            if table_ids:
                in_clause = ", ".join(["%s"] * len(table_ids))
                cursor.execute(
                    f"""
                    SELECT
                        t.table_name,
                        c.campo_logico,
                        c.column_name,
                        c.tipo_campo,
                        c.tipo_dato_tecnico,
                        c.definicion_negocio,
                        c.es_clave
                    FROM {schema}.dd_campos AS c
                    JOIN {schema}.dd_tablas AS t ON t.id = c.tabla_id
                    WHERE c.activo = 1
                      AND c.tabla_id IN ({in_clause})
                    ORDER BY t.table_name, c.es_clave DESC, c.column_name
                    LIMIT %s
                    """,
                    [*table_ids, safe_limit * 10],
                )
                field_rows = cursor.fetchall()

                cursor.execute(
                    f"""
                    SELECT r.nombre_relacion, r.join_sql, r.cardinalidad, r.descripcion
                    FROM {schema}.dd_relaciones AS r
                    WHERE r.activa = 1
                      AND (
                        r.tabla_origen_id IN ({in_clause})
                        OR r.tabla_destino_id IN ({in_clause})
                      )
                    ORDER BY r.nombre_relacion
                    LIMIT %s
                    """,
                    [*table_ids, *table_ids, safe_limit],
                )
                relation_rows = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT termino, sinonimo
                FROM {schema}.dd_sinonimos
                WHERE activo = 1 AND dominio_id = %s
                ORDER BY termino, sinonimo
                LIMIT %s
                """,
                [dominio_id, safe_limit * 4],
            )
            synonym_rows = cursor.fetchall()

        tables = [
            {
                "id": int(row[0]),
                "schema_name": str(row[1] or ""),
                "table_name": str(row[2] or ""),
                "alias_negocio": str(row[3] or ""),
                "clave_negocio": str(row[4] or ""),
                "descripcion": str(row[5] or ""),
            }
            for row in table_rows
        ]
        fields = [
            {
                "table_name": str(row[0] or ""),
                "campo_logico": str(row[1] or ""),
                "column_name": str(row[2] or ""),
                "tipo_campo": str(row[3] or ""),
                "tipo_dato_tecnico": str(row[4] or ""),
                "definicion_negocio": str(row[5] or ""),
                "es_clave": bool(row[6]),
            }
            for row in field_rows
        ]
        rules = [
            {
                "codigo": str(row[0] or ""),
                "nombre": str(row[1] or ""),
                "resultado_funcional": str(row[2] or ""),
                "prioridad": int(row[3] or 0),
            }
            for row in rule_rows
        ]
        relations = [
            {
                "nombre_relacion": str(row[0] or ""),
                "join_sql": str(row[1] or ""),
                "cardinalidad": str(row[2] or ""),
                "descripcion": str(row[3] or ""),
            }
            for row in relation_rows
        ]
        synonyms = [
            {
                "termino": str(row[0] or ""),
                "sinonimo": str(row[1] or ""),
            }
            for row in synonym_rows
        ]

        return {
            "dictionary_table": table,
            "schema": schema,
            "domain": {
                "id": int(dominio_id),
                "code": str(codigo or ""),
                "name": str(nombre or ""),
                "description": str(descripcion or ""),
                "matched": True,
            },
            "tables": tables,
            "fields": fields,
            "rules": rules,
            "relations": relations,
            "synonyms": synonyms,
        }
