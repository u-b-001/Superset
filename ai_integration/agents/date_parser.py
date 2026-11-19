"""
Natural-language date parsing for timeline questions.

Understands phrases such as:
    "on saturday april 5", "5th April 2025", "2025-04-05", "05/04/2025",
    "in april", "april 2025", "in 2025", "today", "yesterday", "last week",
    "this month", "last 30 days", "between 1 may and 15 may",
    "from april to june 2025", "since march", "before 1 june", "as of oct 27".

When the year is missing it is inferred: if a weekday is given ("saturday april 5")
the most recent year in which that date fell on that weekday is used, otherwise the
most recent past occurrence of the date.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5, "sun": 6, "sunday": 6,
}
_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_WD = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(?:rs?)?|fri|sat|sun)"
_ORD = r"(?:st|nd|rd|th)?"
_YEAR = r"((?:19|20)\d{2})"


@dataclass
class _Mention:
    start: date
    end: date                 # exclusive
    granularity: str          # day | month | year | span
    span: tuple
    label: str
    year_explicit: bool = True
    month: int = 0
    day: int = 0
    weekday: Optional[int] = None


@dataclass
class TemporalSpec:
    """A resolved time window.

    mode:
      day    - a single calendar day
      range  - a closed window [start, end)
      until  - cumulative total for everything before ``end``
    """
    mode: str
    start: Optional[date]
    end: date                 # exclusive
    label: str
    granularity: str = "day"
    notes: List[str] = field(default_factory=list)
    spans: List[tuple] = field(default_factory=list)   # character spans of the date phrases in the question


def fmt_day(d: date) -> str:
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


def fmt_short(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _month_end(y: int, m: int) -> date:
    return date(y + (m == 12), (m % 12) + 1, 1)


def _infer_day_year(m: int, d: int, weekday: Optional[int], today: date) -> Optional[date]:
    """Most recent past date for (month, day); honours a weekday when one is given."""
    fallback = None
    for y in range(today.year, today.year - 12, -1):
        cand = _safe_date(y, m, d)
        if cand is None or cand > today:
            continue
        if fallback is None:
            fallback = cand
        if weekday is None or cand.weekday() == weekday:
            return cand
    return fallback


def _infer_month_year(m: int, today: date) -> int:
    return today.year if date(today.year, m, 1) <= today else today.year - 1


def _overlaps(span, taken) -> bool:
    return any(span[0] < t[1] and t[0] < span[1] for t in taken)


def _find_mentions(q: str, today: date) -> List[_Mention]:
    found: List[_Mention] = []
    taken: list = []

    def add(m: _Mention):
        if not _overlaps(m.span, taken):
            found.append(m)
            taken.append(m.span)

    def weekday_before(pos: int) -> Optional[int]:
        prefix = q[max(0, pos - 14):pos]
        wm = re.search(_WD + r"[,\s]*(?:the\s+)?$", prefix)
        return WEEKDAYS[wm.group(1)] if wm else None

    def day_mention(match, y, m, d, year_explicit, wd):
        if y is None:
            dt = _infer_day_year(m, d, wd, today)
        else:
            dt = _safe_date(y, m, d)
        if dt is None:
            return
        add(_Mention(dt, dt + timedelta(days=1), "day", match.span(), fmt_day(dt),
                     year_explicit, m, d, wd))

    # 1. ISO dates: 2025-04-05
    for mt in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", q):
        day_mention(mt, int(mt.group(1)), int(mt.group(2)), int(mt.group(3)), True, weekday_before(mt.start()))

    # 2. Numeric dates, Indian order dd/mm/yyyy (swapped when clearly mm/dd)
    for mt in re.finditer(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b", q):
        a, b, y = int(mt.group(1)), int(mt.group(2)), int(mt.group(3))
        y = y + 2000 if y < 100 else y
        d, m = (a, b) if b <= 12 else (b, a)
        day_mention(mt, y, m, d, True, weekday_before(mt.start()))

    # 3. "5 april 2025", "5th of april"
    for mt in re.finditer(r"\b(\d{1,2})" + _ORD + r"\s+(?:of\s+)?" + _MON + r"\b\.?(?:,?\s+" + _YEAR + r"\b)?", q):
        y = int(mt.group(3)) if mt.group(3) else None
        day_mention(mt, y, MONTHS[mt.group(2)], int(mt.group(1)), y is not None, weekday_before(mt.start()))

    # 4. "april 5", "april 5th, 2025"
    for mt in re.finditer(r"\b" + _MON + r"\.?\s+(\d{1,2})" + _ORD + r"\b(?:,?\s+" + _YEAR + r"\b)?", q):
        y = int(mt.group(3)) if mt.group(3) else None
        day_mention(mt, y, MONTHS[mt.group(1)], int(mt.group(2)), y is not None, weekday_before(mt.start()))

    # 5. Month + year: "april 2025"
    for mt in re.finditer(r"\b" + _MON + r"\.?,?\s+" + _YEAR + r"\b", q):
        m, y = MONTHS[mt.group(1)], int(mt.group(2))
        st = date(y, m, 1)
        add(_Mention(st, _month_end(y, m), "month", mt.span(), st.strftime("%B %Y"), True, m))

    # 6. Month alone after a preposition: "in april", "since march", "april month"
    for mt in re.finditer(r"\b(?:in|during|of|for|since|from|till|until|before|after|by|through|to|and|between|month\s+of)\s+(?:the\s+month\s+of\s+)?" + _MON + r"\b"
                          r"|\b" + _MON + r"\s+month\b", q):
        name = mt.group(1) or mt.group(2)
        m = MONTHS[name]
        y = _infer_month_year(m, today)
        st = date(y, m, 1)
        span = (mt.start(1) if mt.group(1) else mt.start(2), mt.end())
        add(_Mention(st, _month_end(y, m), "month", span, st.strftime("%B %Y"), False, m))

    # 7. Year alone: "in 2025"
    for mt in re.finditer(r"\b" + _YEAR + r"\b", q):
        y = int(mt.group(1))
        add(_Mention(date(y, 1, 1), date(y + 1, 1, 1), "year", mt.span(), str(y), True))

    # 8. Relative expressions
    tomorrow = today + timedelta(days=1)
    rel = [
        (r"\btoday\b", lambda mt: (today, tomorrow, "day", fmt_day(today))),
        (r"\byesterday\b", lambda mt: (today - timedelta(days=1), today, "day", fmt_day(today - timedelta(days=1)))),
        (r"\bthis\s+week\b", lambda mt: (today - timedelta(days=today.weekday()), tomorrow, "span", "this week")),
        (r"\blast\s+week\b|\bprevious\s+week\b", lambda mt: (
            today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday()), "span", "last week")),
        (r"\bthis\s+month\b", lambda mt: (today.replace(day=1), tomorrow, "month", "this month")),
        (r"\blast\s+month\b|\bprevious\s+month\b", lambda mt: (
            (today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1), "month",
            (today.replace(day=1) - timedelta(days=1)).strftime("%B %Y"))),
        (r"\bthis\s+year\b", lambda mt: (date(today.year, 1, 1), tomorrow, "year", str(today.year))),
        (r"\blast\s+year\b|\bprevious\s+year\b", lambda mt: (
            date(today.year - 1, 1, 1), date(today.year, 1, 1), "year", str(today.year - 1))),
        (r"\b(?:last|past|previous)\s+(\d{1,3})\s+(day|week|month)s?\b", lambda mt: (
            tomorrow - timedelta(days=int(mt.group(1)) * {"day": 1, "week": 7, "month": 30}[mt.group(2)]),
            tomorrow, "span", f"the last {mt.group(1)} {mt.group(2)}s")),
    ]
    for pat, fn in rel:
        for mt in re.finditer(pat, q):
            st, en, gran, label = fn(mt)
            add(_Mention(st, en, gran, mt.span(), label, True))

    found.sort(key=lambda m: m.span[0])
    return found


def parse_temporal(question: str, today: Optional[date] = None) -> Optional[TemporalSpec]:
    """Resolve the time window a question refers to, or None when it names no date."""
    today = today or date.today()
    q = question.lower()
    mentions = _find_mentions(q, today)
    spec = _resolve(q, mentions, today)
    if spec:
        spec.spans = [m.span for m in mentions]
    return spec


def _resolve(q: str, mentions: List[_Mention], today: date) -> Optional[TemporalSpec]:
    if not mentions:
        return None

    notes: List[str] = []

    # Borrow an explicit year for partial dates in ranges: "between april 5 and april 10 2025"
    explicit_years = [m.start.year for m in mentions if m.year_explicit and m.granularity in ("day", "month")]
    if explicit_years:
        for m in mentions:
            if not m.year_explicit and m.granularity == "day":
                dt = _safe_date(explicit_years[-1], m.month, m.day)
                if dt:
                    m.start, m.end, m.label, m.year_explicit = dt, dt + timedelta(days=1), fmt_day(dt), True
            elif not m.year_explicit and m.granularity == "month":
                st = date(explicit_years[-1], m.month, 1)
                m.start, m.end, m.label, m.year_explicit = st, _month_end(st.year, m.month), st.strftime("%B %Y"), True

    for m in mentions:
        if m.granularity == "day" and not m.year_explicit:
            if m.weekday is not None and m.start.weekday() == m.weekday:
                notes.append(f"No year was given, so {m.start.year} was used: the most recent year in which "
                             f"{m.start.day} {m.start.strftime('%B')} fell on a {m.start.strftime('%A')}.")
            else:
                notes.append(f"No year was given, so the most recent {m.start.day} {m.start.strftime('%B')} "
                             f"({m.start.year}) was used.")
        if m.granularity == "day" and m.weekday is not None and m.start.weekday() != m.weekday:
            notes.append(f"Note: {fmt_short(m.start)} was a {m.start.strftime('%A')}, not a "
                         f"{_WEEKDAY_NAMES[m.weekday]}.")

    if len(mentions) >= 2:
        a, b = mentions[0], mentions[-1]
        start, end = a.start, b.end
        if start >= end and not a.year_explicit:
            # "from november to march" -> november of the previous year
            try:
                start = start.replace(year=start.year - 1)
            except ValueError:
                start = start - timedelta(days=365)
        label = f"{fmt_short(start)} – {fmt_short(end - timedelta(days=1))}"
        return TemporalSpec("range", start, end, label, "span", notes)

    m = mentions[0]
    before = q[max(0, m.span[0] - 16):m.span[0]]
    if re.search(r"\b(since|after|from)\s+(?:the\s+)?$", before) and not re.search(r"\b(to|till|until)\b", q[m.span[1]:]):
        start = m.end if re.search(r"\bafter\s+(?:the\s+)?$", before) else m.start
        end = today + timedelta(days=1)
        return TemporalSpec("range", start, end, f"{fmt_short(start)} – {fmt_short(today)}", "span", notes)
    if re.search(r"\bbefore\s+(?:the\s+)?$", before):
        return TemporalSpec("until", None, m.start, f"before {m.label}", m.granularity, notes)
    if re.search(r"\b(until|till|by|upto|up\s+to|as\s+of|as\s+on|through)\s+(?:the\s+)?(?:end\s+of\s+)?$", before):
        return TemporalSpec("until", None, m.end, f"by the end of {m.label}", m.granularity, notes)

    mode = "day" if m.granularity == "day" else "range"
    return TemporalSpec(mode, m.start, m.end, m.label, m.granularity, notes)
