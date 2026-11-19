"""
Language-level helpers for matching questions to Superset metadata.

Nothing here knows about specific charts, tables or dashboards — only English
(stop words, plural/verb endings, common abbreviations).
"""

import re
from typing import Dict, Iterable, List, Set, Tuple

STOP_WORDS: Set[str] = {
    # question / filler words
    "a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "at", "by", "with", "from", "into", "per", "each",
    "all", "any", "how", "many", "much", "what", "which", "who", "whom", "whose", "when", "where", "why", "is", "are",
    "was", "were", "be", "been", "being", "do", "does", "did", "have", "has", "had", "get", "got", "gets", "getting",
    "there", "their", "this", "that", "these", "those", "it", "its", "me", "my", "we", "our", "you", "your", "i",
    "show", "tell", "give", "list", "find", "please", "can", "could", "would", "will", "should", "about", "so", "far",
    "number", "count", "total", "totals", "value", "values", "amount", "chart", "graph", "dashboard", "timeline",
    "trend", "trends", "over", "time", "new", "recorded", "record", "records", "data", "till", "until", "since",
    "between", "during", "before", "after", "as", "up", "upto", "than", "more", "less", "most", "least",
    # time vocabulary (handled by the date parser)
    "today", "yesterday", "day", "days", "daily", "date", "dates", "week", "weeks", "weekly", "month", "months",
    "monthly", "year", "years", "yearly", "quarter", "period", "first", "last", "latest", "earliest", "recent",
    "recently", "peak", "busiest", "highest", "lowest", "maximum", "minimum", "wise", "this", "previous", "next",
    "jan", "january", "feb", "february", "mar", "march", "apr", "april", "may", "jun", "june", "jul", "july",
    "aug", "august", "sep", "sept", "september", "oct", "october", "nov", "november", "dec", "december",
    "mon", "monday", "tue", "tuesday", "wed", "wednesday", "thu", "thursday", "fri", "friday", "sat", "saturday",
    "sun", "sunday",
    # SQL-ish words that appear in metric labels
    "distinct", "id", "sum", "avg", "max", "min", "metric",
}

# Spelling variants that should compare equal.
SYNONYMS: Dict[str, str] = {
    "government": "govt", "gov": "govt", "department": "dept", "management": "mgmt", "organisation": "organization",
}


def stem(word: str) -> str:
    w = SYNONYMS.get(word, word)
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 4 and w.endswith(("sses", "xes", "ches", "shes")):
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    return SYNONYMS.get(w, w)


def words(text: str) -> List[Tuple[str, int, int]]:
    """(lower-cased word, start, end) for every alphanumeric word."""
    return [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"[A-Za-z0-9]+", text or "")]


def content_stems(text: str) -> Set[str]:
    """Distinctive word stems of a text (stop words and pure numbers removed)."""
    return {stem(w) for w, _, _ in words(text) if w not in STOP_WORDS and not w.isdigit() and len(w) > 1}


def stems_of(parts: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for p in parts:
        if p:
            out |= content_stems(str(p).replace("_", " "))
    return out
