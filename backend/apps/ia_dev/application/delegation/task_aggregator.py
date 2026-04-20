from __future__ import annotations

from typing import Any

from apps.ia_dev.application.delegation.task_contracts import AggregatedResponse, DelegationResult, DelegationTask


class TaskAggregator:
    def aggregate_results(
        self,
        *,
        tasks: list[DelegationTask],
        results: list[DelegationResult],
    ) -> AggregatedResponse:
        ordered_results = self._order_results(tasks=tasks, results=results)
        kpis: dict[str, Any] = {}
        insights: list[str] = []
        actions: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []
        table_payload = {"columns": [], "rows": [], "rowcount": 0}
        labels: list[Any] = []
        series: list[Any] = []
        chart_payload: dict[str, Any] = {}
        charts_payload: list[dict[str, Any]] = []
        reply_parts: list[str] = []

        for item in ordered_results:
            if item.status not in {"ok", "partial"}:
                continue
            for key, value in dict(item.kpis or {}).items():
                if key not in kpis:
                    kpis[key] = value
                elif isinstance(value, (int, float)) and isinstance(kpis.get(key), (int, float)):
                    kpis[key] = (kpis.get(key) or 0) + value
                else:
                    kpis[key] = value

            candidate_table = dict(item.table or {})
            candidate_rows = list(candidate_table.get("rows") or [])
            if len(candidate_rows) > int(table_payload.get("rowcount") or 0):
                table_payload = {
                    "columns": list(candidate_table.get("columns") or []),
                    "rows": candidate_rows,
                    "rowcount": int(candidate_table.get("rowcount") or len(candidate_rows)),
                }

            if item.labels and not labels:
                labels = list(item.labels)
            if item.series and not series:
                series = list(item.series)
            if item.chart and not chart_payload:
                chart_payload = dict(item.chart)
            if item.chart:
                charts_payload.append(dict(item.chart))

            for insight in list(item.insights or []):
                text = str(insight or "").strip()
                if text and text not in insights:
                    insights.append(text)

            actions.extend(list(item.actions or []))
            trace.extend(list(item.trace_events or []))
            sections.append(
                {
                    "task_id": item.task_id,
                    "domain_code": item.domain_code,
                    "status": item.status,
                    "kpis": dict(item.kpis or {}),
                    "table_rowcount": int((item.table or {}).get("rowcount") or 0),
                    "has_chart": bool(item.chart),
                    "insights_count": len(list(item.insights or [])),
                }
            )
            if item.reply_text:
                reply_parts.append(str(item.reply_text))

        reply = self._build_reply(
            kpis=kpis,
            table=table_payload,
            fallback_parts=reply_parts,
        )
        return AggregatedResponse(
            reply=reply,
            sections=sections,
            kpis=kpis,
            table=table_payload,
            series=series,
            labels=labels,
            chart=chart_payload,
            charts=charts_payload,
            insights=insights,
            trace=trace,
            actions=actions,
        )

    @staticmethod
    def _order_results(
        *,
        tasks: list[DelegationTask],
        results: list[DelegationResult],
    ) -> list[DelegationResult]:
        by_task_id = {item.task_id: item for item in results}
        ordered: list[DelegationResult] = []
        ordered_ids: set[str] = set()
        for task in sorted(tasks, key=lambda item: int(item.priority), reverse=True):
            result = by_task_id.get(task.task_id)
            if result is None:
                continue
            ordered.append(result)
            ordered_ids.add(task.task_id)
        for item in results:
            if item.task_id not in ordered_ids:
                ordered.append(item)
        return ordered

    @staticmethod
    def _build_reply(
        *,
        kpis: dict[str, Any],
        table: dict[str, Any],
        fallback_parts: list[str],
    ) -> str:
        total = kpis.get("total_injustificados")
        groups = kpis.get("total_grupos")
        rowcount = int(table.get("rowcount") or 0)
        if total is not None and groups is not None:
            return (
                f"Comparativo de ausentismo generado: total_injustificados={total}, "
                f"total_grupos={groups}, filas={rowcount}."
            )
        if fallback_parts:
            return " ".join(part for part in fallback_parts if part).strip()
        return "No se encontraron resultados para consolidar."
