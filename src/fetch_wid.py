"""Download income-distribution thresholds from the World Inequality Database (wid.world, CC BY).
Keeps, for each country, the latest year of:
  tptinc992j  income threshold at each percentile (pre-tax national income, adults, equal split)
  aptinc992j  average income per adult in each percentile group
Output: data/wid.csv (country, variable, percentile, year, value)."""
from __future__ import annotations

import csv
import io
import zipfile

import requests

from . import config
from .util import log

URL = "https://wid.world/bulk_download/wid_all_data.zip"
COUNTRIES = ["KZ", "KG", "TJ", "TM", "AF", "RU", "CN", "TR", "KR", "IN", "DE", "JP", "IT", "FR", "GB", "US", "UZ"]
KEEP = ("tptinc992j", "aptinc992j")
OUT = config.DATA / "wid.csv"


def main() -> None:
    log.info("downloading %s", URL)
    r = requests.get(URL, timeout=600, headers={"User-Agent": "uzbekistan-tourism-monitor (research)"})
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    rows = []
    for cc in COUNTRIES:
        name = f"WID_data_{cc}.csv"
        if name not in z.namelist():
            log.warning("missing %s", name)
            continue
        text = z.read(name).decode("utf-8")
        recs = [x for x in csv.DictReader(io.StringIO(text), delimiter=";") if x["variable"] in KEEP and x["country"] == cc]
        if not recs:
            continue
        last = max(int(x["year"]) for x in recs if x["value"])
        rows += [(cc, x["variable"], x["percentile"], x["year"], x["value"]) for x in recs if int(x["year"]) == last and x["value"]]
        log.info("%s: year %s, %d values", cc, last, sum(1 for x in recs if int(x["year"]) == last))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "variable", "percentile", "year", "value"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
