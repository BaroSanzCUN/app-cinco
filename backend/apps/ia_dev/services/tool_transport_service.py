import os
import re
from datetime import date

from django.db import connections


_SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_.]+$")


class TransportToolService:
    def __init__(self):
        self.db_alias = os.getenv("IA_DEV_DB_ALIAS", "default")
        self.table = os.getenv("IA_DEV_TRANSPORT_TABLE", "").strip()
        self.date_column = os.getenv("IA_DEV_TRANSPORT_DATE_COLUMN", "fecha_salida").strip()

    def source_status(self) -> dict:
        configured = bool(self.table)
        return {
            "configured": configured,
            "ok": configured,
            "table": self.table or None,
            "date_column": self.date_column or None,
        }

    def _safe_table(self) -> str:
        if not self.table:
            raise ValueError("Transport data source is not configured")
        if not _SAFE_TABLE_RE.match(self.table):
            raise ValueError("Invalid IA_DEV_TRANSPORT_TABLE value")
        return self.table

    def _safe_column(self) -> str:
        if not self.date_column or not re.match(r"^[A-Za-z0-9_]+$", self.date_column):
            raise ValueError("Invalid IA_DEV_TRANSPORT_DATE_COLUMN value")
        return self.date_column

    def get_departures_summary(self, day: date) -> dict:
        table = self._safe_table()
        date_column = self._safe_column()

        sql = f"""
            SELECT %s AS fecha, COALESCE(COUNT(*), 0) AS total_salidas
            FROM {table}
            WHERE DATE({date_column}) = %s
        """

        params = [day, day]

        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        return {
            "fecha": str(row[0]) if row else day.isoformat(),
            "total_salidas": int((row[1] if row else 0) or 0),
        }
