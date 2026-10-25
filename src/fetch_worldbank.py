"""Download World Bank indicators for the main source countries (for the affordability study).
Output: data/worldbank.csv  (country, indicator, year, value) — latest 15 years."""
from __future__ import annotations

import csv

from . import config
from .util import http_get, log

COUNTRIES = "KAZ;KGZ;TJK;RUS;TKM;AFG;CHN;TUR;KOR;IND;DEU;JPN;ITA;FRA;USA;GBR;UZB"
INDICATORS = {
    "NE.CON.PRVT.CD": "household consumption, current US$ (total)",
    "NE.CON.PRVT.PC.KD": "household consumption per capita, constant 2015 US$",
    "SP.POP.TOTL": "population",
    "SP.POP.0014.TO": "population 0-14",
    "SI.POV.GINI": "Gini index",
    "NY.GDP.PCAP.CD": "GDP per capita, current US$",
    "PA.NUS.FCRF": "official exchange rate, LCU per US$",
    "FP.CPI.TOTL.ZG": "inflation, consumer prices %",
    "ST.INT.DPRT": "international tourism, departures",
}
OUT = config.DATA / "worldbank.csv"


def main() -> None:
    rows = []
    for ind in INDICATORS:
        url = f"https://api.worldbank.org/v2/country/{COUNTRIES}/indicator/{ind}"
        data = http_get(url, params={"format": "json", "date": "2010:2026", "per_page": 2000}, as_json=True, timeout=60)
        if not data or len(data) < 2 or not data[1]:
            log.warning("no data for %s", ind)
            continue
        for r in data[1]:
            if r.get("value") is not None:
                rows.append((r["countryiso3code"], ind, r["date"], r["value"]))
        log.info("%s: %d values", ind, sum(1 for x in rows if x[1] == ind))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "indicator", "year", "value"])
        w.writerows(sorted(rows))


if __name__ == "__main__":
    main()
