"""Google Trends: Uzbekistan's share of search attention among similar destinations, by country.

Measure — "competitor share": in each country, Google splits searches for five destination TOPICS
(language independent: Uzbekistan, Kazakhstan, Kyrgyzstan, Georgia, Tajikistan) into percentages that
add up to 100. Uzbekistan's percentage says how much of the attention to this group of destinations it
gets in that country. Unlike Google's worldwide "interest by country" (where Uzbekistan itself scores 100
and distant markets round to 0-1), this keeps full resolution in every market.

Kept as a yearly history from 2016 (one request per year) plus a rolling last-90-days snapshot taken
weekly. Topics count ALL searches about a country (news, sport, business), not only travel.

Tried and dropped (tests in reports/trends_test*.txt, October 2026): searches for "<Uzbekistan> visa" in
local languages are below Google's reporting threshold in Germany, Korea and Japan even over 5 years,
so a "visa awareness" indicator cannot be built from Trends. China has no Google data (Google is blocked).
"""
from __future__ import annotations

import sys
import time
from datetime import date

import pandas as pd

from . import config
from .util import log

TOPICS = {   # Google Knowledge Graph ids (checked with suggestions(), October 2026)
    "Uzbekistan": "/m/07t_x", "Kazakhstan": "/m/047lj", "Kyrgyzstan": "/m/0jt3tjf",
    "Georgia": "/m/0d0kn", "Tajikistan": "/m/07dvs",
}
NAMES_UZ = {"Uzbekistan": "O'zbekiston", "Kazakhstan": "Qozog'iston", "Kyrgyzstan": "Qirg'iziston",
            "Georgia": "Gruziya", "Tajikistan": "Tojikiston"}
FIRST_YEAR = 2016
OUT = config.DATA / "trends_share.csv"      # period, geo, country, destination, share
PAUSE = 12


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


def split_by_country(py, timeframe: str) -> pd.DataFrame | None:
    ids = list(TOPICS.values())
    back = {v: k for k, v in TOPICS.items()}

    def go():
        py.build_payload(ids, timeframe=timeframe, geo="")
        return py.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=True)
    df = _retry(go)
    if df is None or df.empty:
        return None
    df = df.reset_index().rename(columns={"geoName": "country", "geoCode": "geo", **back})
    df = df[df[list(TOPICS)].sum(axis=1) > 0]
    long = df.melt(id_vars=["country", "geo"], value_vars=list(TOPICS), var_name="destination", value_name="share")
    return long


def load() -> pd.DataFrame:
    return pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["period", "geo", "country", "destination", "share"])


def collect() -> None:
    """Fill missing past years (full calendar years only), refresh the current year to date and add a
    last-90-days snapshot. Safe to run weekly."""
    py = client()
    df = load()
    have = set(df["period"].astype(str))
    this = date.today().year
    todo = [str(y) for y in range(FIRST_YEAR, this) if str(y) not in have] + [str(this)]
    frames = [df[~df["period"].astype(str).isin(todo)]]
    for i, period in enumerate(todo):
        if i:
            time.sleep(PAUSE)
        end = f"{period}-12-31" if int(period) < this else date.today().isoformat()
        part = split_by_country(py, f"{period}-01-01 {end}")
        if part is None:
            log.warning("trends: %s failed", period)
            if period in have:  # keep the old values rather than lose them
                frames.append(df[df["period"].astype(str) == period])
            continue
        frames.append(part.assign(period=period))
    time.sleep(PAUSE)
    snap = split_by_country(py, "today 3-m")
    label = "90d-" + date.today().isoformat()
    if snap is not None:
        frames = [f[f["period"].astype(str) != label] for f in frames]
        frames.append(snap.assign(period=label))
    out = pd.concat(frames, ignore_index=True)[["period", "geo", "country", "destination", "share"]]
    out.to_csv(OUT, index=False)
    log.info("trends: %d rows, periods %s", len(out), sorted(out["period"].astype(str).unique())[-4:])


if __name__ == "__main__":
    {"collect": collect}[sys.argv[1] if len(sys.argv) > 1 else "collect"]()
