"""One-off: save the plain text of every tourism-related stat.uz release found by the archive scan,
so parsing can be developed and checked offline. Output: reports/statuz_archive/raw/<id>.txt"""
from __future__ import annotations

import csv
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup

from .util import http_get, log

SCAN = Path("reports/statuz_archive/releases.csv")
RAW = Path("reports/statuz_archive/raw")
TOURISM = re.compile(r"touris|turist|visit|arriv|came to Uzbekistan|entering|foreign citizens|foreigners", re.I)


def fetch(row: dict) -> bool:
    out = RAW / f"{row['id']}.txt"
    if out.exists():
        return True
    html = http_get(row["url"], retries=3, timeout=40)
    if not html:
        return False
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out.write_text(f"URL: {row['url']}\nTITLE: {row['title']}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return True


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(SCAN.open(encoding="utf-8"))
            if TOURISM.search(r["title"]) or r["parser_ok"] == "True"]
    log.info("fetching %d releases", len(rows))
    with ThreadPoolExecutor(6) as pool:
        ok = list(pool.map(fetch, rows))
    log.info("saved %d / %d", sum(ok), len(rows))


if __name__ == "__main__":
    main()
