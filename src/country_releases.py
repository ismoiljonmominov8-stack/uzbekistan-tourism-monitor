"""Single-country stat.uz releases ("28.2 thousand tourists from Italy visited Uzbekistan in eight months").

The monthly top-10 list never reaches the high-spending distant markets (Japan, USA, Italy, France, UK...),
but the statistics committee publishes a separate release about one country a few times a year. Each gives:
  * the total since January (year-to-date) for that country — an official anchor point,
  * the change vs the same period last year — so last year's value for that period is official too,
  * a split by purpose of visit ("travel/tourism" = leisure).
Output: data/country_releases.csv, one row per (country, year, months covered).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import config

OUT = config.DATA / "country_releases.csv"
COLUMNS = ["country", "year", "month", "ytd", "exact", "prev_ytd", "leisure", "url", "source_id"]

# nationality adjective / phrase in the release -> country name used in the rest of the data
NATIONALITY = {
    "italian": "Italy", "german": "Germany", "japanese": "Japan", "us": "United States", "u.s.": "United States",
    "american": "United States", "korean": "Republic of Korea", "south korean": "Republic of Korea",
    "french": "France", "british": "United Kingdom", "spanish": "Spain", "indian": "India", "chinese": "China",
    "turkish": "Türkiye", "iranian": "Iran", "australian": "Australia", "malaysian": "Malaysia",
    "indonesian": "Indonesia", "israeli": "Israel", "polish": "Poland", "canadian": "Canada", "dutch": "Netherlands",
    "swiss": "Switzerland", "austrian": "Austria", "belgian": "Belgium", "czech": "Czech Republic",
    "vietnamese": "Viet Nam", "thai": "Thailand", "singaporean": "Singapore", "saudi": "Saudi Arabia",
    "emirati": "United Arab Emirates", "pakistani": "Pakistan", "azerbaijani": "Azerbaijan", "belarusian": "Belarus",
    "ukrainian": "Ukraine", "georgian": "Georgia", "latvian": "Latvia", "lithuanian": "Lithuania",
    "estonian": "Estonia", "hungarian": "Hungary", "greek": "Greece", "portuguese": "Portugal",
    "swedish": "Sweden", "norwegian": "Norway", "finnish": "Finland", "danish": "Denmark",
}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
NUM = r"(\d[\d,. ]*\d|\d)\s*(thousand)?"


def _num(s: str, unit: str | None) -> tuple[int, bool]:
    s = s.replace(" ", "")
    if unit:                                   # "28.2 thousand", "3,2 thousand" (comma = decimal)
        return int(round(float(s.replace(",", ".")) * 1000)), False
    return int(s.replace(",", "").replace(".", "")), True   # "26,138 people"


def parse(text: str) -> dict | None:
    flat = re.sub(r"\s+", " ", text.replace("–", "-").replace("—", "-"))
    nat = "|".join(sorted((re.escape(k) for k in NATIONALITY), key=len, reverse=True))
    m = re.search(rf"(?:a total of |,\s*)?{NUM} ({nat}) citizens (?:visited|arrived|entered|came)[^.]*?"
                  rf"(?:in|during) (?:the )?(?:(january)(?:\s*-\s*|\s+to\s+)?([a-z]+)?\s+(20\d\d)|(20\d\d))", flat, re.I)
    if not m:
        m2 = re.search(rf"in (january)(?:\s*-\s*|\s+to\s+)?([a-z]+)?\s+(20\d\d),? (?:a total of )?{NUM} ({nat}) citizens", flat, re.I)
        if not m2:
            return None
        start, end, year, n, unit, natn = m2.groups()
        full = None
    else:
        n, unit, natn, start, end, year, full = m.groups()
    if full:
        year, month = int(full), 12
    else:
        end = (end or "january").lower()
        if end not in MONTHS:
            end = "january"
        year, month = int(year), MONTHS.index(end) + 1
    ytd, exact = _num(n, unit)
    out = {"country": NATIONALITY[natn.lower()], "year": year, "month": month, "ytd": ytd, "exact": exact,
           "prev_ytd": None, "leisure": None}
    # "increased by 5,500 people", "by 4.7 thousand people", "by almost 3 thousand people" — never "1.7 times" or "27 %"
    ch = re.search(r"(increased|decreased|grew|fell|rose) by (?:almost |about |nearly |more than )?"
                   r"(\d[\d,. ]*\d|\d)\s*(thousand)?\s*(?:people|persons|tourists|citizens)\b", flat, re.I)
    if ch:
        d, _ = _num(ch.group(2), ch.group(3))
        out["prev_ytd"] = ytd - d if ch.group(1).lower() in ("increased", "grew", "rose") else ytd + d
    if out["prev_ytd"] is None:   # only a percentage: "This figure increased by 15.8 % compared to..."
        pc = re.search(r"(?:figure|indicator|number)[^.]{0,40}?(increased|decreased) by (\d+(?:[.,]\d+)?)\s*%[^.]{0,30}compared", flat, re.I)
        if pc:
            r = float(pc.group(2).replace(",", ".")) / 100
            out["prev_ytd"] = round(ytd / (1 + r if pc.group(1).lower() == "increased" else 1 - r))
    le = re.search(rf"\b(?:travel|tourism)\s*[-:]\s*{NUM}", flat, re.I)
    if le:
        out["leisure"] = _num(le.group(1), le.group(2))[0]
    return out


def parse_dir(raw: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(raw.glob("*.txt")):
        text = f.read_text(encoding="utf-8")
        url = re.search(r"URL: (\S+)", text)
        rel = parse(text)
        if rel:
            rows.append(rel | {"url": url.group(1) if url else "", "source_id": f.stem})
    return pd.DataFrame(rows, columns=COLUMNS)


def load() -> pd.DataFrame:
    return pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=COLUMNS)


def add(rel: dict, url: str) -> bool:
    """Store one parsed release (used by the daily stat.uz scan). True if it was new."""
    df = load()
    key = (df["country"] == rel["country"]) & (df["year"] == rel["year"]) & (df["month"] == rel["month"])
    if key.any():
        return False
    row = rel | {"url": url, "source_id": re.search(r"/(\d+)-", url).group(1) if re.search(r"/(\d+)-", url) else ""}
    df = pd.concat([df, pd.DataFrame([row], columns=COLUMNS)], ignore_index=True)
    df.sort_values(["country", "year", "month"]).to_csv(OUT, index=False)
    return True


def _main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        return backfill()
    d = parse_dir(Path(sys.argv[1] if len(sys.argv) > 1 else "reports/statuz_archive/raw"))
    d = d.sort_values(["country", "year", "month"]).drop_duplicates(["country", "year", "month"], keep="last")
    d.to_csv(OUT, index=False)
    print(d.to_string())


TOURISM_SLUG = re.compile(r"turist|tourist|o-imi|oqimi|fu-arolari|fuqarolari|tashrif", re.I)


def backfill() -> None:
    """One-off (GitHub Actions — stat.uz blocks other networks): fetch the tourism pages the daily scan marked as
    seen before it could read single-country releases, save their text and store every country release found."""
    from concurrent.futures import ThreadPoolExecutor

    from bs4 import BeautifulSoup

    from .util import http_get, log, read_json
    raw = Path("reports/statuz_archive/raw")
    raw.mkdir(parents=True, exist_ok=True)
    have = {f.stem for f in raw.glob("*.txt")}
    seen = read_json(config.DATA / "statuz_seen.json", [])
    todo = []
    for u in seen:
        m = re.search(r"/(\d+)-", u)
        if m and int(m.group(1)) >= 40000 and m.group(1) not in have and TOURISM_SLUG.search(u):
            todo.append((m.group(1), u))
    log.info("backfill: %d pages to fetch", len(todo))

    def fetch(item):
        sid, url = item
        html = http_get(url, retries=3, timeout=40)
        if not html:
            return None
        lines = [l.strip() for l in BeautifulSoup(html, "html.parser").get_text("\n").splitlines() if l.strip()]
        text = f"URL: {url}\n\n" + "\n".join(lines) + "\n"
        (raw / f"{sid}.txt").write_text(text, encoding="utf-8")
        return url, parse(text)

    with ThreadPoolExecutor(6) as pool:
        res = [r for r in pool.map(fetch, todo) if r]
    n = sum(add(rel, url) for url, rel in res if rel)
    log.info("backfill: fetched %d, new country releases %d", len(res), n)


if __name__ == "__main__":
    _main()
