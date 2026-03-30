import re
import unicodedata
from datetime import date, timedelta


DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}).{0,10}(\d{4}-\d{2}-\d{2})")
WEEKDAY_MAP = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}
WEEKDAY_PATTERNS = {
    "lunes": r"\blunes\b",
    "martes": r"\bmartes\b",
    "miercoles": r"\bmi.?rcoles\b",
    "jueves": r"\bjueves\b",
    "viernes": r"\bviernes\b",
    "sabado": r"\bs.?bado\b",
    "domingo": r"\bdomingo\b",
}


def _shift_months(base: date, months: int) -> date:
    month_index = (base.year * 12 + (base.month - 1)) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _last_saturday(today: date) -> date:
    # Python weekday: Monday=0 ... Sunday=6, Saturday=5
    delta = (today.weekday() - 5) % 7
    if delta == 0:
        delta = 7
    return today - timedelta(days=delta)


def _most_recent_saturday(today: date) -> date:
    # Includes today when it is Saturday.
    delta = (today.weekday() - 5) % 7
    return today - timedelta(days=delta)


def _most_recent_weekday(today: date, target_weekday: int, *, include_today: bool) -> date:
    # Python weekday: Monday=0 ... Sunday=6
    delta = (today.weekday() - target_weekday) % 7
    if delta == 0 and not include_today:
        delta = 7
    return today - timedelta(days=delta)


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def resolve_period_from_text(text: str, today: date | None = None) -> dict:
    now = today or date.today()
    msg = (text or "").strip().lower()
    norm = _normalize_text(text)

    match_range = DATE_RANGE_RE.search(msg)
    if match_range:
        start = date.fromisoformat(match_range.group(1))
        end = date.fromisoformat(match_range.group(2))
        if start > end:
            start, end = end, start
        return {"label": "rango", "start": start, "end": end}

    if "ayer" in norm:
        d = now - timedelta(days=1)
        return {"label": "ayer", "start": d, "end": d}

    for weekday_name, weekday_idx in WEEKDAY_MAP.items():
        weekday_pattern = WEEKDAY_PATTERNS.get(weekday_name, rf"\b{weekday_name}\b")
        if re.search(weekday_pattern, norm):
            is_past_reference = bool(
                re.search(weekday_pattern.replace(r"\b", "") + r"\s+pasad[oa]\b", norm)
            )
            d = _most_recent_weekday(
                now,
                weekday_idx,
                include_today=not is_past_reference,
            )
            suffix = "pasado" if is_past_reference else "reciente"
            return {"label": f"{weekday_name}_{suffix}", "start": d, "end": d}

    if "ultima semana" in norm:
        return {"label": "ultima_semana", "start": now - timedelta(days=6), "end": now}

    m_days = re.search(r"ultimos?\s+(\d+)\s+dias", norm)
    if m_days:
        n = max(1, int(m_days.group(1)))
        return {"label": f"ultimos_{n}_dias", "start": now - timedelta(days=n - 1), "end": now}

    if "mes pasado" in norm:
        first_current = now.replace(day=1)
        end = first_current - timedelta(days=1)
        start = end.replace(day=1)
        return {"label": "mes_pasado", "start": start, "end": end}

    if "este mes" in norm or "mes actual" in norm:
        return {"label": "mes_actual", "start": now.replace(day=1), "end": now}

    m_months = re.search(r"ultimos?\s+(\d+)\s+meses", norm)
    if m_months:
        n = max(1, int(m_months.group(1)))
        start = _shift_months(now.replace(day=1), -(n - 1))
        return {"label": f"ultimos_{n}_meses", "start": start, "end": now}

    if "ano pasado" in norm:
        return {
            "label": "anio_pasado",
            "start": date(now.year - 1, 1, 1),
            "end": date(now.year - 1, 12, 31),
        }

    if "este ano" in norm or "ano actual" in norm:
        return {"label": "anio_actual", "start": date(now.year, 1, 1), "end": now}

    if "hoy" in norm:
        return {"label": "hoy", "start": now, "end": now}

    return {"label": "hoy", "start": now, "end": now}
