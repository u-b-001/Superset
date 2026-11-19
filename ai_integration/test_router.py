"""
Tests for the subagent router.

    python ai_integration/test_router.py            # date parsing + routing (needs Superset metadata DB)
    python ai_integration/test_router.py --live     # also runs queries against the chart databases

No chart names, slice ids or tables are assumed by the timeline agent; the routing test
injects a brand-new synthetic timeline chart to prove new charts are picked up automatically.
"""

import copy
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.date_parser import parse_temporal  # noqa: E402
from dynamic_catalog import dynamic_catalog  # noqa: E402
from dynamic_router import build_context, rank_agents, resolve_query  # noqa: E402

TODAY = date(2026, 11, 16)
failures = 0


def check(label, got, want):
    global failures
    ok = got == want
    failures += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f"  (expected {want!r})"))


print("Date parsing")
cases = [
    ("how many schools get onboarded on saturday april 5", ("day", date(2025, 4, 5), date(2025, 4, 6))),
    ("schools onboarded on 5th april 2025", ("day", date(2025, 4, 5), date(2025, 4, 6))),
    ("schools onboarded on 2025-10-27", ("day", date(2025, 10, 27), date(2025, 10, 28))),
    ("schools onboarded on 27/10/2025", ("day", date(2025, 10, 27), date(2025, 10, 28))),
    ("schools onboarded in may 2025", ("range", date(2025, 5, 1), date(2025, 6, 1))),
    ("schools onboarded in 2025", ("range", date(2025, 1, 1), date(2026, 1, 1))),
    ("schools onboarded between 1 june and 30 june 2025", ("range", date(2025, 6, 1), date(2025, 7, 1))),
    ("schools onboarded from april to june 2025", ("range", date(2025, 4, 1), date(2025, 7, 1))),
    ("how many schools were onboarded by oct 27 2025", ("until", None, date(2025, 10, 28))),
    ("schools onboarded before 1 june 2025", ("until", None, date(2025, 6, 1))),
    ("schools onboarded yesterday", ("day", date(2026, 11, 15), date(2026, 11, 16))),
    ("schools onboarded last month", ("range", date(2026, 10, 1), date(2026, 11, 1))),
    ("how many schools are onboarded", None),
]
for q, want in cases:
    spec = parse_temporal(q, TODAY)
    check(q, (spec.mode, spec.start, spec.end) if spec else None, want)

if not dynamic_catalog.refresh():
    print("\nSuperset metadata DB unreachable — skipping routing tests.")
    sys.exit(1 if failures else 0)

ts = dynamic_catalog.time_series_slices()
print(f"\nDiscovered time-series charts: {[(s['slice_id'], s['slice_name']) for s in ts]}")

print("\nRouting (top agent)")
routes = [
    ("how many schools get onboarded on saturday april 5", "timeline"),
    ("when was the first school onboarded", "timeline"),
    ("show the monthly onboarding trend", "timeline"),
    ("which day had the most onboardings", "timeline"),
    ("how many schools are onboarded", "school"),
    ("how many aided schools", "school"),
    ("which school type has the most schools", "school"),
    ("how many female teachers", "staff"),
    ("teachers with more than 20 years experience", "staff"),
    ("how many regular teachers", "staff"),
]
for q, want in routes:
    check(q, rank_agents(build_context(q, today=TODAY))[0][0].name, want)

# ── A chart that exists nowhere in the code: built from an existing chart's dataset ──
template = next((s for s in ts if s["dataset"].get("columns")), None)
if template:
    ds = template["dataset"]
    dttm_cols = [c for c, i in ds["columns"].items() if i.get("is_dttm") and c != (template["params"].get("x_axis"))]
    if dttm_cols:
        fake = copy.deepcopy(template)
        fake.update(slice_id=990001, slice_name="Zephyr Renewals",
                    dashboard_id=990, dashboard_title="Synthetic Test Dashboard")
        fake["params"] = {**template["params"], "x_axis": dttm_cols[0], "time_grain_sqla": "P1M",
                          "rolling_type": None, "rolling_periods": None}
        dynamic_catalog.slices[990001] = fake
        q = "how many zephyr renewals happened in may 2025"
        ctx = build_context(q, dashboard_context={"dashboard_id": 990}, today=TODAY)
        top = rank_agents(ctx)[0][0]
        check(f"new chart '{fake['slice_name']}' -> {q!r}", top.name, "timeline")
        if "--live" in sys.argv:
            r = top.handle(ctx)
            check("new chart answered from its own slice", r and r.get("slice_id"), 990001)
            print(f"     {r and r.get('auth_text')}")
        del dynamic_catalog.slices[990001]

if "--live" in sys.argv:
    print("\nLive answers")
    for q in [
        "how many schools get onboarded on saturday april 5",
        "how many schools were onboarded on oct 27 2025",
        "how many schools were onboarded by oct 27 2025",
        "schools onboarded in may 2025",
        "when was the first school onboarded",
        "which day had the most onboardings",
        "which month had the most onboardings",
        "monthly onboarding trend",
        "how many aided schools onboarded in 2025",
        "how many english medium schools onboarded in may 2025",
        "how many employees were created in 2025",
        "how many schools are onboarded",
        "how many female teachers",
    ]:
        r = resolve_query(q, today=TODAY)
        print(f"\n  Q: {q}\n  -> agent={r and r.get('agent')} value={r and r.get('value')} slice={r and r.get('slice_id')} "
              f"db={r and r.get('db')}\n     {r and r.get('auth_text')}")
    first = resolve_query("how many schools get onboarded on saturday april 5", today=TODAY)
    check("saturday april 5 -> 19", first and first.get("value"), "19")
    asof = resolve_query("how many schools were onboarded by oct 27 2025", today=TODAY)
    check("as of 27 Oct 2025 matches chart tooltip 1,439", asof and asof.get("value"), "1,439")

print(f"\n{'All checks passed' if not failures else f'{failures} check(s) FAILED'}")
sys.exit(1 if failures else 0)
