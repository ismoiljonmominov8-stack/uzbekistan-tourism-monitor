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
KEEP = ("tptincj992", "aptincj992")   # bulk files write concept + pop + age
OUT = config.DATA / "wid.csv"


def main() -> None:
    log.info("downloading %s", URL)
    r = requests.get(URL, timeout=600, headers={"User-Agent": "uzbekistan-tourism-monitor (research)"})
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    debug = [f"zip bytes: {len(r.content)}", f"files: {len(names)}", "sample: " + ", ".join(names[:15])]
    rows = []
    for cc in COUNTRIES:
        name = next((n for n in names if n.split("/")[-1] == f"WID_data_{cc}.csv"), None)
        if not name:
            log.warning("missing %s", cc)
            debug.append(f"{cc}: file missing")
            continue
        text = z.read(name).decode("utf-8", errors="replace")
        if cc == "IN":
            debug.append("IN head:\n" + "\n".join(text.splitlines()[:5]))
        delim = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
        recs = [x for x in csv.DictReader(io.StringIO(text), delimiter=delim) if x.get("variable") in KEEP]
        debug.append(f"{cc}: {len(recs)} matching rows")
        if not recs:
            continue
        last = max(int(x["year"]) for x in recs if x["value"])
        rows += [(cc, x["variable"], x["percentile"], x["year"], x["value"]) for x in recs if int(x["year"]) == last and x["value"]]
        log.info("%s: year %s, %d values", cc, last, sum(1 for x in recs if int(x["year"]) == last))
    from pathlib import Path
    Path("reports").mkdir(exist_ok=True)
    Path("reports/wid_debug.txt").write_text("\n".join(debug) + "\n", encoding="utf-8")
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country", "variable", "percentile", "year", "value"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
