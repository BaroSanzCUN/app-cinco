from __future__ import annotations

from datetime import date

from django.test import SimpleTestCase

from apps.ia_dev.services.period_service import resolve_period_from_text


class PeriodServiceSemanticsTests(SimpleTestCase):
    def test_resolves_current_week_from_monday_to_today(self):
        period = resolve_period_from_text(
            "Cantidad ausentismos de esta semana",
            today=date(2026, 4, 11),
        )
        self.assertEqual(period.get("label"), "semana_actual")
        self.assertEqual(period.get("start"), date(2026, 4, 6))
        self.assertEqual(period.get("end"), date(2026, 4, 11))

    def test_resolves_previous_calendar_week(self):
        period = resolve_period_from_text(
            "Cantidad ausentismos de la semana pasada",
            today=date(2026, 4, 11),
        )
        self.assertEqual(period.get("label"), "semana_anterior")
        self.assertEqual(period.get("start"), date(2026, 3, 30))
        self.assertEqual(period.get("end"), date(2026, 4, 5))

    def test_resolves_last_year_as_rolling_12_months(self):
        period = resolve_period_from_text(
            "Ausentismos del ultimo ano del empleado 1055837370",
            today=date(2026, 4, 13),
        )
        self.assertEqual(period.get("label"), "ultimo_ano_12_meses")
        self.assertEqual(period.get("start"), date(2025, 4, 14))
        self.assertEqual(period.get("end"), date(2026, 4, 13))
