"""Campaign test results: reads the counts from the Cloudflare worker (GET /stats) every day and compares
version A (inspiration) with version B (practical).

Measures, per version: views, engaged readers (half the page or 30 s), clicks on "Plan your trip" (main goal),
on entry rules and on train tickets. Main comparison: share of views that clicked "Plan your trip", U.S.
visitors only (the target market), with a two-proportion z-test. Until each version has MIN_VIEWS U.S. views
the result is reported as "too early".
The worker address is read from docs/visit/track.js (window.TRACK_URL), the same file the pages use.
"""
from __future__ import annotations

import math
import re

import pandas as pd

from . import config
from .util import http_get, log

TRACK_JS = config.ROOT / "docs" / "visit" / "track.js"
OUT = config.DATA / "campaign_hits.csv"
MIN_VIEWS = 100
EVENTS = ["view", "engaged", "cta_plan", "cta_rules", "cta_route"]


def worker_url() -> str:
    if not TRACK_JS.exists():
        return ""
    m = re.search(r'TRACK_URL\s*=\s*"([^"]*)"', TRACK_JS.read_text(encoding="utf-8"))
    return (m.group(1) if m else "").rstrip("/")


def collect() -> int:
    url = worker_url()
    if not url:
        log.info("campaign: counting not configured (docs/visit/track.js is empty)")
        return 0
    data = http_get(url + "/stats", as_json=True)
    if not data or "rows" not in data:
        log.warning("campaign: no answer from %s/stats", url)
        return 0
    df = pd.DataFrame(data["rows"], columns=["day", "v", "e", "country", "src", "n"])
    df.to_csv(OUT, index=False)
    log.info("campaign: %d count rows saved", len(df))
    return len(df)


def load() -> pd.DataFrame:
    return pd.read_csv(OUT, keep_default_na=False) if OUT.exists() else pd.DataFrame(columns=["day", "v", "e", "country", "src", "n"])


def ztest(k1: int, n1: int, k2: int, n2: int) -> float | None:
    """Two-sided p-value for 'the two click rates are equal'."""
    if min(n1, n2) == 0:
        return None
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def summary(df: pd.DataFrame | None = None, country: str | None = "US") -> dict:
    df = load() if df is None else df
    if df.empty:
        return {"rows": [], "verdict": "no_data", "p": None, "days": 0}
    d = df if country is None else df[df["country"] == country]
    t = d.pivot_table(index="v", columns="e", values="n", aggfunc="sum", fill_value=0).reindex(index=["a", "b"], columns=EVENTS, fill_value=0)
    rows = []
    for v, r in t.iterrows():
        views = int(r["view"])
        rows.append({"v": v, **{e: int(r[e]) for e in EVENTS},
                     "engaged_rate": r["engaged"] / views if views else None, "plan_rate": r["cta_plan"] / views if views else None})
    a, b = rows
    p = ztest(a["cta_plan"], a["view"], b["cta_plan"], b["view"])
    if min(a["view"], b["view"]) < MIN_VIEWS:
        verdict = "too_early"
    elif p is not None and p < 0.05:
        verdict = "a_wins" if a["plan_rate"] > b["plan_rate"] else "b_wins"
    else:
        verdict = "no_difference"
    return {"rows": rows, "p": p, "verdict": verdict, "days": int(df["day"].nunique()),
            "first": df["day"].min(), "last": df["day"].max(), "country": country,
            "by_source": df.groupby(["src"])["n"].sum().to_dict() if not df.empty else {}}


if __name__ == "__main__":
    collect()
    print(summary())
    print(summary(country=None))
