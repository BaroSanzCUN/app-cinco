import os
import re
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db import connections
else:
    from django.db import connections


_SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_.]+$")


class AttendanceToolService:
    def __init__(self):
        self.table = os.getenv("IA_DEV_ATTENDANCE_TABLE", "cincosas_cincosas.gestionh_ausentismo")
        self.db_alias = os.getenv("IA_DEV_DB_ALIAS", "default")
        self.personal_table = os.getenv(
            "IA_DEV_PERSONAL_TABLE",
            "cincosas_cincosas.cinco_base_de_personal",
        )

    def _safe_table(self) -> str:
        if not _SAFE_TABLE_RE.match(self.table):
            raise ValueError("Invalid IA_DEV_ATTENDANCE_TABLE value")
        return self.table

    def _safe_personal_table(self) -> str:
        if not _SAFE_TABLE_RE.match(self.personal_table):
            raise ValueError("Invalid IA_DEV_PERSONAL_TABLE value")
        return self.personal_table

    def get_summary(self, start_date: date, end_date: date) -> dict:
        table = self._safe_table()
        sql = f"""
            SELECT
                %s AS periodo_inicio,
                %s AS periodo_fin,
                COALESCE(SUM(CASE WHEN UPPER(TRIM(g.ausentismo)) = 'SI' THEN 1 ELSE 0 END), 0) AS total_ausentismos,
                COALESCE(SUM(
                    CASE
                        WHEN UPPER(TRIM(g.ausentismo)) = 'SI'
                         AND g.justificacion IS NOT NULL
                         AND TRIM(g.justificacion) <> ''
                         AND UPPER(TRIM(g.justificacion)) <> 'SIN JUSTIFICAR'
                        THEN 1 ELSE 0
                    END
                ), 0) AS justificados,
                COALESCE(SUM(
                    CASE
                        WHEN UPPER(TRIM(g.ausentismo)) = 'SI'
                         AND (
                            g.justificacion IS NULL
                            OR TRIM(g.justificacion) = ''
                            OR UPPER(TRIM(g.justificacion)) = 'SIN JUSTIFICAR'
                         )
                        THEN 1 ELSE 0
                    END
                ), 0) AS injustificados
            FROM {table} AS g
            WHERE DATE(g.fecha_edit) BETWEEN %s AND %s
        """

        params = [start_date, end_date, start_date, end_date]

        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        if not row:
            return {
                "periodo_inicio": start_date.isoformat(),
                "periodo_fin": end_date.isoformat(),
                "total_ausentismos": 0,
                "justificados": 0,
                "injustificados": 0,
            }

        return {
            "periodo_inicio": str(row[0]),
            "periodo_fin": str(row[1]),
            "total_ausentismos": int(row[2] or 0),
            "justificados": int(row[3] or 0),
            "injustificados": int(row[4] or 0),
        }

    def get_unjustified_table(self, start_date: date, end_date: date, limit: int = 100) -> dict:
        table = self._safe_table()
        safe_limit = max(1, min(int(limit), 500))
        sql = f"""
            SELECT
                g.cedula,
                DATE(g.fecha_edit) AS fecha_ausentismo,
                COALESCE(g.justificacion, '') AS justificacion
            FROM {table} AS g
            WHERE DATE(g.fecha_edit) BETWEEN %s AND %s
              AND UPPER(TRIM(g.ausentismo)) = 'SI'
              AND (
                    g.justificacion IS NULL
                    OR TRIM(g.justificacion) = ''
                    OR UPPER(TRIM(g.justificacion)) = 'SIN JUSTIFICAR'
              )
            ORDER BY DATE(g.fecha_edit) DESC, g.cedula
            LIMIT %s
        """
        params = [start_date, end_date, safe_limit]

        rows: list[dict] = []
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            for cedula, fecha_ausentismo, justificacion in cursor.fetchall():
                rows.append(
                    {
                        "cedula": str(cedula),
                        "fecha_ausentismo": str(fecha_ausentismo),
                        "justificacion": str(justificacion or ""),
                    }
                )

        return {
            "periodo_inicio": start_date.isoformat(),
            "periodo_fin": end_date.isoformat(),
            "rows": rows,
            "rowcount": len(rows),
            "truncated": len(rows) == safe_limit,
        }

    def get_unjustified_with_personal(self, start_date: date, end_date: date, limit: int = 100) -> dict:
        table = self._safe_table()
        personal_table = self._safe_personal_table()
        safe_limit = max(1, min(int(limit), 500))
        sql = f"""
            SELECT
                g.cedula,
                DATE(g.fecha_edit) AS fecha_ausentismo,
                COALESCE(
                    NULLIF(CONCAT(TRIM(COALESCE(emp.nombre, '')), ' ', TRIM(COALESCE(emp.apellido, ''))), ''),
                    CONCAT('Cedula ', g.cedula)
                ) AS empleado,
                COALESCE(emp.area, '') AS area,
                COALESCE(emp.cargo, '') AS cargo,
                COALESCE(
                    NULLIF(
                        CONCAT(TRIM(COALESCE(sup.nombre, '')), ' ', TRIM(COALESCE(sup.apellido, ''))),
                        ''
                    ),
                    TRIM(COALESCE(emp.supervisor, ''))
                ) AS supervisor,
                COALESCE(g.justificacion, '') AS justificacion
            FROM {table} AS g
            LEFT JOIN {personal_table} AS emp ON TRIM(COALESCE(emp.cedula, '')) = TRIM(COALESCE(g.cedula, ''))
            LEFT JOIN {personal_table} AS sup ON TRIM(COALESCE(sup.cedula, '')) = TRIM(COALESCE(emp.supervisor, ''))
            WHERE DATE(g.fecha_edit) BETWEEN %s AND %s
              AND UPPER(TRIM(g.ausentismo)) = 'SI'
              AND (
                    g.justificacion IS NULL
                    OR TRIM(g.justificacion) = ''
                    OR UPPER(TRIM(g.justificacion)) = 'SIN JUSTIFICAR'
              )
            ORDER BY DATE(g.fecha_edit) DESC, g.cedula
            LIMIT %s
        """
        params = [start_date, end_date, safe_limit]

        rows: list[dict] = []
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            for (
                cedula,
                fecha_ausentismo,
                empleado,
                area,
                cargo,
                supervisor,
                justificacion,
            ) in cursor.fetchall():
                rows.append(
                    {
                        "cedula": str(cedula),
                        "fecha_ausentismo": str(fecha_ausentismo),
                        "empleado": str(empleado or "").strip(),
                        "area": str(area or ""),
                        "cargo": str(cargo or ""),
                        "supervisor": str(supervisor or "").strip() or "N/D",
                        "justificacion": str(justificacion or ""),
                    }
                )

        return {
            "periodo_inicio": start_date.isoformat(),
            "periodo_fin": end_date.isoformat(),
            "rows": rows,
            "rowcount": len(rows),
            "truncated": len(rows) == safe_limit,
        }

    def get_detail_with_personal(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int = 150,
    ) -> dict:
        table = self._safe_table()
        personal_table = self._safe_personal_table()
        safe_limit = max(1, min(int(limit), 500))
        sql = f"""
            SELECT
                g.cedula,
                COALESCE(emp.nombre, '') AS nombre,
                COALESCE(emp.apellido, '') AS apellido,
                TRIM(
                    CONCAT(
                        COALESCE(emp.nombre, ''),
                        ' ',
                        COALESCE(emp.apellido, '')
                    )
                ) AS nombre_completo,
                DATE(g.fecha_edit) AS fecha_ausentismo,
                UPPER(TRIM(COALESCE(g.ausentismo, ''))) AS ausentismo,
                COALESCE(g.justificacion, '') AS justificacion,
                COALESCE(emp.supervisor, '') AS supervisor_cedula,
                COALESCE(emp.area, '') AS area,
                COALESCE(emp.cargo, '') AS cargo,
                COALESCE(emp.carpeta, '') AS carpeta,
                COALESCE(
                    NULLIF(
                        CONCAT(TRIM(COALESCE(sup.nombre, '')), ' ', TRIM(COALESCE(sup.apellido, ''))),
                        ''
                    ),
                    TRIM(COALESCE(emp.supervisor, ''))
                ) AS supervisor,
                CASE
                    WHEN g.justificacion IS NULL
                      OR TRIM(g.justificacion) = ''
                      OR UPPER(TRIM(g.justificacion)) = 'SIN JUSTIFICAR'
                    THEN 'INJUSTIFICADO'
                    ELSE 'JUSTIFICADO'
                END AS estado_justificacion
            FROM {table} AS g
            LEFT JOIN {personal_table} AS emp ON TRIM(COALESCE(emp.cedula, '')) = TRIM(COALESCE(g.cedula, ''))
            LEFT JOIN {personal_table} AS sup ON TRIM(COALESCE(sup.cedula, '')) = TRIM(COALESCE(emp.supervisor, ''))
            WHERE DATE(g.fecha_edit) BETWEEN %s AND %s
              AND UPPER(TRIM(COALESCE(g.ausentismo, ''))) = 'SI'
            ORDER BY DATE(g.fecha_edit) DESC, emp.apellido, emp.nombre, g.cedula
            LIMIT %s
        """
        params = [start_date, end_date, safe_limit]

        rows: list[dict] = []
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            for (
                cedula,
                nombre,
                apellido,
                nombre_completo,
                fecha_ausentismo,
                ausentismo,
                justificacion,
                supervisor_cedula,
                area,
                cargo,
                carpeta,
                supervisor,
                estado_justificacion,
            ) in cursor.fetchall():
                rows.append(
                    {
                        "cedula": str(cedula),
                        "nombre": str(nombre or ""),
                        "apellido": str(apellido or ""),
                        "nombre_completo": str(nombre_completo or "").strip(),
                        "fecha_ausentismo": str(fecha_ausentismo),
                        "ausentismo": str(ausentismo or ""),
                        "justificacion": str(justificacion or ""),
                        "estado_justificacion": str(estado_justificacion or ""),
                        "supervisor_cedula": str(supervisor_cedula or ""),
                        "supervisor": str(supervisor or "").strip() or "N/D",
                        "area": str(area or ""),
                        "cargo": str(cargo or ""),
                        "carpeta": str(carpeta or ""),
                    }
                )

        return {
            "periodo_inicio": start_date.isoformat(),
            "periodo_fin": end_date.isoformat(),
            "rows": rows,
            "rowcount": len(rows),
            "truncated": len(rows) == safe_limit,
        }

    def get_recurrent_unjustified_with_supervisor(
        self,
        start_date: date,
        end_date: date,
        *,
        threshold: int = 2,
        limit: int = 150,
    ) -> dict:
        table = self._safe_table()
        personal_table = self._safe_personal_table()
        safe_limit = max(1, min(int(limit), 500))
        safe_threshold = max(1, int(threshold))

        sql = f"""
            SELECT
                g.cedula,
                COALESCE(
                    NULLIF(CONCAT(TRIM(COALESCE(emp.nombre, '')), ' ', TRIM(COALESCE(emp.apellido, ''))), ''),
                    CONCAT('Cedula ', g.cedula)
                ) AS empleado,
                COALESCE(
                    NULLIF(CONCAT(TRIM(COALESCE(sup.nombre, '')), ' ', TRIM(COALESCE(sup.apellido, ''))), ''),
                    TRIM(COALESCE(emp.supervisor, ''))
                ) AS supervisor,
                COUNT(*) AS cantidad_incidencias,
                GROUP_CONCAT(
                    DISTINCT DATE(g.fecha_edit)
                    ORDER BY DATE(g.fecha_edit) DESC
                    SEPARATOR ', '
                ) AS fechas
            FROM {table} AS g
            LEFT JOIN {personal_table} AS emp ON TRIM(COALESCE(emp.cedula, '')) = TRIM(COALESCE(g.cedula, ''))
            LEFT JOIN {personal_table} AS sup ON TRIM(COALESCE(sup.cedula, '')) = TRIM(COALESCE(emp.supervisor, ''))
            WHERE DATE(g.fecha_edit) BETWEEN %s AND %s
              AND UPPER(TRIM(g.ausentismo)) = 'SI'
              AND (
                    g.justificacion IS NULL
                    OR TRIM(g.justificacion) = ''
                    OR UPPER(TRIM(g.justificacion)) = 'SIN JUSTIFICAR'
              )
            GROUP BY g.cedula, empleado, supervisor
            HAVING COUNT(*) >= %s
            ORDER BY cantidad_incidencias DESC, g.cedula
            LIMIT %s
        """

        params = [start_date, end_date, safe_threshold, safe_limit]
        rows: list[dict] = []
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            for cedula, empleado, supervisor, cantidad_incidencias, fechas in cursor.fetchall():
                rows.append(
                    {
                        "cedula": str(cedula),
                        "empleado": str(empleado or "").strip(),
                        "supervisor": str(supervisor or "").strip() or "N/D",
                        "cantidad_incidencias": int(cantidad_incidencias or 0),
                        "fechas": str(fechas or ""),
                    }
                )

        return {
            "periodo_inicio": start_date.isoformat(),
            "periodo_fin": end_date.isoformat(),
            "threshold": safe_threshold,
            "rows": rows,
            "rowcount": len(rows),
            "truncated": len(rows) == safe_limit,
        }
