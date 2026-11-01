"""Forecast scorecard: how wrong are our month-ahead forecasts, measured, not assumed.

Method (same as the page's forecast, generalised to any month and to single countries):
  forecast(target month) = same month last year x growth of the latest 3 months vs a year earlier;
  range = lowest/highest single-month growth of the latest 6 months (true single months), base widened
  by 5% if it was rounded in the source.

Growth is damped (only DAMP = 75% of recent growth assumed to continue, see forecast.py). Ranges are
calibrated: once a level/horizon has 8+ scored back-test forecasts, the range is the 10th-90th percentile
of its past errors (target: the actual falls inside ~80% of the time); otherwise the method range is used.

Two kinds of scored forecasts, kept apart:
  backtest — rolling back-test: for every past month c with enough data, pretend the data ends at c and
             forecast c+1 .. c+3. Gives dozens of measured forecasts now. (December totals of finished
             years come from SIAT yearly data, published a few months later: a small look-ahead.)
  live     — forecasts saved on the day they were made (data/forecast_log.csv), scored when stat.uz
             publishes the month. Only these are a true out-of-sample record; they accumulate from Nov 2026.

A forecast is scored only when the target month's actual value is a true single month (not an evenly
spread gap). Error = forecast / actual - 1.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import config, statuz
from .forecast import DAMP

LOG = config.DATA / "forecast_log.csv"
SCORES = config.DATA / "forecast_scores.csv"
HORIZON = 3
CALIB = config.DATA / "forecast_calibration.csv"
CALIB_MIN = 8          # scored back-test forecasts needed before the range comes from past errors
COVER = (0.10, 0.90)   # the calibrated range should hold the actual value about 80% of the time
ROUNDED_PAD = 0.05
COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Russia", "China", "Türkiye", "India",
             "Turkmenistan", "Republic of Korea"]
NAME_UZ = {"TOTAL": "Jami", "Kazakhstan": "Qozog'iston", "Kyrgyzstan": "Qirg'iziston", "Tajikistan": "Tojikiston",
           "Russia": "Rossiya", "China": "Xitoy", "Türkiye": "Turkiya", "India": "Hindiston",
           "Turkmenistan": "Turkmaniston", "Republic of Korea": "Janubiy Koreya"}


def ym_add(ym: str, k: int) -> str:
    p = pd.Period(ym, "M") + k
    return f"{p.year}-{p.month:02d}"


def monthly_points(ytd: pd.DataFrame, yearly: pd.DataFrame, level: str) -> dict[str, dict]:
    """{'YYYY-MM': {v, exact, kind}} for TOTAL or one country, from year-to-date figures; December of a
    finished year is closed with the SIAT yearly value when the year-to-date series reaches September."""
    t = ytd[ytd["country"] == level].copy()
    if t.empty:
        return {}
    t["exact"] = t["exact"].astype(str).str.lower().eq("true")
    yv = yearly[yearly["country"] == level]
    ytot = {int(r.year): int(r.arrivals) for r in yv.itertuples()}
    out = {}
    for year, g in t.groupby("year"):
        year = int(year)
        pts = {int(r.month): (int(r.ytd), bool(r.exact)) for r in g.itertuples()}
        if 12 not in pts and year in ytot and max(pts) >= 9:
            pts[12] = (ytot[year], False)
        pm, pv, px = 0, 0, True
        for m in sorted(pts):
            v, x = pts[m]
            span = m - pm
            if v < pv:
                pm, pv, px = m, v, x
                continue
            each = (v - pv) / span
            for k in range(pm + 1, m + 1):
                out[f"{year}-{k:02d}"] = {"v": each, "exact": x and px and span == 1,
                                          "kind": "month" if span == 1 else "span" if span <= 3 else "long"}
            pm, pv, px = m, v, x
    return out


def project(pts: dict[str, dict], last: str, horizon: int = HORIZON) -> list[dict]:
    """Forecasts for last+1 .. last+horizon (may cross the year end). [] if inputs are missing."""
    usable = ("month", "span")
    pairs = []
    for k in range(0, 6):
        m = ym_add(last, -k)
        a, b = pts.get(m), pts.get(ym_add(m, -12))
        if a and b and a["kind"] in usable and b["kind"] in usable and b["v"] > 0:
            pairs.append((k, a["v"], b["v"], a["kind"] == "month" and b["kind"] == "month"))
    last3 = [p for p in pairs if p[0] < 3]
    if len(last3) < 3:
        return []
    raw = sum(p[1] for p in last3) / sum(p[2] for p in last3)
    central = 1 + (raw - 1) * DAMP
    damp = lambda r: 1 + (r - 1) * DAMP  # noqa: E731
    six = [damp(p[1] / p[2]) for p in pairs if p[3]] or [damp(p[1] / p[2]) for p in pairs]
    lo_r, hi_r = min(six + [central]), max(six + [central])
    out = []
    for h in range(1, horizon + 1):
        target = ym_add(last, h)
        base = pts.get(ym_add(target, -12))
        if not base or base["kind"] not in usable:
            continue
        pad = 0 if base["exact"] else ROUNDED_PAD
        out.append({"target": target, "h": h, "forecast": round(base["v"] * central),
                    "lo": round(base["v"] * (1 - pad) * lo_r), "hi": round(base["v"] * (1 + pad) * hi_r),
                    "growth": round(central, 3)})
    return out


def _truncate(ytd: pd.DataFrame, yearly: pd.DataFrame, cutoff: str):
    cy, cm = int(cutoff[:4]), int(cutoff[5:])
    y = ytd[(ytd["year"] < cy) | ((ytd["year"] == cy) & (ytd["month"] <= cm))]
    return y, yearly[yearly["year"] < cy]


def calibration() -> dict[tuple[str, int], tuple[float, float]]:
    if not CALIB.exists():
        return {}
    c = pd.read_csv(CALIB)
    return {(r.level, int(r.h)): (float(r.q_lo), float(r.q_hi)) for r in c.itertuples()}


def apply_calibration(rows: list[dict], level: str, cal: dict) -> list[dict]:
    """Replace the range with one built from the method's own past errors at that horizon:
    actual = forecast / (1 + error), so the 10th-90th percentile of past errors gives the range."""
    for r in rows:
        q = cal.get((level, r["h"]))
        if q:
            r["lo"], r["hi"], r["range"] = round(r["forecast"] / (1 + q[1])), round(r["forecast"] / (1 + q[0])), "calibrated"
        else:
            r["range"] = "method"
    return rows


def current(ytd=None, yearly=None) -> dict[str, dict]:
    """Latest forecasts per level: {level: {last, rows}} (levels without enough data are left out)."""
    ytd = statuz.load() if ytd is None else ytd
    yearly = statuz.load_yearly() if yearly is None else yearly
    out = {}
    for level in ["TOTAL"] + COUNTRIES:
        pts = monthly_points(ytd, yearly, level)
        months = sorted(k for k, v in pts.items() if v["kind"] == "month")
        if not months:
            continue
        last = max(pts)
        rows = apply_calibration(project(pts, last), level, calibration())
        out[level] = {"last": last, "rows": rows, "last_value": round(pts[last]["v"])}
    return out


def log_live(ytd=None, yearly=None) -> int:
    """Save today's forecasts once per (data month, level, target). Returns rows added."""
    cur = current(ytd, yearly)
    old = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=["made_on", "data_through", "level", "target", "h",
                                                                         "forecast", "lo", "hi", "growth"])
    have = set(zip(old["data_through"].astype(str), old["level"].astype(str), old["target"].astype(str)))
    new = []
    for level, c in cur.items():
        for r in c["rows"]:
            if (c["last"], level, r["target"]) not in have:
                new.append({"made_on": date.today().isoformat(), "data_through": c["last"], "level": level} | r)
    if new:
        pd.concat([old, pd.DataFrame(new)], ignore_index=True).to_csv(LOG, index=False)
    return len(new)


def score(ytd=None, yearly=None, start: str = "2023-01") -> pd.DataFrame:
    """Rolling back-test + live log, each scored against the actual single-month value."""
    ytd = statuz.load() if ytd is None else ytd
    yearly = statuz.load_yearly() if yearly is None else yearly
    actual = {lvl: monthly_points(ytd, yearly, lvl) for lvl in ["TOTAL"] + COUNTRIES}
    rows = []
    last_all = max(actual["TOTAL"]) if actual["TOTAL"] else None
    if last_all:
        for cutoff in pd.period_range(start, ym_add(last_all, -1), freq="M"):
            c = f"{cutoff.year}-{cutoff.month:02d}"
            y_c, yl_c = _truncate(ytd, yearly, c)
            for level in ["TOTAL"] + COUNTRIES:
                pts = monthly_points(y_c, yl_c, level)
                if c not in pts or pts[c]["kind"] not in ("month", "span"):
                    continue
                for r in project(pts, c):
                    rows.append({"kind": "backtest", "made_on": None, "data_through": c, "level": level} | r)
    if LOG.exists():
        for r in pd.read_csv(LOG).to_dict("records"):
            rows.append({"kind": "live"} | r)
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    def act(r):
        a = actual.get(r["level"], {}).get(r["target"])
        return round(a["v"]) if a and a["kind"] == "month" else None
    df["actual"] = df.apply(act, axis=1)
    df["error"] = (df["forecast"] / df["actual"] - 1).round(4)
    inside = (df["actual"] >= df["lo"]) & (df["actual"] <= df["hi"])
    df["inside"] = inside.astype(object).where(df["actual"].notna(), None)
    df.to_csv(SCORES, index=False)
    # calibration from back-test errors (enough cases only)
    b = df[(df["kind"] == "backtest") & df["actual"].notna()]
    cal = (b.groupby(["level", "h"])["error"]
             .agg(n="size", q_lo=lambda e: e.quantile(COVER[0]), q_hi=lambda e: e.quantile(COVER[1]))
             .reset_index())
    cal[cal["n"] >= CALIB_MIN].round(4).to_csv(CALIB, index=False)
    return df


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per kind, level and horizon: number scored, mean absolute error, median error (bias), share inside range."""
    d = df[df["actual"].notna()].copy()
    if d.empty:
        return pd.DataFrame()
    d["abs"] = d["error"].abs()
    g = d.groupby(["kind", "level", "h"])
    return pd.DataFrame({"n": g.size(), "mae": g["abs"].mean().round(3), "bias": g["error"].median().round(3),
                         "inside": g["inside"].apply(lambda s: round(float(s.astype(bool).mean()), 2))}).reset_index()


def run() -> pd.DataFrame:
    df = score()          # first: refresh the calibration from the back-test
    added = log_live()    # then: save today's forecasts with calibrated ranges
    if added:
        df = score()
    from .util import log
    log.info("scorecard: %d live forecasts added, %d scored", added, int(df["actual"].notna().sum()) if not df.empty else 0)
    return df


if __name__ == "__main__":
    d = run()
    pd.set_option("display.width", 200)
    s = summary(d)
    print(s.to_string(index=False))
