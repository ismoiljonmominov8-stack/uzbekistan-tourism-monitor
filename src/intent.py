"""Google travel-intent searches: the Uzbekistan topic inside Google's "Travel" category (cat 67), monthly, by
country. Unlike the plain topic (news, sport, business...), this keeps searches made while planning a trip
(tours, hotels, flights, sights), in any language. Used to test whether planning shows up before arrivals
(src/signals_test.py, signal "intent"). Output: data/intent_monthly.csv (month, geo, value 0-100 per geo)."""
from __future__ import annotations

import time

import pandas as pd

from . import config
from .trends import TOPICS, _retry, client
from .util import log

OUT = config.DATA / "intent_monthly.csv"
TRAVEL_CAT = 67
GEOS = {"": "TOTAL", "KZ": "Kazakhstan", "KG": "Kyrgyzstan", "TJ": "Tajikistan", "RU": "Russia", "TR": "Türkiye",
        "IN": "India", "KR": "Republic of Korea", "TM": "Turkmenistan", "CN": "China"}
TIMEFRAME = "2019-01-01 2026-10-31"     # longer than 5 years -> Google returns monthly values
PAUSE = 15


def collect(timeframe: str = TIMEFRAME) -> pd.DataFrame:
    py = client()
    rows = []
    for geo, level in GEOS.items():
        def go():
            py.build_payload([TOPICS["Uzbekistan"]], cat=TRAVEL_CAT, timeframe=timeframe, geo=geo)
            return py.interest_over_time()
        df = _retry(go)
        if df is None or df.empty:
            log.warning("intent: no data for %s", geo or "worldwide")
        else:
            s = df[TOPICS["Uzbekistan"]]
            nz = int((s > 0).sum())
            log.info("intent %s: %d months, %d non-zero, last %s", geo or "world", len(s), nz, s.index.max().date())
            rows += [{"month": d.strftime("%Y-%m"), "geo": geo or "WORLD", "level": level, "value": int(v)} for d, v in s.items()]
        time.sleep(PAUSE)
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_csv(OUT, index=False)
    return out


if __name__ == "__main__":
    d = collect()
    print(d.groupby("level")["value"].agg(["count", lambda s: (s > 0).sum(), "mean"]) if not d.empty else "no data")
