"""
Shared building blocks for the chatbot subagents.

Each subagent owns one group of questions (staff, schools, onboarding timeline, ...).
The supervisor in ``ai_integration/dynamic_router.py`` asks every agent how confident
it is (``score``) and hands the question to the best one (``handle``).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class QueryContext:
    """Everything a subagent needs to answer one question."""
    raw: str                      # question exactly as the user typed it
    text: str                     # typo-normalised question
    lower: str                    # lower-cased normalised question
    raw_numeric: Optional[int] = None
    dashboard_context: Dict[str, Any] = field(default_factory=dict)
    today: date = field(default_factory=date.today)
    scratch: Dict[str, Any] = field(default_factory=dict)   # agents cache work between score() and handle()


class BaseAgent:
    """A specialist that answers one group of dashboard questions."""

    name: str = "base"
    description: str = ""

    def score(self, ctx: QueryContext) -> float:
        """Confidence in [0, 1] that this agent owns the question. 0 = not mine."""
        raise NotImplementedError

    def handle(self, ctx: QueryContext) -> Optional[Dict[str, Any]]:
        """Return a chart-aligned result dict, or None to let the next agent try."""
        raise NotImplementedError
