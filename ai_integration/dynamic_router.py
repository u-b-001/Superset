"""
Supervisor for the dashboard chatbot.

Splits question answering across specialist subagents instead of one long if-chain:

    TimelineAgent  - onboarding by date / range / trend      (slice 27, org_db)
    StaffAgent     - teachers & employees                    (employee_db)
    SchoolAgent    - school counts by management/type/level  (org_db)
    CatalogAgent   - any other Superset chart (fallback)

Every agent scores the question; agents are tried from the highest score down and the
first one that returns a result answers. Agents that scored 0 are still tried last, so
nothing the old single resolver could answer is lost.

``websocket_server.py`` imports ``resolve_query`` and ``normalize_query_text`` from here.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

try:
    from ai_integration.agents import CatalogAgent, QueryContext, SchoolAgent, StaffAgent, TimelineAgent  # type: ignore
    from ai_integration.agents.base import BaseAgent  # type: ignore
    from ai_integration.chart_engine import normalize_query_text  # type: ignore
except ImportError:
    from agents import CatalogAgent, QueryContext, SchoolAgent, StaffAgent, TimelineAgent  # type: ignore
    from agents.base import BaseAgent  # type: ignore
    from chart_engine import normalize_query_text  # type: ignore

logger = logging.getLogger("samarthx.router")

# Order breaks score ties.
AGENTS: List[BaseAgent] = [TimelineAgent(), StaffAgent(), SchoolAgent(), CatalogAgent()]


def build_context(question: str, raw_numeric: Optional[int] = None,
                  dashboard_context: Optional[Dict[str, Any]] = None,
                  today: Optional[date] = None) -> QueryContext:
    text = normalize_query_text(question)
    return QueryContext(raw=question, text=text, lower=text.lower().strip(), raw_numeric=raw_numeric,
                        dashboard_context=dashboard_context or {}, today=today or date.today())


def rank_agents(ctx: QueryContext) -> List[Tuple[BaseAgent, float]]:
    scored = []
    for agent in AGENTS:
        try:
            scored.append((agent, float(agent.score(ctx))))
        except Exception as e:  # a broken scorer must not take the router down
            logger.warning(f"[router] {agent.name}.score failed: {e}")
            scored.append((agent, 0.0))
    order = {a.name: i for i, a in enumerate(AGENTS)}
    return sorted(scored, key=lambda p: (-p[1], order[p[0].name]))


def resolve_query(question: str, raw_numeric: Optional[int] = None,
                  dashboard_context: Optional[Dict[str, Any]] = None,
                  today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """Route the question to the best subagent and return its chart-aligned answer."""
    ctx = build_context(question, raw_numeric, dashboard_context, today)
    ranked = rank_agents(ctx)
    ranking = {a.name: round(s, 2) for a, s in ranked}

    for agent, score in ranked:
        try:
            result = agent.handle(ctx)
        except Exception as e:
            logger.warning(f"[router] {agent.name} failed on {question!r}: {e}")
            continue
        if result:
            result["agent"] = agent.name
            result["routing"] = ranking
            logger.info(f"[router] {question!r} -> {agent.name} (scores {ranking})")
            return result

    logger.info(f"[router] {question!r} -> no agent matched (scores {ranking}); falling back to n8n")
    return None


__all__ = ["resolve_query", "normalize_query_text", "rank_agents", "build_context", "AGENTS"]
