"""Monthly arrivals for the countries that never make the monthly top-10 (Japan, USA, Italy, France, UK, Spain...).

Official inputs (all from the statistics committee):
  * yearly totals for every country (SIAT),
  * year-to-date totals from single-country releases (country_releases.csv) and, for countries that
    sometimes reach the top-10 (Germany, Korea), from the monthly lists (arrivals_ytd.csv),
  * last year's same-period values given in those releases.
Method — "seasonal curve with anchors":
  F(m) = typical share of a year's arrivals that has come by the end of month m, measured from every official
  point where the full-year total is also known (separate curves for Europe/America/East Asia and for the rest).
  Between official year-to-date points the months are split in proportion to F; after the last point the
  year total is estimated as ytd / F(m) and continued along F. With no point in the year at all, last year's
  total x the growth seen this year in similar markets is used.
Every month is labelled official (two consecutive official totals give it exactly) or estimated; ranges come
from back-tests on countries whose true monthly numbers are known (see backtest()).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, country_releases, statuz

WEST = {"Germany", "Italy", "France", "Spain", "United Kingdom", "United States", "Japan", "Republic of Korea",
        "Australia", "Canada", "Israel", "Finland", "Netherlands", "Switzerland", "Austria", "Belgium", "Poland",
        "Czech Republic", "Sweden", "Norway", "Denmark", "Portugal", "Greece", "Hungary", "Ireland", "New Zealand",
        "Singapore", "Malaysia", "Indonesia", "Thailand", "Viet Nam"}
# fully covered by the monthly top-10 every month — not estimated here
MONTHLY_TOP = {"Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan", "Afghanistan", "Russia", "China",
               "Türkiye", "India", "TOTAL"}
MIN_YEARLY = 3000          # smaller countries are left out (too noisy, too little to say)
DEFAULT_REL = {"inside": 0.31, "after1": 0.30, "after3": 0.40, "none": 0.41}   # 80 % error bands, see backtest()
BT = config.DATA / "distant_backtest.json"


def points() -> pd.DataFrame:
    """All official year-to-date points: country, year, month, ytd, exact, source."""
    cr = country_releases.load()
    rows = [(r.country, int(r.year), int(r.month), float(r.ytd), bool(r.exact), "release") for r in cr.itertuples()]
    rows += [(r.country, int(r.year) - 1, int(r.month), float(r.prev_ytd), False, "release_prev")
             for r in cr.itertuples() if pd.notna(r.prev_ytd)]
    ytd = statuz.load()
    rows += [(r.country, int(r.year), int(r.month), float(r.ytd), bool(r.exact), "top10")
             for r in ytd.itertuples() if r.country not in ("TOTAL",)]
    d = pd.DataFrame(rows, columns=["country", "year", "month", "ytd", "exact", "source"])
    # a direct release beats a derived previous-year value for the same period
    order = {"release": 0, "top10": 1, "release_prev": 2}
    d["o"] = d["source"].map(order)
    return d.sort_values("o").drop_duplicates(["country", "year", "month"]).drop(columns="o")


def yearly() -> dict[tuple[str, int], int]:
    y = statuz.load_yearly()
    return {(r.country, int(r.year)): int(r.arrivals) for r in y.itertuples() if r.country != "TOTAL"}


def curves(pts: pd.DataFrame, Y: dict, exclude: str | None = None) -> dict[str, np.ndarray]:
    """F[0..12] for 'west' and 'other' (F[0]=0, F[12]=1, non-decreasing)."""
    d = pts[(pts["month"] < 12) & (pts["country"] != exclude)].copy()
    d["Y"] = [Y.get((c, y)) for c, y in zip(d["country"], d["year"])]
    d = d[d["Y"].fillna(0) > 0]
    d["F"] = d["ytd"] / d["Y"]
    d = d[(d["F"] > 0) & (d["F"] < 1.05)]
    out = {}
    for grp, sub in (("west", d[d["country"].isin(WEST)]), ("other", d[~d["country"].isin(WEST | MONTHLY_TOP)]),
                     ("all", d)):
        med = sub.groupby("month")["F"].median()
        if len(med) < 6:
            med = d.groupby("month")["F"].median()
        F = np.interp(range(13), [0] + list(med.index) + [12], [0] + list(med.values) + [1])
        out[grp] = np.minimum(np.maximum.accumulate(F), 1)
    return out


def _curve(F: dict, country: str) -> np.ndarray:
    return F["west"] if country in WEST else F["other"] if country not in MONTHLY_TOP else F["all"]


def country_curve(pts: pd.DataFrame, Y: dict, F: dict, country: str, skip_year: int | None = None) -> np.ndarray:
    """The country's own seasonal curve (from its official points in other years), shrunk toward its group curve
    — weight = own points / 12, at most 0.8. Back-test: cuts the error of months after the last official point
    from ~36 % to ~22 % (median)."""
    grp = _curve(F, country)
    d = pts[(pts["country"] == country) & (pts["year"] != skip_year) & (pts["month"] < 12)].copy()
    d["Y"] = [Y.get((country, y)) for y in d["year"]]
    d = d[d["Y"].fillna(0) > 0]
    d["F"] = d["ytd"] / d["Y"]
    d = d[(d["F"] > 0) & (d["F"] < 1.05)]
    med = d.groupby("month")["F"].median()
    if len(med) < 2:
        return grp
    own = np.interp(range(13), [0] + list(med.index) + [12], [0] + list(med.values) + [1])
    w = min(len(d) / 12, 0.8)
    F = np.minimum(np.maximum.accumulate(w * own + (1 - w) * grp), 1)
    # medians of points from different years can leave a month almost empty (Italy: June ~1 %) —
    # no month may get less than half of its share in the group curve
    inc = np.maximum(np.diff(F), 0.5 * np.diff(grp))
    return np.concatenate([[0], np.cumsum(inc) / inc.sum()])


def estimate_year(anchors: dict[int, float], F: np.ndarray, annual_guess: float | None) -> tuple[np.ndarray, int]:
    """Cumulative arrivals C[0..12] from official ytd anchors {month: ytd}. Returns (C, last anchor month)."""
    C = np.zeros(13)
    if not anchors:
        return (annual_guess or 0) * F, 0
    pts = [(0, 0.0)] + sorted(anchors.items())
    for (ma, ca), (mb, cb) in zip(pts, pts[1:]):
        for m in range(ma + 1, mb + 1):
            span = F[mb] - F[ma]
            C[m] = ca + (cb - ca) * ((F[m] - F[ma]) / span if span > 0 else (m - ma) / (mb - ma))
    last, cl = pts[-1]
    total = cl / F[last] if F[last] > 0.02 else (annual_guess or cl / max(F[last], 0.02))
    for m in range(last + 1, 13):
        C[m] = cl + total * (F[m] - F[last])
    return C, last


def growth_now(pts: pd.DataFrame, year: int) -> float:
    """Median year-on-year growth of the western markets with an official point this year."""
    cr = country_releases.load()
    cr = cr[(cr["year"] == year) & cr["prev_ytd"].notna() & cr["country"].isin(WEST) & (cr["month"] >= 2)]
    g = (cr.sort_values("month").groupby("country").last().eval("ytd / prev_ytd"))
    return float(g.median()) if len(g) else 1.0


def _bands() -> dict:
    import json
    try:
        bt = json.loads(BT.read_text())
        return {k: min(max(v["q80"], 0.10), 0.8) for k, v in bt.items() if v.get("q80")} | {}
    except Exception:  # noqa: BLE001
        return DEFAULT_REL


def _rel(kind: str, h: int = 0) -> float:
    r = DEFAULT_REL | _bands()
    if kind == "inside":
        return r["inside"]
    if kind == "none":
        return r["none"]
    return r["after1"] if h <= 1 else r["after1"] + (r["after3"] - r["after1"]) * min(h - 1, 2) / 2


def build(year: int | None = None, horizon: int = 3) -> dict:
    """{country: {"YYYY-MM": {v, lo, hi, kind}}, ...} for the current year (+ next months) and last year,
    plus the official releases per country. kind: official | estimate | forecast."""
    pts, Y = points(), yearly()
    year = year or int(pts["year"].max())
    F = curves(pts, Y)
    g = growth_now(pts, year)
    last_month_total = statuz.monthly()
    last_m = int(last_month_total.loc[last_month_total["year"] == year, "month"].max())
    with_release = set(country_releases.load()["country"])
    # estimate only where something official shapes the months: a single-country release, or the
    # Europe/America/East Asia group curve (measured on its members); others would be a flat split of the year
    big = {c for (c, y), v in Y.items() if y == year - 1 and v >= MIN_YEARLY
           and (c in with_release or c in WEST)} - MONTHLY_TOP
    out, releases = {}, {}
    cr = country_releases.load()
    for c in sorted(big):
        Fc = country_curve(pts, Y, F, c)
        series = {}
        for yy in (year - 1, year):
            a = pts[(pts["country"] == c) & (pts["year"] == yy)]
            anchors = {int(r.month): r.ytd for r in a.itertuples()}
            exact_m = {int(r.month) for r in a.itertuples()}
            if yy < year and (c, yy) in Y:
                anchors[12] = Y[(c, yy)]                      # last year's total is official
                exact_m.add(12)
            guess = Y.get((c, yy - 1), 0) * (g if yy == year else 1.0) if (c, yy - 1) in Y else None
            if yy == year and not anchors and not guess:
                continue
            C, last = estimate_year(anchors, Fc, guess)
            end = 12 if yy < year else min(12, last_m + horizon)
            for m in range(1, end + 1):
                v = C[m] - C[m - 1]
                ym = f"{yy}-{m:02d}"
                official = m in exact_m and (m == 1 or (m - 1) in exact_m)
                if official:
                    kind, rel = "official", 0.0
                elif yy == year and m > last_m:
                    kind, rel = "forecast", _rel("after", m - max(last, 0)) if last else _rel("none")
                elif m <= max(anchors) if anchors else False:
                    kind, rel = "estimate", _rel("inside")
                else:
                    kind, rel = "estimate", _rel("after", m - last) if last else _rel("none")
                series[ym] = {"v": int(round(max(v, 0))), "lo": int(round(max(v, 0) * (1 - rel))),
                              "hi": int(round(max(v, 0) * (1 + rel))), "kind": kind}
        # forecast months that fall in the next year: same month this year x this country's growth
        a_now = cr[(cr["country"] == c) & (cr["year"] == year) & cr["prev_ytd"].notna()].sort_values("month")
        gc = float(a_now.iloc[-1]["ytd"] / a_now.iloc[-1]["prev_ytd"]) if len(a_now) else g
        for k in range(1, max(0, last_m + horizon - 12) + 1):
            base = series.get(f"{year}-{k:02d}")
            if base:
                v = base["v"] * gc
                rel = _rel("after", 3)
                series[f"{year + 1}-{k:02d}"] = {"v": int(round(v)), "lo": int(round(v * (1 - rel))),
                                                 "hi": int(round(v * (1 + rel))), "kind": "forecast"}
        out[c] = series
        rel_rows = cr[cr["country"] == c].sort_values(["year", "month"])
        releases[c] = [{"y": int(r.year), "m": int(r.month), "ytd": int(r.ytd),
                        "prev": None if pd.isna(r.prev_ytd) else int(r.prev_ytd),
                        "leisure": None if pd.isna(r.leisure) else int(r.leisure), "url": r.url}
                       for r in rel_rows.itertuples()]
    return {"series": out, "releases": releases, "growth": round(g, 3), "year": year, "through": last_m}


def backtest() -> dict:
    """Error of monthly estimates on country-years whose true monthly numbers are known (the monthly lists).
    Simulates the usual situation: only ONE official ytd point in the year (at month k) plus last year's total."""
    pts, Y = points(), yearly()
    top = statuz.load()
    errs = {"inside": [], "after1": [], "after3": [], "none": []}
    for (c, yy), g in top[top["country"] != "TOTAL"].groupby(["country", "year"]):
        months = sorted(g["month"].astype(int))
        if months != list(range(1, months[-1] + 1)) or len(months) < 6 or (c, yy - 1) not in Y:
            continue
        truth_c = dict(zip(g["month"].astype(int), g["ytd"].astype(float)))
        truth = {m: truth_c[m] - truth_c.get(m - 1, 0) for m in months}
        Fc = country_curve(pts, Y, curves(pts, Y, exclude=c), c, skip_year=yy)
        prev = Y[(c, yy - 1)]
        for k in (3, 5, 7):
            if k >= months[-1]:
                continue
            C, _ = estimate_year({k: truth_c[k]}, Fc, None)
            for m in months:
                est = C[m] - C[m - 1]
                e = est / truth[m] - 1 if truth[m] else None
                if e is None:
                    continue
                key = "inside" if m <= k else "after1" if m - k <= 1 else "after3"
                errs[key].append(e)
        C, _ = estimate_year({}, Fc, prev)
        errs["none"] += [(C[m] - C[m - 1]) / truth[m] - 1 for m in months if truth[m]]
    return {k: {"n": len(v), "mae": float(np.median(np.abs(v))) if v else None,
                "q80": float(np.quantile(np.abs(v), 0.8)) if v else None} for k, v in errs.items()}


if __name__ == "__main__":
    import json
    res = backtest()
    BT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
