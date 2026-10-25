"""Overall foreign arrivals since 2018, month by month, with a simple forecast for the rest of the year.

Data reality (why the series looks the way it does):
- Official MONTHLY figures exist only as stat.uz year-to-date press releases (collected from 2025).
  Before that only YEARLY totals (SIAT dataset 1031, sum of all countries) are available, so those
  years are shown as yearly total / 12 and flagged kind="year". No official daily or weekly figures
  exist at all; day/week views on the page are averages (month / days, x7).
- When a month's release is missing, the gap between two known year-to-date figures is spread
  evenly over the months it covers (kind="span"). December of a finished year is taken from the
  SIAT yearly total minus November's year-to-date figure.

Forecast (remaining months of the latest year), deliberately simple and explainable:
  value = same month last year x growth ratio of the latest 3 months (this year / last year).
  Low/high = the lowest/highest single-month growth ratio of the latest 6 months (true single
  months only, not evenly spread gaps), applied to the
  base, which is widened by 5% when last year's figure was rounded in the source.
This is a seasonal-naive projection, not a model of causes; it assumes the recent growth rate holds.
"""
from __future__ import annotations

import calendar

import pandas as pd

from . import statuz

FIRST_YEAR = 2018
ROUNDED_PAD = 0.05


def _monthly_total(ytd: pd.DataFrame, yearly: dict[int, int]) -> dict[str, dict]:
    """{'YYYY-MM': {v, exact, kind}} from year-to-date TOTAL rows (+ yearly total for December)."""
    out = {}
    t = ytd[ytd["country"] == "TOTAL"].copy()
    t["exact"] = t["exact"].astype(str).str.lower().eq("true")
    for year, g in t.groupby("year"):
        year = int(year)
        pts = {int(r.month): (int(r.ytd), bool(r.exact)) for r in g.itertuples()}
        if 12 not in pts and year in yearly and pts and max(pts) == 11:
            pts[12] = (yearly[year], False)  # SIAT yearly total closes the year
        prev_m, prev_v, prev_x = 0, 0, True
        for m in sorted(pts):
            v, x = pts[m]
            span = m - prev_m
            if v < prev_v:  # revision / definition change: skip rather than invent a negative month
                prev_m, prev_v, prev_x = m, v, x
                continue
            each = (v - prev_v) / span
            for k in range(prev_m + 1, m + 1):
                out[f"{year}-{k:02d}"] = {"v": round(each), "exact": x and prev_x and span == 1,
                                          "kind": "month" if span == 1 else "span"}
            prev_m, prev_v, prev_x = m, v, x
    return out


def build(ytd: pd.DataFrame | None = None, yearly_df: pd.DataFrame | None = None) -> dict:
    ytd = statuz.load() if ytd is None else ytd
    yearly_df = statuz.load_yearly() if yearly_df is None else yearly_df
    yearly = {}
    if yearly_df is not None and not yearly_df.empty:
        tt = yearly_df[yearly_df["country"] == "TOTAL"]
        yearly = {int(r.year): int(r.arrivals) for r in tt.itertuples()}
    monthly = _monthly_total(ytd, yearly) if ytd is not None and not ytd.empty else {}

    years_with_months = {int(k[:4]) for k in monthly}
    points = []
    for y in sorted(yearly):
        if y < FIRST_YEAR or y in years_with_months:
            continue
        for m in range(1, 13):
            points.append({"m": f"{y}-{m:02d}", "v": round(yearly[y] / 12), "exact": False, "kind": "year"})
    points += [{"m": k} | v for k, v in sorted(monthly.items())]
    points.sort(key=lambda p: p["m"])
    by_m = {p["m"]: p for p in points}

    result = {"points": points, "forecast": [], "years": {}, "method": None}
    for y, v in sorted(yearly.items()):  # official yearly totals (SIAT)
        if y >= FIRST_YEAR:
            result["years"][y] = {"v": v, "kind": "actual"}

    if not monthly:
        return result
    last = max(monthly)
    ly, lm = int(last[:4]), int(last[5:])
    if lm == 12:
        return result

    # growth ratios this year vs last year, month by month (only months known in both years)
    ratios = []
    for m in range(1, lm + 1):
        a, b = by_m.get(f"{ly}-{m:02d}"), by_m.get(f"{ly-1}-{m:02d}")
        # evenly spread gap months would give fake single-month growth rates: skip them
        if a and b and a["kind"] == "month" and b["kind"] == "month" and b["v"] > 0:
            ratios.append((m, a["v"], b["v"]))
    if len(ratios) < 3:
        return result
    last3 = ratios[-3:]
    central = sum(r[1] for r in last3) / sum(r[2] for r in last3)
    six = [r[1] / r[2] for r in ratios if r[0] > lm - 6]  # calendar window, not "last 6 found"
    lo_r, hi_r = min(six + [central]), max(six + [central])

    ytd_now = sum(p["v"] for p in points if p["m"].startswith(f"{ly}-") and int(p["m"][5:]) <= lm)
    f_sum = f_lo = f_hi = 0
    for m in range(lm + 1, 13):
        base = by_m.get(f"{ly-1}-{m:02d}")
        if not base or base["kind"] == "year":
            return result | {"forecast": []}
        pad = 0 if base["exact"] else ROUNDED_PAD
        v, lo, hi = base["v"] * central, base["v"] * (1 - pad) * lo_r, base["v"] * (1 + pad) * hi_r
        result["forecast"].append({"m": f"{ly}-{m:02d}", "v": round(v), "lo": round(lo), "hi": round(hi)})
        f_sum, f_lo, f_hi = f_sum + v, f_lo + lo, f_hi + hi
    result["years"][ly] = {"v": round(ytd_now + f_sum), "lo": round(ytd_now + f_lo), "hi": round(ytd_now + f_hi),
                           "ytd": ytd_now, "kind": "forecast", "through": lm}
    result["method"] = {"year": ly, "through": lm, "central": round(central, 3), "lo": round(lo_r, 3),
                        "hi": round(hi_r, 3), "months": [m for m, _, _ in last3],
                        "ratios": {f"{ly}-{m:02d}": round(a / b, 3) for m, a, b in ratios}}
    return result


def days_in(ym: str) -> int:
    return calendar.monthrange(int(ym[:4]), int(ym[5:]))[1]


if __name__ == "__main__":
    import json
    r = build()
    print(json.dumps({k: r[k] for k in ("forecast", "years", "method")}, indent=1))
    print(len(r["points"]), "points", r["points"][0], r["points"][-1])
