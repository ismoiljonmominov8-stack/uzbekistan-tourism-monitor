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
        if 12 not in pts and year in yearly and pts and max(pts) >= 9:
            pts[12] = (yearly[year], False)  # SIAT yearly total closes the year (Oct-Dec spread evenly if Nov is missing)
        prev_m, prev_v, prev_x = 0, 0, True
        for m in sorted(pts):
            v, x = pts[m]
            span = m - prev_m
            if v < prev_v:  # revision / definition change: skip rather than invent a negative month
                prev_m, prev_v, prev_x = m, v, x
                continue
            each = (v - prev_v) / span
            for k in range(prev_m + 1, m + 1):
                # a gap of more than 3 months is an average, not monthly data ("long": drawn grey, not used)
                out[f"{year}-{k:02d}"] = {"v": round(each), "exact": x and prev_x and span == 1,
                                          "kind": "month" if span == 1 else "span" if span <= 3 else "long"}
            prev_m, prev_v, prev_x = m, v, x
    return out


def build(ytd: pd.DataFrame | None = None, yearly_df: pd.DataFrame | None = None, cutoff: str | None = None) -> dict:
    """cutoff='YYYY-MM' pretends the data ends at that month (used to test the method on past years)."""
    ytd = statuz.load() if ytd is None else ytd
    yearly_df = statuz.load_yearly() if yearly_df is None else yearly_df
    yearly = {}
    if yearly_df is not None and not yearly_df.empty:
        tt = yearly_df[yearly_df["country"] == "TOTAL"]
        yearly = {int(r.year): int(r.arrivals) for r in tt.itertuples()}
    if cutoff:
        cy, cm = int(cutoff[:4]), int(cutoff[5:])
        ytd = ytd[(ytd["year"] < cy) | ((ytd["year"] == cy) & (ytd["month"] <= cm))]
        yearly = {y: v for y, v in yearly.items() if y < cy}
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

    # growth this year vs last year. Central = the latest 3 calendar months (evenly spread gap months
    # are allowed here: summed over 3 months they are close to the truth). Range = single-month growth
    # rates of the latest 6 months, true single months only (spread months give fake single rates);
    # with fewer than 2 of those, spread months are used too.
    pairs = []
    for m in range(1, lm + 1):
        a, b = by_m.get(f"{ly}-{m:02d}"), by_m.get(f"{ly-1}-{m:02d}")
        if a and b and a["kind"] in ("month", "span") and b["kind"] in ("month", "span") and b["v"] > 0:
            pairs.append((m, a["v"], b["v"], a["kind"] == "month" and b["kind"] == "month"))
    last3 = [r for r in pairs if r[0] > lm - 3]
    if len(last3) < 3:
        return result
    central = sum(r[1] for r in last3) / sum(r[2] for r in last3)
    six = [r[1] / r[2] for r in pairs if r[0] > lm - 6 and r[3]]
    if len(six) < 2:
        six = [r[1] / r[2] for r in pairs if r[0] > lm - 6]
    ratios = [(m, a, b) for m, a, b, true in pairs if true]
    lo_r, hi_r = min(six + [central]), max(six + [central])

    ytd_now = sum(p["v"] for p in points if p["m"].startswith(f"{ly}-") and int(p["m"][5:]) <= lm)
    f_sum = f_lo = f_hi = 0
    for m in range(lm + 1, 13):
        base = by_m.get(f"{ly-1}-{m:02d}")
        if not base or base["kind"] not in ("month", "span"):
            return result | {"forecast": []}
        pad = 0 if base["exact"] else ROUNDED_PAD
        v, lo, hi = base["v"] * central, base["v"] * (1 - pad) * lo_r, base["v"] * (1 + pad) * hi_r
        result["forecast"].append({"m": f"{ly}-{m:02d}", "v": round(v), "lo": round(lo), "hi": round(hi)})
        f_sum, f_lo, f_hi = f_sum + v, f_lo + lo, f_hi + hi
    result["years"][ly] = {"v": round(ytd_now + f_sum), "lo": round(ytd_now + f_lo), "hi": round(ytd_now + f_hi),
                           "ytd": ytd_now, "kind": "forecast", "through": lm}
    result["method"] = {"year": ly, "through": lm, "central": round(central, 3), "lo": round(lo_r, 3),
                        "hi": round(hi_r, 3), "months": [r[0] for r in last3],
                        "ratios": {f"{ly}-{m:02d}": round(a / b, 3) for m, a, b in ratios}}
    return result


def backtest(ytd: pd.DataFrame | None = None, yearly_df: pd.DataFrame | None = None, through: int = 9) -> list[dict]:
    """Run the forecast as if it were the end of month `through` of each past year, compare with the
    official yearly total (SIAT). Years without enough monthly data are skipped."""
    ytd = statuz.load() if ytd is None else ytd
    yearly_df = statuz.load_yearly() if yearly_df is None else yearly_df
    tt = yearly_df[yearly_df["country"] == "TOTAL"]
    yearly = {int(r.year): int(r.arrivals) for r in tt.itertuples()}
    out = []
    for y in sorted(set(ytd["year"].astype(int))):
        if y not in yearly:
            continue
        if not ((ytd["year"] == y) & (ytd["month"] == through) & (ytd["country"] == "TOTAL")).any():
            continue
        r = build(ytd, yearly_df, cutoff=f"{y}-{through:02d}")
        f = r["years"].get(y)
        if not f or f.get("kind") != "forecast":
            continue
        actual = yearly[y]
        out.append({"year": y, "through": through, "forecast": f["v"], "lo": f["lo"], "hi": f["hi"], "actual": actual,
                    "error_pct": round((f["v"] - actual) / actual * 100, 1),
                    "rest_error_pct": round((f["v"] - actual) / max(1, actual - f["ytd"]) * 100, 1),
                    "inside": f["lo"] <= actual <= f["hi"]})
    return out


def days_in(ym: str) -> int:
    return calendar.monthrange(int(ym[:4]), int(ym[5:]))[1]


if __name__ == "__main__":
    import json
    r = build()
    print(json.dumps({k: r[k] for k in ("forecast", "years", "method")}, indent=1))
    print("backtest:", json.dumps(backtest(), indent=1))
    print(len(r["points"]), "points", r["points"][0], r["points"][-1])
