"""Diagnostics: save the plain text of stat.uz releases to reports/statuz_raw/ so the parser can be
checked against the real wording. Usage: python -m src.debug_statuz <url> [<url> ...]"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from . import config, statuz
from .util import http_get

OUT = config.ROOT / "reports" / "statuz_raw"


def main(urls):
    OUT.mkdir(parents=True, exist_ok=True)
    for url in urls:
        html = http_get(url)
        nid = re.search(r"/(\d+)-", url).group(1)
        if not html:
            (OUT / f"{nid}.txt").write_text(f"FETCH FAILED: {url}\n", encoding="utf-8")
            continue
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n")
        # keep only the part around the figures, not the whole site menu
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        start = next((i for i, l in enumerate(lines) if re.search(r"January|foreign|tourist", l, re.I)), 0)
        body = "\n".join(lines[max(0, start - 3): start + 60])
        parsed = statuz.parse_release(text)
        Path(OUT / f"{nid}.txt").write_text(f"URL: {url}\nPARSED: {parsed}\n\n{body}\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
