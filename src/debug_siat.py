"""Diagnostics: find SIAT (siat.stat.uz) datasets about inbound tourism and save their download links.
Usage: python -m src.debug_siat <first_id> <last_id>"""
import re
import sys

from bs4 import BeautifulSoup

from . import config
from .util import http_get

OUT = config.ROOT / "reports"


def main(a, b):
    OUT.mkdir(exist_ok=True)
    lines = []
    for i in range(a, b + 1):
        html = http_get(f"https://siat.stat.uz/data/{i}/?lang=en", retries=1, timeout=20)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.get_text(" ", strip=True) if soup.title else "").replace(" — SIAT", "")
        if not re.search(r"touris|foreign|visitor|arriv", title, re.I):
            continue
        links = sorted({x["href"] for x in soup.find_all("a", href=True) if "api.siat" in x["href"]})
        lines.append(f"{i}\t{title}\n\t" + "\n\t".join(links))
    (OUT / f"siat_index_{a}_{b}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")




def download(ids):
    """Save CSV and JSON of the given SIAT datasets to reports/siat/."""
    out = OUT / "siat"
    out.mkdir(parents=True, exist_ok=True)
    for i in ids:
        for fmt in ("csv", "json"):
            text = http_get(f"https://api.siat.stat.uz/sdmx/{i}/table/download/?download_format={fmt}", timeout=60)
            (out / f"{i}.{fmt}").write_text(text or "FETCH FAILED\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "download":
        download(sys.argv[2:])
    else:
        main(int(sys.argv[1]), int(sys.argv[2]))
