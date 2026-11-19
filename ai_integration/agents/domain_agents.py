"""
Staff, School and Catalog subagents.

These wrap the existing, verified chart routes in ``chart_engine.align_query_to_charts``
but each one is restricted to its own route group via the ``domains`` argument, so a
staff question can never be answered by a school route (and vice-versa).
"""

import re
from typing import Any, Dict, Optional

from .base import BaseAgent, QueryContext

try:
    from ai_integration.chart_engine import align_query_to_charts, detect_school_dimensions  # type: ignore
except ImportError:
    from chart_engine import align_query_to_charts, detect_school_dimensions  # type: ignore


_STAFF_SIGNAL = re.compile(
    r"\b(teachers?|teaching|non[\s-]?teaching|faculty|academic|staff|employees?|workforce|clerks?|administrative|"
    r"female|women|woman|male|men|transgender|trans|gender|"
    r"sc|st|obc|scheduled\s+(?:caste|tribe)|other\s+backward|caste|social\s+category|general\s+category|"
    r"regular|permanent|confirmed|non[\s-]?regular|contract(?:ual)?|temporary|adhoc|guest|"
    r"experience|exp|yrs?|designations?|heads?\s+of\s+(?:the\s+)?institutions?|hoi|acting\s+head|lecturers?|vocational)\b"
)
_SCHOOL_SIGNAL = re.compile(r"\b(schools?|institutions?|onboard\w*)\b")


class StaffAgent(BaseAgent):
    name = "staff"
    description = "Employees & teachers from employee_db (gender, category, appointment, experience, designation)"

    def score(self, ctx: QueryContext) -> float:
        return 0.7 if _STAFF_SIGNAL.search(ctx.lower) else 0.0

    def handle(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        res = align_query_to_charts(ctx.text, ctx.raw_numeric, ctx.dashboard_context, domains={"staff"})
        if res:
            res.setdefault("db", "PostgreSQL (employee_db)")
        return res


class SchoolAgent(BaseAgent):
    name = "school"
    description = "School counts from org_db (management type, school type, education level, total onboarded)"

    def score(self, ctx: QueryContext) -> float:
        if _SCHOOL_SIGNAL.search(ctx.lower) or any(detect_school_dimensions(ctx.lower)):
            return 0.6
        return 0.0

    def handle(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        res = align_query_to_charts(ctx.text, ctx.raw_numeric, ctx.dashboard_context, domains={"school"})
        if res:
            res.setdefault("db", "PostgreSQL (org_db)")
        return res


class CatalogAgent(BaseAgent):
    name = "catalog"
    description = "Fallback: matches any other Superset chart from the live dashboard catalog"

    def score(self, ctx: QueryContext) -> float:
        return 0.1

    def handle(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        return align_query_to_charts(ctx.text, ctx.raw_numeric, ctx.dashboard_context, domains={"catalog"})
