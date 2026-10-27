"""Google Trends: how much each country searches for Uzbekistan, and what share of that is about visas.

Two measures, both relative (Google gives 0-100 indices, never counts):
  interest  — worldwide "interest by country" for the Uzbekistan TOPIC (language independent): searches
              for Uzbekistan as a share of all searches in that country, scaled so the top country = 100.
  visa share — inside one country, searches for "<Uzbekistan> visa" in the local language relative to
              searches for "<Uzbekistan>" (same request, so the two are on one scale). A high share where
              no visa is needed suggests people don't know they can travel visa-free (a proxy, not proof).
China has no Google data (Google is blocked there).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

from . import config
from .util import log

TOPIC_UZ = "/m/07t_x"          # Google Knowledge Graph id of Uzbekistan
TIMEFRAME = "today 12-m"
# geo: (name_uz, "Uzbekistan" in the main local language, "... visa", visa needed for a tourist trip?)
TERMS = {
    "US": ("AQSh", "Uzbekistan", "Uzbekistan visa", False),
    "GB": ("Buyuk Britaniya", "Uzbekistan", "Uzbekistan visa", False),
    "IN": ("Hindiston", "Uzbekistan", "Uzbekistan visa", False),     # visa-free from 1 Sep 2026
    "DE": ("Germaniya", "Usbekistan", "Usbekistan Visum", False),
    "FR": ("Fransiya", "Ouzbékistan", "Ouzbékistan visa", False),
    "IT": ("Italiya", "Uzbekistan", "Uzbekistan visto", False),
    "JP": ("Yaponiya", "ウズベキスタン", "ウズベキスタン ビザ", False),
    "KR": ("Janubiy Koreya", "우즈베키스탄", "우즈베키스탄 비자", False),
    "TR": ("Turkiya", "Özbekistan", "Özbekistan vize", False),
    "RU": ("Rossiya", "Узбекистан", "Узбекистан виза", False),
    "KZ": ("Qozog'iston", "Узбекистан", "Узбекистан виза", False),
}
OUT_INTEREST = config.DATA / "trends_interest.csv"
OUT_VISA = config.DATA / "trends_visa.csv"
PAUSE = 12   # seconds between requests: Google rate-limits fast clients


def client():
    from pytrends.request import TrendReq
    return TrendReq(hl="en-US", tz=0, timeout=(10, 30))


def _retry(fn, tries=4):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            wait = PAUSE * (2 ** i)
            log.warning("trends request failed (%s/%s): %s — waiting %ss", i + 1, tries, str(e)[:120], wait)
            time.sleep(wait)
    return None


def interest_by_country(py) -> pd.DataFrame | None:
    def go():
        py.build_payload([TOPIC_UZ], timeframe=TIMEFRAME, geo="")
        return py.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True)
    df = _retry(go)
    if df is None or df.empty:
        return None
    df = df.reset_index().rename(columns={TOPIC_UZ: "interest", "geoName": "country", "geoCode": "geo"})
    return df[df["interest"] > 0].sort_values("interest", ascending=False)


def visa_share(py, geo: str) -> dict | None:
    name, term, visa_term, _ = TERMS[geo]

    def go():
        py.build_payload([term, visa_term], timeframe=TIMEFRAME, geo=geo)
        return py.interest_over_time()
    df = _retry(go)
    if df is None or df.empty:
        return None
    base, visa = float(df[term].mean()), float(df[visa_term].mean())
    return {"geo": geo, "country": name, "term": term, "visa_term": visa_term,
            "mean_base": round(base, 2), "mean_visa": round(visa, 2),
            "visa_share": round(visa / base, 3) if base > 0 else None, "weeks": len(df)}


def test() -> None:
    """Feasibility test: one worldwide request and three country requests; writes a report."""
    lines = []
    py = client()
    t0 = time.time()
    ib = interest_by_country(py)
    lines.append(f"interest_by_country: {'FAILED' if ib is None else f'{len(ib)} countries'} ({time.time() - t0:.0f}s)")
    if ib is not None:
        lines.append(ib.head(25).to_string(index=False))
    for geo in ("DE", "KR", "IN"):
        time.sleep(PAUSE)
        t0 = time.time()
        r = visa_share(py, geo)
        lines.append(f"visa_share {geo}: {r} ({time.time() - t0:.0f}s)")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/trends_test.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def collect() -> None:
    """Weekly: worldwide interest by country + visa share for each market. Keeps a dated history."""
    py = client()
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    ib = interest_by_country(py)
    if ib is not None:
        ib.insert(0, "date", today)
        old = pd.read_csv(OUT_INTEREST) if OUT_INTEREST.exists() else pd.DataFrame()
        old = old[old["date"] != today] if not old.empty else old
        pd.concat([old, ib], ignore_index=True).to_csv(OUT_INTEREST, index=False)
    rows = []
    for geo in TERMS:
        time.sleep(PAUSE)
        r = visa_share(py, geo)
        if r:
            r["date"] = today
            r["visa_needed"] = TERMS[geo][3]
            rows.append(r)
    if rows:
        new = pd.DataFrame(rows)
        old = pd.read_csv(OUT_VISA) if OUT_VISA.exists() else pd.DataFrame()
        old = old[old["date"] != today] if not old.empty else old
        pd.concat([old, new], ignore_index=True).to_csv(OUT_VISA, index=False)
    log.info("trends: interest %s, visa rows %d", "ok" if ib is not None else "failed", len(rows))


def test2() -> None:
    """Second test: topic ids, competitor share by country, visa share with monthly data over 5 years."""
    lines = []
    py = client()
    ids = {}
    for name in ("Uzbekistan", "Kazakhstan", "Kyrgyzstan", "Georgia", "Tajikistan", "Turkmenistan", "Samarkand"):
        sug = _retry(lambda: py.suggestions(name)) or []
        lines.append(f"suggest {name}: " + "; ".join(f"{x.get('mid')}={x.get('title')}/{x.get('type')}" for x in sug[:4]))
        hit = next((x for x in sug if x.get("title") == name and "ountry" in str(x.get("type"))), None) or (sug[0] if sug else None)
        if hit:
            ids[name] = hit["mid"]
        time.sleep(3)
    comp = [ids[k] for k in ("Uzbekistan", "Kazakhstan", "Kyrgyzstan", "Georgia", "Tajikistan") if k in ids]
    names = {v: k for k, v in ids.items()}

    def go():
        py.build_payload(comp, timeframe=TIMEFRAME, geo="")
        return py.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True)
    time.sleep(PAUSE)
    df = _retry(go)
    if df is not None:
        df = df.rename(columns=names)
        keep = df[df["geoCode"].isin(["US", "GB", "IN", "DE", "FR", "IT", "JP", "KR", "TR", "RU", "KZ", "CN", "ES", "PL", "NL"])]
        lines.append("competitor split by country (row = %):\n" + keep.to_string())
    else:
        lines.append("competitor split: FAILED")
    for geo in ("DE", "KR", "IN", "JP", "TR"):
        name, term, visa_term, _ = TERMS[geo]

        def go2():
            py.build_payload([term, visa_term], timeframe="2021-10-01 2026-10-26", geo=geo)
            return py.interest_over_time()
        time.sleep(PAUSE)
        d = _retry(go2)
        if d is None or d.empty:
            lines.append(f"visa5y {geo}: FAILED")
            continue
        lines.append(f"visa5y {geo}: rows={len(d)} base_mean={d[term].mean():.2f} visa_mean={d[visa_term].mean():.2f} "
                     f"visa_nonzero_rows={(d[visa_term] > 0).sum()} share={d[visa_term].mean() / max(d[term].mean(), 1e-9):.3f}")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/trends_test2.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    {"test": test, "test2": test2, "collect": collect}[sys.argv[1] if len(sys.argv) > 1 else "test"]()
