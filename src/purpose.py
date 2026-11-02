"""Leisure tourists ("dam olish va sayohat" purpose) by country: the segment attraction policy works on.

Official data (see data/purpose_yearly.csv, data/purpose_by_country.csv):
  - national arrivals by purpose, yearly 2016-2025 (SIAT): relatives / leisure / business / other;
  - leisure arrivals BY COUNTRY only as snapshots (stat.uz releases): Jan-Jun 2025 (12 countries + other),
    Jan-Oct 2023 (14 countries, full purpose split).
There is no official monthly leisure series by country, so it is ESTIMATED here:
  leisure(country, month) = arrivals(country, month) x leisure share(country)
  share = leisure Jan-Jun 2025 / arrivals Jan-Jun 2025 (latest snapshot); 2023 snapshot as fallback;
  every other country (incl. Afghanistan) gets the share of the "other countries" group.
The key assumption -- shares stay stable over time -- is TESTED: the 2025 shares are applied to the 2023 and
2024 country totals and the sum is compared with the official national leisure figure of that year.
"""
from __future__ import annotations

import pandas as pd

from . import config, scorecard, statuz

YEARLY = config.DATA / "purpose_yearly.csv"
BY_COUNTRY = config.DATA / "purpose_by_country.csv"
OUT = config.DATA / "leisure_estimates.csv"
SNAP = "2025-01..06"
FALLBACK = "2023-01..10"
# countries listed in (almost) every monthly stat.uz release; the rest are estimated as one "other" group
MONTHLY = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Russia", "Turkmenistan", "China", "Türkiye", "India"]
NAME_UZ = scorecard.NAME_UZ | {"Italy": "Italiya", "Germany": "Germaniya", "United States": "AQSH",
                                "Afghanistan": "Afg'oniston", "OTHER": "Boshqa davlatlar"}


def _h1_arrivals(ytd: pd.DataFrame, yearly: pd.DataFrame, country: str) -> float | None:
    """Arrivals Jan-Jun 2025. The June 2025 release has no country list, so June is interpolated between the
    April and July year-to-date figures; countries outside the monthly list use the yearly total x the
    national Jan-Jun share."""
    c = ytd[(ytd["year"] == 2025) & (ytd["country"] == country)].set_index("month")["ytd"]
    if 4 in c.index and 7 in c.index:
        return float(c[4] + (c[7] - c[4]) * 2 / 3)
    tot = ytd[(ytd["year"] == 2025) & (ytd["country"] == "TOTAL")].set_index("month")["ytd"]
    y = yearly[(yearly["year"] == 2025)].set_index("country")["arrivals"]
    if country in y.index and 6 in tot.index and "TOTAL" in y.index:
        return float(y[country] * tot[6] / y["TOTAL"])
    return None


def shares(ytd: pd.DataFrame | None = None, yearly: pd.DataFrame | None = None) -> pd.DataFrame:
    """Leisure share per country (+ OTHER), with source."""
    ytd = statuz.load() if ytd is None else ytd
    yearly = statuz.load_yearly() if yearly is None else yearly
    p = pd.read_csv(BY_COUNTRY)
    snap = p[p["period"] == SNAP].set_index("country")["leisure"]
    old = p[p["period"] == FALLBACK].set_index("country")
    rows, named_arr, named_leis = [], 0.0, 0.0
    for country, leis in snap.items():
        if country == "Other":
            continue
        arr = _h1_arrivals(ytd, yearly, country)
        if not arr:
            continue
        rows.append({"country": country, "share": leis / arr, "leisure_h1": leis, "arrivals_h1": round(arr),
                     "source": "stat.uz 2025 I yarim yillik"})
        named_arr += arr
        named_leis += leis
    tot = ytd[(ytd["year"] == 2025) & (ytd["country"] == "TOTAL")].set_index("month")["ytd"]
    other_arr = float(tot[6]) - named_arr
    other_leis = float(snap.get("Other", 0))
    rows.append({"country": "OTHER", "share": other_leis / other_arr, "leisure_h1": other_leis,
                 "arrivals_h1": round(other_arr), "source": "stat.uz 2025 I yarim yillik (qolgan davlatlar)"})
    out = pd.DataFrame(rows)
    # 2023 snapshot: kept for comparison (did the share change?)
    out["share_2023"] = out["country"].map(lambda c: old.loc[c, "leisure"] / old.loc[c, "total"] if c in old.index else None)
    return out


def share_of(sh: pd.DataFrame, country: str) -> float:
    s = sh.set_index("country")["share"]
    return float(s.get(country, s["OTHER"]))


def validate(sh: pd.DataFrame, yearly: pd.DataFrame | None = None) -> list[dict]:
    """Apply the 2025 shares to each year's country totals; compare with the official national leisure total."""
    yearly = statuz.load_yearly() if yearly is None else yearly
    official = pd.read_csv(YEARLY).set_index("year")["leisure_k"] * 1000
    out = []
    for yr in (2022, 2023, 2024, 2025):
        y = yearly[yearly["year"] == yr]
        if y.empty or yr not in official.index:
            continue
        total = int(y[y["country"] == "TOTAL"]["arrivals"].sum())
        named = y[y["country"].isin(sh["country"])]
        est = sum(r.arrivals * share_of(sh, r.country) for r in named.itertuples())
        est += (total - int(named["arrivals"].sum())) * share_of(sh, "OTHER")
        out.append({"year": yr, "estimate": round(est), "official": int(official[yr]),
                    "error_pct": round((est / official[yr] - 1) * 100, 1), "in_sample": yr == 2025})
    return out


def monthly(sh: pd.DataFrame, ytd: pd.DataFrame | None = None, yearly: pd.DataFrame | None = None) -> pd.DataFrame:
    """Estimated leisure arrivals per month and country (true single months only), plus OTHER and TOTAL."""
    ytd = statuz.load() if ytd is None else ytd
    yearly = statuz.load_yearly() if yearly is None else yearly
    countries = [c for c in MONTHLY if c in set(sh["country"])]
    tot = scorecard.monthly_points(ytd, yearly, "TOTAL")
    rows = []
    for m, t in sorted(tot.items()):
        if t["kind"] == "long" or m < "2023-01":
            continue
        named_arr = named_leis = 0.0
        for c in countries:
            pts = scorecard.monthly_points(ytd, yearly, c)
            if m not in pts:
                continue
            a = pts[m]["v"]
            named_arr += a
            named_leis += a * share_of(sh, c)
            rows.append({"month": m, "country": c, "arrivals": round(a), "leisure": round(a * share_of(sh, c)),
                         "kind": pts[m]["kind"]})
        other = max(0.0, t["v"] - named_arr)
        rows.append({"month": m, "country": "OTHER", "arrivals": round(other), "leisure": round(other * share_of(sh, "OTHER")),
                     "kind": t["kind"]})
        rows.append({"month": m, "country": "TOTAL", "arrivals": round(t["v"]),
                     "leisure": round(named_leis + other * share_of(sh, "OTHER")), "kind": t["kind"]})
    return pd.DataFrame(rows)


def forecast(sh: pd.DataFrame, cur: dict | None = None, other_pts: dict | None = None) -> list[dict]:
    """Next months' leisure forecast per country = arrivals forecast x leisure share. The range only carries the
    arrivals uncertainty, not the share's (stated on the page)."""
    cur = scorecard.current() if cur is None else cur
    out = []
    for level, c in cur.items():
        if level == "TOTAL":
            continue
        s = share_of(sh, level)
        for r in c["rows"]:
            # a calibrated range can sit beside the forecast when the method is biased (Turkmenistan +12%);
            # widened so it always contains the central value
            out.append({"country": level, "target": r["target"], "h": r["h"], "leisure": round(r["forecast"] * s),
                        "lo": round(min(r["lo"], r["forecast"]) * s), "hi": round(max(r["hi"], r["forecast"]) * s),
                        "share": round(s, 3)})
    # remaining countries: their recent share of total arrivals x the TOTAL forecast. (Forecasting their remainder
    # as its own series fails: 2025 H2 totals were published rounded to 0.1 mln, so the remainder is noise.)
    if other_pts and "TOTAL" in cur:
        frac, s = other_pts["frac"], share_of(sh, "OTHER")
        for r in cur["TOTAL"]["rows"]:
            out.append({"country": "OTHER", "target": r["target"], "h": r["h"], "leisure": round(r["forecast"] * frac * s),
                        "lo": round(r["lo"] * frac * s), "hi": round(r["hi"] * frac * s), "share": round(s, 3)})
    for t in sorted({x["target"] for x in out}):
        part = [x for x in out if x["target"] == t]
        if any(x["country"] == "OTHER" for x in part):
            out.append({"country": "TOTAL", "target": t, "h": part[0]["h"], "leisure": sum(x["leisure"] for x in part),
                        "lo": sum(x["lo"] for x in part), "hi": sum(x["hi"] for x in part), "share": None})
    return out


def other_points(ytd: pd.DataFrame, yearly: pd.DataFrame, countries: list[str], n: int = 6) -> dict | None:
    """Share of total arrivals coming from countries outside `countries`, over the latest n exact months where
    all of them are known. {'frac', 'months'} or None."""
    tot = scorecard.monthly_points(ytd, yearly, "TOTAL")
    per = {c: scorecard.monthly_points(ytd, yearly, c) for c in countries}
    good = [m for m in sorted(tot) if tot[m]["kind"] == "month" and tot[m]["exact"] and all(m in p for p in per.values())]
    good = good[-n:]
    if not good:
        return None
    t = sum(tot[m]["v"] for m in good)
    named = sum(per[c][m]["v"] for c in countries for m in good)
    return {"frac": max(0.0, (t - named) / t), "months": good}


def build() -> dict:
    ytd, yearly = statuz.load(), statuz.load_yearly()
    sh = shares(ytd, yearly)
    mon = monthly(sh, ytd, yearly)
    if not mon.empty:
        mon.to_csv(OUT, index=False)
    py = pd.read_csv(YEARLY)
    cur = scorecard.current(ytd, yearly)
    # Korea: monthly data has gaps and its forecast is unreliable (3 test cases) -> counted inside "other"
    cur = {k: v for k, v in cur.items() if k != "Republic of Korea"}
    fc_countries = [c for c in cur if c != "TOTAL"]
    return {"shares": sh, "validation": validate(sh, yearly), "monthly": mon,
            "forecast": forecast(sh, cur, other_points(ytd, yearly, fc_countries)), "yearly": py}


def run():
    b = build()
    from .util import log
    log.info("leisure: %d monthly rows, validation %s", len(b["monthly"]),
             [(v["year"], v["error_pct"]) for v in b["validation"]])
    return b


if __name__ == "__main__":
    b = build()
    pd.set_option("display.width", 200)
    print(b["shares"].round(3).to_string(index=False))
    print(pd.DataFrame(b["validation"]).to_string(index=False))
    m = b["monthly"]
    print(m[m.country == "TOTAL"].tail(12).to_string(index=False))
    print(pd.DataFrame(b["forecast"]).to_string(index=False))
