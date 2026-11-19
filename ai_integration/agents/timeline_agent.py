"""
Timeline subagent — answers date-based questions for ANY time-series chart in Superset.

Nothing here is tied to a particular chart. On every question the agent:
  1. lists all dashboard charts that plot a metric over a temporal x-axis
     (read live from Superset's metadata DB via ``dynamic_catalog``);
  2. picks the chart whose name / metric / dataset best matches the question,
     preferring the dashboard the user is currently looking at;
  3. rebuilds that chart's SQL from its own settings (dataset or virtual SQL, adhoc filters,
     metric, time column, time grain, rolling window) and runs it on the chart's database;
  4. narrows the result by any dataset values named in the question
     (e.g. "aided", "english medium"), discovered from the data itself.

So a new timeline chart on a new dashboard is answerable as soon as it is saved in Superset.

Question shapes handled:
    single day ........ "how many schools got onboarded on saturday april 5"
    range ............. "in may 2025", "between 1 june and 30 june", "last month", "since march"
    as-of ............. "how many by oct 27"   (the value the chart plots on that date)
    first / latest .... "when was the first ...", "most recent ..."
    extremes .......... "which day/month had the most / least ..."
    trend ............. "monthly trend", "timeline", "over time"
"""

import re
import statistics
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAgent, QueryContext
from .date_parser import TemporalSpec, fmt_day, fmt_short, parse_temporal
from .text_match import STOP_WORDS, content_stems, stem, stems_of, words

try:
    from ai_integration.dynamic_catalog import dynamic_catalog as catalog  # type: ignore
    from ai_integration.chart_engine import is_specific_or_adhoc_query  # type: ignore
except ImportError:
    from dynamic_catalog import dynamic_catalog as catalog  # type: ignore
    from chart_engine import is_specific_or_adhoc_query  # type: ignore

_TREND = re.compile(
    r"\b(when|timeline|trend|over\s+time|history|historical|growth|daily|weekly|monthly|yearly|annually|"
    r"(?:day|week|month|year)[\s-]?wise|(?:per|each|by|every)\s+(?:day|week|month|year)|"
    r"first|earliest|latest|most\s+recent|recent(?:ly)?|start(?:ed)?|began|begin)\b")
_EXTREME = re.compile(r"\b(peak|busiest|most|highest|maximum|max|lowest|least|minimum|fewest|slowest)\b")
_UNIT_WORD = re.compile(r"\b(day|date|week|month|year|quarter|period)s?\b")
_LOW = re.compile(r"\b(lowest|least|minimum|fewest|slowest)\b")
_VALUE_SKIP = {"true", "false", "yes", "no", "null", "none", "na", "nil", "unknown", "other", "others", "test"}


def _num(v: Any) -> float:
    if v is None:
        return 0
    f = float(v)
    return int(f) if f.is_integer() else round(f, 2)


def _fmt(v: Any) -> str:
    n = _num(v)
    return f"{n:,}" if isinstance(n, int) else f"{n:,.2f}"


def _lit(d: date) -> str:
    """Date literal built only from a datetime.date, never from user text."""
    return f"'{d.isoformat()}'"


class _Chart:
    """A matched time-series chart plus everything needed to query it."""

    def __init__(self, slice_info: Dict[str, Any], dim_conds: List[str], dim_label: str):
        self.s = slice_info
        self.ds = slice_info.get("dataset") or {}
        self.name = slice_info.get("slice_name") or "chart"
        self.dashboard = slice_info.get("dashboard_title") or ""
        self.tcol = catalog.temporal_column(slice_info)
        self.metric, self.metric_label, self.additive = catalog.metric_sql(slice_info)
        if "(" in self.metric_label or self.metric_label.lower() == "count":
            self.metric_label = self.name  # raw SQL label: the chart name reads better
        self.src = catalog.from_clause(self.ds)
        self.base = catalog.where_conditions(slice_info) + dim_conds
        self.dim_label = dim_label
        p = slice_info.get("params") or {}
        self.grain = catalog.GRAIN_UNITS.get(p.get("time_grain_sqla") or "P1D", "day")
        self.rolling = (p.get("rolling_type") or "").lower() if p.get("rolling_type") not in (None, "None", "") else ""
        self.periods = int(p.get("rolling_periods") or 0)
        self.min_periods = int(p.get("min_periods") or 0)

    def where(self, *extra: str) -> str:
        conds = self.base + [e for e in extra if e]
        return " WHERE " + " AND ".join(conds) if conds else ""

    def q(self, sql: str) -> List[tuple]:
        return catalog.run_sql(self.ds, " ".join(sql.split())) or []

    def value(self, start: Optional[date], end: Optional[date]) -> float:
        rows = self.q(f"SELECT {self.metric} FROM {self.src}"
                      f"{self.where(f'{self.tcol} >= {_lit(start)}' if start else '', f'{self.tcol} < {_lit(end)}' if end else '')}")
        return _num(rows[0][0]) if rows else 0

    def plotted(self, end: date) -> Optional[Tuple[float, str]]:
        """What the chart itself plots at the last point before ``end`` (applies its rolling window)."""
        if self.rolling in ("cumsum", "sum", "mean", "std"):
            rows = self.q(f"SELECT DATE_TRUNC('{self.grain}', {self.tcol}), {self.metric} FROM {self.src}"
                          f"{self.where(f'{self.tcol} < {_lit(end)}')} GROUP BY 1 ORDER BY 1")
            series = [_num(r[1]) for r in rows]
            if not series:
                return 0, "running total"
            if self.rolling == "cumsum" or (self.rolling == "sum" and len(series) <= self.periods):
                return _num(sum(series)), "running total"
            window = series[-self.periods:] if self.periods else series
            if self.min_periods and len(window) < self.min_periods:
                return None
            unit = f"{self.periods}-{self.grain}"
            if self.rolling == "sum":
                return _num(sum(window)), f"rolling {unit} total"
            if self.rolling == "mean":
                return _num(statistics.mean(window)), f"rolling {unit} average"
            return (_num(statistics.stdev(window)) if len(window) > 1 else 0), f"rolling {unit} standard deviation"
        if self.additive:
            return self.value(None, end), "running total"
        return None


class TimelineAgent(BaseAgent):
    name = "timeline"
    description = "Date-based questions on any time-series chart (discovered live from Superset)"

    # ── Routing ──────────────────────────────────────────────────────────────
    def _plan(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        if "timeline" in ctx.scratch:
            return ctx.scratch["timeline"]
        plan = None
        spec = parse_temporal(ctx.lower, ctx.today)
        extreme = bool(_EXTREME.search(ctx.lower) and _UNIT_WORD.search(ctx.lower))
        if spec or _TREND.search(ctx.lower) or extreme:
            match = self._match_chart(ctx)
            if match:
                plan = {"slice": match[0], "score": match[1], "spec": spec, "extreme": extreme}
        ctx.scratch["timeline"] = plan
        return plan

    @staticmethod
    def _active_dashboard_id(ctx: QueryContext) -> Optional[int]:
        dc = ctx.dashboard_context or {}
        if dc.get("dashboard_id"):
            try:
                return int(dc["dashboard_id"])
            except (TypeError, ValueError):
                pass
        if dc.get("url"):
            d = catalog.resolve_active_dashboard(dc["url"])
            return d.get("id") if d else None
        return None

    def _match_chart(self, ctx: QueryContext) -> Optional[Tuple[Dict[str, Any], float]]:
        q = content_stems(ctx.lower)
        if not q:
            return None
        active = self._active_dashboard_id(ctx)
        best: Optional[Tuple[Dict[str, Any], float]] = None
        for s in catalog.time_series_slices():
            ds = s.get("dataset") or {}
            name = stems_of([s.get("slice_name")])
            other = stems_of([catalog.metric_sql(s)[1], ds.get("table_name"), catalog.temporal_column(s)]) - name
            dash = stems_of([s.get("dashboard_title")]) - name - other
            strong = len(q & name) + 0.6 * len(q & other)
            if strong <= 0:
                continue
            score = strong + 0.3 * len(q & dash) + (0.5 if active and s.get("dashboard_id") == active else 0)
            if best is None or score > best[1]:
                best = (s, score)
        return best

    def score(self, ctx: QueryContext) -> float:
        plan = self._plan(ctx)
        return 0.9 if plan else 0.0

    # ── Dimension filters discovered from the data ───────────────────────────
    @staticmethod
    def _dimension_filters(ctx: QueryContext, s: Dict[str, Any], spec: Optional[TemporalSpec]) -> Tuple[List[str], List[str]]:
        ds = s.get("dataset") or {}
        text = ctx.lower
        for a, b in (spec.spans if spec else []):
            text = text[:a] + " " * (b - a) + text[b:]
        q_seq = [stem(w) for w, _, _ in words(text)]
        chart_stems = stems_of([s.get("slice_name"), catalog.metric_sql(s)[1], ds.get("table_name")])

        candidates = []  # (length, start, column, value)
        for col, vals in catalog.categorical_values(ds).items():
            for val in vals:
                v = (val or "").strip()
                if len(v) < 3 or v.lower() in _VALUE_SKIP or re.fullmatch(r"[\d\s.\-/:]+", v):
                    continue
                core = [stem(w) for w, _, _ in words(v) if w not in STOP_WORDS]
                core = [c for c in core if c not in chart_stems]
                if not core:
                    continue
                n = len(core)
                for i in range(len(q_seq) - n + 1):
                    if q_seq[i:i + n] == core:
                        candidates.append((n, i, col, v))

        used: set = set()
        by_phrase: Dict[Tuple[int, int], List[Tuple[str, str]]] = {}
        for n, i, col, v in sorted(candidates, key=lambda c: -c[0]):
            pos = set(range(i, i + n))
            key = (i, n)
            if pos & used and key not in by_phrase:
                continue
            used |= pos
            by_phrase.setdefault(key, []).append((col, v))

        col_values: Dict[str, List[str]] = {}
        conds, labels = [], []
        for hits in by_phrase.values():
            cols = {c for c, _ in hits}
            if len(cols) == 1:
                col_values.setdefault(hits[0][0], []).extend(v for _, v in hits)
            else:
                conds.append("(" + " OR ".join(f"{catalog.column_expr(ds, c)} = {catalog.sql_literal(v)}" for c, v in hits) + ")")
            labels.extend(dict.fromkeys(f"{TimelineAgent._column_label(ds, c)}: {v}" for c, v in hits))
        for col, vals in col_values.items():
            vals = list(dict.fromkeys(vals))
            conds.append(f"{catalog.column_expr(ds, col)} IN ({', '.join(catalog.sql_literal(v) for v in vals)})")
        return conds, list(dict.fromkeys(labels))

    @staticmethod
    def _column_label(ds: Dict[str, Any], col: str) -> str:
        info = (ds.get("columns") or {}).get(col) or {}
        return info.get("verbose_name") or col.replace("_", " ").title()

    # ── Answering ────────────────────────────────────────────────────────────
    def handle(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        plan = self._plan(ctx)
        if not plan:
            return None
        s, spec = plan["slice"], plan["spec"]
        dim_conds, dim_labels = self._dimension_filters(ctx, s, spec)
        if is_specific_or_adhoc_query(ctx.lower) and not dim_conds:
            return None  # names a specific entity we cannot filter on: let the SQL agent (n8n) answer
        c = _Chart(s, dim_conds, ", ".join(dim_labels))
        if not c.tcol:
            return None

        q = ctx.lower
        if spec is not None:
            if spec.mode == "day":
                return self._single_day(c, spec)
            if spec.mode == "until":
                return self._as_of(c, spec)
            return self._date_range(c, spec)
        if re.search(r"\b(first|earliest|start(?:ed)?|began|begin)\b", q):
            return self._edge(c, first=True)
        if re.search(r"\b(latest|most\s+recent|recent(?:ly)?|last)\b", q) and not plan["extreme"]:
            return self._edge(c, first=False)
        if plan["extreme"]:
            unit_m = _UNIT_WORD.search(q)
            unit = {"date": "day", "period": c.grain}.get(unit_m.group(1), unit_m.group(1)) if unit_m else "day"
            return self._extreme(c, unit, lowest=bool(_LOW.search(q)))
        return self._trend(c)

    # ── Result helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _for(c: _Chart) -> str:
        return f" for {c.dim_label}" if c.dim_label else ""

    def _result(self, c: _Chart, value: Any, tag: str, text: str, sql: str,
                matched: Dict[str, Any], intent: str, notes: List[str]) -> Dict[str, Any]:
        source = f" (from the **{c.name}** chart" + (f" on {c.dashboard}" if c.dashboard else "") + ")."
        text = text.rstrip(".") + source
        if notes:
            text += " " + " ".join(notes)
        return {
            "title": c.name,
            "value": _fmt(value),
            "numeric_value": _num(value),
            "category": "Timeline",
            "target_kpi": f"slice_{c.s.get('slice_id')}",
            "filter_tag": tag + (f" · {c.dim_label}" if c.dim_label else ""),
            "matched_slices": {k: _num(v) for k, v in matched.items()},
            "auth_text": text,
            "sql": " ".join(sql.split()),
            "slice_id": c.s.get("slice_id"),
            "dashboard_id": c.s.get("dashboard_id"),
            "db": catalog.db_label_for(c.ds),
            "intent_summary": intent,
        }

    def _single_day(self, c: _Chart, spec: TemporalSpec) -> Dict[str, Any]:
        s, e = spec.start, spec.end
        sql = f"SELECT {c.metric} FROM {c.src}{c.where(f'{c.tcol} >= {_lit(s)}', f'{c.tcol} < {_lit(e)}')};"
        val = c.value(s, e)
        label = fmt_day(s)
        plotted = c.plotted(e)
        matched: Dict[str, Any] = {f"{c.metric_label} on {fmt_short(s)}": val}

        if val:
            text = f"On **{label}**, **{c.metric_label}**{self._for(c)} was **{_fmt(val)}**."
        else:
            prev = c.q(f"SELECT CAST(MAX({c.tcol}) AS DATE) FROM {c.src}{c.where(f'{c.tcol} < {_lit(s)}')}")
            nxt = c.q(f"SELECT CAST(MIN({c.tcol}) AS DATE) FROM {c.src}{c.where(f'{c.tcol} >= {_lit(e)}')}")
            near = []
            if prev and prev[0][0]:
                near.append(f"the previous record was on {fmt_short(prev[0][0])}")
            if nxt and nxt[0][0]:
                near.append(f"the next was on {fmt_short(nxt[0][0])}")
            text = (f"There were no records{self._for(c)} on **{label}** ({c.metric_label}: **0**)"
                    + (f"; {' and '.join(near)}." if near else "."))
        if plotted:
            text += f" The chart's {plotted[1]} at the end of that day was **{_fmt(plotted[0])}**."
            matched[plotted[1].capitalize()] = plotted[0]
        return self._result(c, val, fmt_short(s), text, sql, matched,
                            f"{c.metric_label}{self._for(c)} on {label}.", spec.notes)

    def _date_range(self, c: _Chart, spec: TemporalSpec) -> Dict[str, Any]:
        s, e = spec.start, spec.end
        sql = f"SELECT {c.metric} FROM {c.src}{c.where(f'{c.tcol} >= {_lit(s)}', f'{c.tcol} < {_lit(e)}')};"
        total = c.value(s, e)
        days = c.q(f"SELECT CAST(DATE_TRUNC('day', {c.tcol}) AS DATE), {c.metric} FROM {c.src}"
                   f"{c.where(f'{c.tcol} >= {_lit(s)}', f'{c.tcol} < {_lit(e)}')} GROUP BY 1")
        matched: Dict[str, Any] = {f"{c.metric_label} ({spec.label})": total}
        text = f"During **{spec.label}**, **{c.metric_label}**{self._for(c)} was **{_fmt(total)}**."
        if days:
            peak_d, peak_v = max(days, key=lambda r: (_num(r[1]), r[0]))
            text += (f" Records fall on {len(days):,} day{'s' if len(days) != 1 else ''}; the busiest was "
                     f"{fmt_day(peak_d)} with {_fmt(peak_v)}.")
            matched[f"Peak day {fmt_short(peak_d)}"] = peak_v
        plotted = c.plotted(e)
        if plotted:
            text += f" The chart's {plotted[1]} at the end of the period was **{_fmt(plotted[0])}**."
            matched[plotted[1].capitalize()] = plotted[0]
        return self._result(c, total, spec.label, text, sql, matched,
                            f"{c.metric_label}{self._for(c)} during {spec.label}.", spec.notes)

    def _as_of(self, c: _Chart, spec: TemporalSpec) -> Dict[str, Any]:
        e = spec.end
        plotted = c.plotted(e)
        if plotted:
            val, desc = plotted
        else:
            val, desc = c.value(None, e), c.metric_label
        sql = (f"SELECT DATE_TRUNC('{c.grain}', {c.tcol}), {c.metric} FROM {c.src}"
               f"{c.where(f'{c.tcol} < {_lit(e)}')} GROUP BY 1 ORDER BY 1;")
        text = f"The chart's {desc} of **{c.metric_label}**{self._for(c)} {spec.label} was **{_fmt(val)}**."
        return self._result(c, val, spec.label, text, sql, {desc.capitalize(): val},
                            f"{desc.capitalize()} of {c.metric_label}{self._for(c)} {spec.label}.", spec.notes)

    def _edge(self, c: _Chart, first: bool) -> Optional[Dict[str, Any]]:
        agg = "MIN" if first else "MAX"
        edge = c.q(f"SELECT CAST({agg}({c.tcol}) AS DATE) FROM {c.src}{c.where()}")
        if not edge or edge[0][0] is None:
            return None
        d = edge[0][0]
        e = d + timedelta(days=1)
        sql = f"SELECT {c.metric} FROM {c.src}{c.where(f'{c.tcol} >= {_lit(d)}', f'{c.tcol} < {_lit(e)}')};"
        val = c.value(d, e)
        word = "first" if first else "most recent"
        text = f"The {word} record{self._for(c)} is on **{fmt_day(d)}**, when **{c.metric_label}** was **{_fmt(val)}**."
        return self._result(c, val, fmt_short(d), text, sql, {f"{c.metric_label} on {fmt_short(d)}": val},
                            f"The {word} date with records{self._for(c)}.", [])

    def _extreme(self, c: _Chart, unit: str, lowest: bool) -> Optional[Dict[str, Any]]:
        order = "ASC" if lowest else "DESC"
        sql = (f"SELECT CAST(DATE_TRUNC('{unit}', {c.tcol}) AS DATE) AS period, {c.metric} AS value "
               f"FROM {c.src}{c.where()} GROUP BY 1 ORDER BY 2 {order}, 1 LIMIT 3;")
        rows = c.q(sql)
        if not rows:
            return None
        label = self._period_label(unit)
        top_p, top_v = rows[0]
        others = "; ".join(f"{label(p)}: {_fmt(v)}" for p, v in rows[1:])
        word = "lowest" if lowest else "highest"
        text = (f"The {unit} with the {word} **{c.metric_label}**{self._for(c)} was **{label(top_p)}**, "
                f"with **{_fmt(top_v)}**" + (f" (next: {others})." if others else "."))
        return self._result(c, top_v, label(top_p), text, sql, {label(p): v for p, v in rows},
                            f"The {unit} with the {word} {c.metric_label}{self._for(c)}.", [])

    def _trend(self, c: _Chart) -> Optional[Dict[str, Any]]:
        unit = c.grain if c.grain in ("quarter", "year") else "month"
        sql = (f"SELECT CAST(DATE_TRUNC('{unit}', {c.tcol}) AS DATE) AS period, {c.metric} AS value "
               f"FROM {c.src}{c.where()} GROUP BY 1 ORDER BY 1;")
        rows = c.q(sql)
        if not rows:
            return None
        label = self._period_label(unit)
        total = c.value(None, None)
        top_p, top_v = max(rows, key=lambda r: _num(r[1]))
        recent = ", ".join(f"{label(p)}: {_fmt(v)}" for p, v in rows[-6:])
        text = (f"**{c.metric_label}**{self._for(c)} runs from **{label(rows[0][0])}** to **{label(rows[-1][0])}**, "
                f"**{_fmt(total)}** overall. The busiest {unit} was **{label(top_p)}** with **{_fmt(top_v)}**. "
                f"Most recent {unit}s: {recent}.")
        return self._result(c, total, f"{unit.capitalize()}-wise trend", text, sql,
                            {label(p): v for p, v in rows[-6:]}, f"{unit.capitalize()}-wise trend of {c.metric_label}{self._for(c)}.", [])

    @staticmethod
    def _period_label(unit: str):
        if unit == "month":
            return lambda d: d.strftime("%B %Y")
        if unit == "year":
            return lambda d: str(d.year)
        if unit == "quarter":
            return lambda d: f"Q{(d.month - 1) // 3 + 1} {d.year}"
        if unit == "week":
            return lambda d: f"week of {fmt_short(d)}"
        return fmt_day
