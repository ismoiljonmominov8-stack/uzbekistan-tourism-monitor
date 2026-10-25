"""One-off archive scan: which monthly inbound-tourism releases for 2018–2024 exist on stat.uz?

Runs on GitHub (the site is not reachable from everywhere). Crawls the committee news listing as
deep as it goes, keeps releases whose title looks like foreign arrivals (English, Uzbek or Russian),
opens each one, and records the period (year, end month), a total if one can be read, and whether
the current English parser understands it. Nothing is added to the project data.

Output: reports/statuz_archive/releases.csv and coverage.txt (a year x month grid).
"""
from __future__ import annotations

import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup

from . import config, statuz
from .util import http_get, log

OUT = Path("reports/statuz_archive")
KEYS = re.compile(r"touris|turist|foreign|chet el|chet fuqaro|xorijlik|xorijiy fuqaro|иностран|турист|визит", re.I)

MONTH_WORDS = [
    ("january", "yanvar", "январ"), ("february", "fevral", "феврал"), ("march", "mart", "март"),
    ("april", "aprel", "апрел"), ("may", "may", "ма[йя]"), ("june", "iyun", "июн"), ("july", "iyul", "июл"),
    ("august", "avgust", "август"), ("september", "sentabr", "сентябр"), ("october", "oktabr", "октябр"),
    ("november", "noyabr", "ноябр"), ("december", "dekabr", "декабр")]
MONTH_RE = [re.compile("|".join(rf"\b{w}" for w in ws), re.I) for ws in MONTH_WORDS]
ANY_MONTH = "|".join(rf"{w}" for ws in MONTH_WORDS for w in ws)
RANGE = re.compile(rf"(?:january|yanvar|январ)\w*\s*[-–—]\s*({ANY_MONTH})\w*", re.I)
YEAR = re.compile(r"\b(201[5-9]|202[0-6])\b")
NUM = r"\d{1,3}(?:[,  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
TOTAL = re.compile(rf"({NUM})\s*(million|mln|million|ming|thousand|млн|тыс)?\.?\s*(?:nafar\s*)?"
                   rf"(?:foreign|chet el|xorijlik|xorijiy|иностран)", re.I)


def month_index(word: str) -> int | None:
    for i, rx in enumerate(MONTH_RE):
        if rx.match(word):
            return i + 1
    return None


def period(text: str) -> tuple[int | None, int | None]:
    """(year, end month) of a year-to-date period, from title + first part of the text."""
    m = RANGE.search(text)
    if m:
        end = month_index(m.group(1))
        y = YEAR.search(text[max(0, m.start() - 60): m.end() + 60])
        return (int(y.group(1)) if y else None), end
    # single month: "in January 2023", "2023 yil yanvar oyida", "в январе 2023"
    m = re.search(r"(?:january|yanvar|январ)\w*", text, re.I)
    if m:
        y = YEAR.search(text[max(0, m.start() - 40): m.end() + 40])
        return (int(y.group(1)) if y else None), 1
    return None, None


def to_number(num: str, unit: str | None) -> int | None:
    try:
        n = float(re.sub(r"[  ]", "", num).replace(",", "") if re.search(r"\d[,  ]\d{3}\b", num)
                  else num.replace(",", "."))
    except ValueError:
        return None
    u = (unit or "").lower()
    if u in ("million", "mln", "млн"):
        n *= 1e6
    elif u in ("ming", "thousand", "тыс"):
        n *= 1e3
    return int(round(n))


def listing(i: int) -> list[tuple[str, str]]:
    url = config.STATUZ_LIST_URL if i == 0 else f"{config.STATUZ_LIST_URL}?start={i * config.STATUZ_PAGE_SIZE}"
    try:
        return statuz._list_links(url)
    except Exception:  # noqa: BLE001
        return []


def inspect(item: tuple[str, str]) -> dict:
    url, title = item
    nid = int(re.search(r"/news-of-committee/(\d+)", url).group(1))
    row = {"id": nid, "url": url, "title": title[:160], "pub_date": "", "year": "", "month": "",
           "total_guess": "", "parser_ok": False, "parser_total": "", "error": ""}
    html = http_get(url, retries=2)
    if not html:
        row["error"] = "fetch failed"
        return row
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    d = re.search(r"\b(\d{2})\.(\d{2})\.(20\d\d)\b", text)
    if d:
        row["pub_date"] = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
    flat = re.sub(r"\s+", " ", text)
    start = flat.find(title[:40]) if title[:40] in flat else 0
    body = flat[start: start + 4000]
    y, m = period(title + " " + body)
    row["year"], row["month"] = y or "", m or ""
    t = TOTAL.search(body)
    if t:
        row["total_guess"] = to_number(t.group(1), t.group(2)) or ""
    try:
        rel = statuz.parse_release(text)
        if rel:
            row["parser_ok"], row["parser_total"] = True, rel["total"]
    except Exception as e:  # noqa: BLE001
        row["error"] = f"parser: {e}"[:80]
    return row


def main(max_pages: int = 2500, batch: int = 50) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    links, empty_batches, last_page = [], 0, 0
    with ThreadPoolExecutor(8) as pool:
        for b in range(0, max_pages, batch):
            pages = list(pool.map(listing, range(b, b + batch)))
            found = [x for p in pages for x in p]
            last_page = b + batch
            log.info("listing pages %d-%d: %d links", b, b + batch - 1, len(found))
            if not found:
                empty_batches += 1
                if empty_batches >= 2:
                    break
                continue
            empty_batches = 0
            links += found
        links = list(dict.fromkeys(links))
        ids = sorted(int(re.search(r"/(\d+)", u.split("news-of-committee")[1]).group(1)) for u, _ in links)
        log.info("total links %d, ids %s..%s", len(links), ids[0] if ids else "-", ids[-1] if ids else "-")
        cand = [x for x in links if KEYS.search(x[1])]
        log.info("candidate releases: %d", len(cand))
        rows = list(pool.map(inspect, cand))

    rows.sort(key=lambda r: r["id"])
    with open(OUT / "releases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)

    # coverage grid: a month counts if some release gives that year-to-date period with a total
    grid = {}
    for r in rows:
        if r["year"] and r["month"] and (r["total_guess"] or r["parser_ok"]):
            grid.setdefault(int(r["year"]), {}).setdefault(int(r["month"]), []).append(r)
    lines = [f"listing pages scanned: {last_page}; links: {len(links)}; candidates: {len(cand)}",
             f"oldest news id: {ids[0] if ids else '-'}", "",
             "year  " + " ".join(f"{m:>3}" for m in range(1, 13)) + "   (P = current parser reads it, t = only a total found, . = none)"]
    for y in range(2015, 2027):
        cells = []
        for m in range(1, 13):
            rs = grid.get(y, {}).get(m, [])
            cells.append("  P" if any(r["parser_ok"] for r in rs) else "  t" if rs else "  .")
        lines.append(f"{y}  " + " ".join(cells))
    (OUT / "coverage.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:]))
