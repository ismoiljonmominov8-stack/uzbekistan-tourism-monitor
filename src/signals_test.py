"""Do moving holidays and exchange rates improve the arrivals forecast? An honest, out-of-sample test.

Baseline = the current method (scorecard.project): same month last year x damped recent growth.
Candidate signals, all known on the day a forecast is made:
  eid   — days of Eid al-Fitr / Eid al-Adha holidays (+2 days around each) and Ramadan in the target month,
          minus the same in the month a year earlier (the baseline copies last year's month, so only the
          SHIFT of these moving holidays is new information). Neighbours, Russia, Turkey and the total.
  cny   — the same for Chinese New Year (7-day holiday) and China.
  fx    — change of the market's currency against the som over the 3 months before the forecast
          (log ratio; positive = their money buys more in Uzbekistan).
Test (rolling, no look-ahead): for every back-test forecast made at month c, the effect size (beta) is
estimated only from forecasts whose target month was already known at c, by least squares of
log(actual / forecast) on the signal, pooled over markets. Adjusted forecast = forecast x exp(beta x signal).
A signal is worth keeping only if it lowers the mean absolute error on the same forecasts.
Output: reports/signals_test.txt and data/signals_test.csv
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config, scorecard, statuz

FX = config.DATA / "fx_monthly.csv"
OUT_CSV = config.DATA / "signals_test.csv"
OUT_TXT = config.ROOT / "reports" / "signals_test.txt"
MIN_PRIOR = 12          # forecasts needed before beta is estimated
EID_LEVELS = {"TOTAL", "Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan", "Russia", "Türkiye"}
CCY = {"Kazakhstan": "KZT", "Kyrgyzstan": "KGS", "Tajikistan": "TJS", "Russia": "RUB", "China": "CNY",
       "Türkiye": "TRY", "India": "INR", "Republic of Korea": "KRW"}


def _days_in_month(days: set[date], ym: str) -> int:
    y, m = int(ym[:4]), int(ym[5:])
    return sum(1 for d in days if d.year == y and d.month == m)


def holiday_days(years=range(2020, 2029)) -> dict[str, set[date]]:
    """Moving holidays: Eid al-Fitr and Eid al-Adha (+-days around them), Ramadan, Chinese New Year week."""
    import holidays
    eid, ram, cny = set(), set(), set()
    for y in years:
        uz = holidays.country_holidays("UZ", years=y)
        main = {d: n for d, n in uz.items() if "hayit" in n.lower() and "chirilgan" not in n.lower()}  # skip moved days off
        for d, n in main.items():
            eid.update(d + timedelta(days=k) for k in (-1, 0, 1, 2))
            if n.lower().startswith(("ramazon", "ro'za", "roʻza")):
                ram.update(d - timedelta(days=k) for k in range(1, 30))
        for d, n in holidays.country_holidays("CN", years=y, language="en_US").items():
            if "Spring Festival" in n:
                cny.update(d + timedelta(days=k) for k in range(-1, 6))
    return {"eid": eid, "ram": ram, "cny": cny}


def signal_values(level: str, target: str, cutoff: str, H: dict, fx: pd.DataFrame | None) -> dict:
    prev = scorecard.ym_add(target, -12)
    out = {}
    if level in EID_LEVELS:
        out["eid"] = (_days_in_month(H["eid"], target) - _days_in_month(H["eid"], prev)) \
            - 0.25 * (_days_in_month(H["ram"], target) - _days_in_month(H["ram"], prev))
    if level == "China":
        out["cny"] = _days_in_month(H["cny"], target) - _days_in_month(H["cny"], prev)
    if fx is not None and level in CCY:
        s = fx[fx["ccy"] == CCY[level]].set_index("month")["som_per_unit"]
        a, b = s.get(cutoff), s.get(scorecard.ym_add(cutoff, -3))
        if a and b:
            out["fx"] = float(np.log(a / b))
    return out


def backtest_rows() -> pd.DataFrame:
    ytd, yearly = statuz.load(), statuz.load_yearly()
    actual = {lvl: scorecard.monthly_points(ytd, yearly, lvl) for lvl in ["TOTAL"] + scorecard.COUNTRIES}
    last_all = max(actual["TOTAL"])
    H = holiday_days()
    fx = pd.read_csv(FX) if FX.exists() else None
    rows = []
    for cutoff in pd.period_range("2023-01", scorecard.ym_add(last_all, -1), freq="M"):
        c = f"{cutoff.year}-{cutoff.month:02d}"
        y_c, yl_c = scorecard._truncate(ytd, yearly, c)
        for level in ["TOTAL"] + scorecard.COUNTRIES:
            pts = scorecard.monthly_points(y_c, yl_c, level)
            if c not in pts or pts[c]["kind"] not in ("month", "span"):
                continue
            for r in scorecard.project(pts, c):
                a = actual[level].get(r["target"])
                if not a or a["kind"] != "month":
                    continue
                rows.append({"cutoff": c, "level": level, "target": r["target"], "h": r["h"], "forecast": r["forecast"],
                             "actual": round(a["v"])} | signal_values(level, r["target"], c, H, fx))
    return pd.DataFrame(rows)


def rolling_adjust(df: pd.DataFrame, sig: str) -> pd.Series:
    """Adjusted forecasts for one signal, beta estimated only from forecasts whose target month was known."""
    d = df.copy()
    d["y"] = np.log(d["actual"] / d["forecast"])
    adj = pd.Series(np.nan, index=d.index)
    betas = pd.Series(np.nan, index=d.index)
    for i, r in d.iterrows():
        if pd.isna(r.get(sig)):
            continue
        prior = d[(d["target"] <= r["cutoff"]) & d[sig].notna()]
        if len(prior) < MIN_PRIOR or prior[sig].abs().sum() == 0:
            continue
        x, y = prior[sig].values, prior["y"].values - prior["y"].mean()   # remove the method's average bias
        beta = float((x * y).sum() / (x * x).sum()) if (x * x).sum() > 0 else 0.0
        adj[i] = r["forecast"] * np.exp(beta * r[sig])
        betas[i] = beta
    return adj, betas


def run() -> str:
    df = backtest_rows()
    lines = ["Signals test — do holidays and exchange rates improve the arrivals forecast?",
             f"Back-test forecasts: {len(df)} (2023–{df['target'].max()}, 1–3 months ahead, total + {df['level'].nunique() - 1} countries)",
             f"Exchange rates available: {'yes' if FX.exists() else 'NO (run the fetch first)'}", ""]
    res = []
    for sig in ("eid", "cny", "fx"):
        if sig not in df.columns:
            lines.append(f"{sig}: no data"); continue
        adj, betas = rolling_adjust(df, sig)
        m = adj.notna()
        if m.sum() == 0:
            lines.append(f"{sig}: not enough cases yet"); continue
        base = (df.loc[m, "forecast"] / df.loc[m, "actual"] - 1).abs()
        new = (adj[m] / df.loc[m, "actual"] - 1).abs()
        moved = (df.loc[m, sig] != 0)
        lines.append(f"[{sig}] tested on {int(m.sum())} forecasts ({int(moved.sum())} where the signal was not zero); last beta {betas[m].iloc[-1]:+.4f}")
        lines.append(f"   mean abs error: baseline {base.mean():.2%} -> with signal {new.mean():.2%}  (change {new.mean() - base.mean():+.2%})")
        if moved.sum():
            lines.append(f"   only months where the signal moved: {base[moved].mean():.2%} -> {new[moved].mean():.2%}  (n={int(moved.sum())})")
        by = pd.DataFrame({"level": df.loc[m, "level"], "base": base, "new": new}).groupby("level").mean()
        for lvl, r in by.iterrows():
            lines.append(f"     {lvl:18s} {r.base:7.2%} -> {r.new:7.2%}")
        better = new.mean() < base.mean() - 0.002
        lines.append("   VERDICT: " + ("keep — it lowers the error" if better else "drop — no real improvement") + "\n")
        res.append({"signal": sig, "n": int(m.sum()), "n_moved": int(moved.sum()), "mae_base": round(base.mean(), 4),
                    "mae_new": round(new.mean(), 4), "keep": bool(better)})
    pd.DataFrame(res).to_csv(OUT_CSV, index=False)
    OUT_TXT.parent.mkdir(exist_ok=True)
    text = "\n".join(lines)
    OUT_TXT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(run())
