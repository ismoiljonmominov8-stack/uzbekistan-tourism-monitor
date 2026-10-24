"""Collector 2: official inbound-tourism figures from stat.uz press releases.

stat.uz publishes monthly figures only as press-release text ("In January-August 2026,
9,102,729 foreign citizens ... Kyrgyz Republic - 2,524,378 people; ..."). The figures are
year-to-date (cumulative). This module finds those releases, parses them, sanity-checks
the numbers and stores them in data/arrivals_ytd.csv. Monthly values are derived later.
"""
import re
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from . import config
from .util import http_get, log, read_json, write_json

CSV = config.DATA / "arrivals_ytd.csv"
SEEN = config.DATA / "statuz_seen.json"
COLUMNS = ["year", "month", "country", "ytd", "url", "note"]

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
_NUM = r"\d[\d,\s \.]*\d|\d"

# stat.uz spells countries in different ways; map them to one name.
COUNTRY_ALIASES = {
    "kyrgyz republic": "Kyrgyzstan", "kyrgyzstan": "Kyrgyzstan",
    "republic of korea": "Republic of Korea", "korea": "Republic of Korea", "south korea": "Republic of Korea",
    "turkey": "Türkiye", "turkiye": "Türkiye", "türkiye": "Türkiye",
    "russian federation": "Russia", "russia": "Russia",
}


def _to_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _norm_country(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" .;:-–—")
    return COUNTRY_ALIASES.get(name.lower(), name)


def is_inbound(title: str, text: str) -> bool:
    t = title.lower()
    if "touris" not in t and "turist" not in t:
        return False
    if any(w in t for w in ("abroad", "went to", "travel to", "uzbeks", "outbound")):
        return False
    return bool(re.search(r"foreign (citizens|visitors|tourists)", text, re.I))


def parse_release(text: str) -> dict | None:
    """Return {year, month, total, countries:{name: n}, notes:[...]} or None if not parseable."""
    flat = re.sub(r"[ \t ]+", " ", text)

    # Period: "January-August 2026", "January–February 2026", "In January 2026"
    m = re.search(r"January(?:\s*[-–—]\s*([A-Za-z]+))?,?\s+(20\d\d)", flat)
    if not m:
        return None
    end_month = (m.group(1) or "january").lower()
    if end_month not in MONTHS:
        return None
    year, month = int(m.group(2)), MONTHS.index(end_month) + 1

    total = None
    for pat in (rf"total of ({_NUM}) foreign", rf"welcomed ({_NUM}) foreign", rf"({_NUM}) foreign citizens"):
        tm = re.search(pat, flat, re.I)
        if tm:
            total = _to_int(tm.group(1))
            break
    if not total:
        return None

    notes, countries = [], {}
    line_pat = re.compile(
        rf"^\s*[-•*\d\.\)]*\s*([A-Z][A-Za-zÀ-ÿ'’\.\s]+?)\s*[-–—:]\s*({_NUM})\s*(thousand\s+)?(?:people|persons|tourists)",
        re.M,
    )
    for cm in line_pat.finditer(text):
        name, raw = _norm_country(cm.group(1)), cm.group(2)
        val = _to_int(raw)
        # Known typos in releases, e.g. "43,572,000 people" or "69,070 thousand people"
        # meaning 43,572 and 69,070. A single country can never exceed the total.
        if val > total:
            fixed = val
            while fixed > total:
                fixed //= 1000
            notes.append(f"{name}: '{raw.strip()}' read as {fixed} (source typo)")
            val = fixed
        countries[name] = val
    if not countries:
        notes.append("no country lines found")
    return {"year": year, "month": month, "total": total, "countries": countries, "notes": notes}


def validate(rel: dict, df: pd.DataFrame) -> list[str]:
    """Sanity checks. Any problem means the release is stored but NOT posted to the channel."""
    problems = []
    y, m, total = rel["year"], rel["month"], rel["total"]
    per_month = total / m
    if not 200_000 <= per_month <= 4_000_000:
        problems.append(f"average {per_month:,.0f}/month is outside the plausible range")
    if len(rel["countries"]) < 5:
        problems.append(f"only {len(rel['countries'])} countries parsed")
    if sum(rel["countries"].values()) > total:
        problems.append("countries add up to more than the total")
    totals = df[df["country"] == "TOTAL"]
    prev = totals[(totals["year"] == y) & (totals["month"] == m - 1)]
    if len(prev) and total < int(prev["ytd"].iloc[0]):
        problems.append("year-to-date total is lower than last month's")
    nxt = totals[(totals["year"] == y) & (totals["month"] == m + 1)]
    if len(nxt) and total > int(nxt["ytd"].iloc[0]):
        problems.append("year-to-date total is higher than next month's")
    if any("typo" in n for n in rel.get("notes", [])):
        problems.append("source contained a typo that was auto-corrected; please confirm")
    return problems


def _list_links(page_url: str) -> list[tuple[str, str]]:
    html = http_get(page_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/news-of-committee/\d+", href):
            title = a.get_text(" ", strip=True)
            if title:
                out.append((urljoin(page_url, href), title))
    return list(dict.fromkeys(out))


def load() -> pd.DataFrame:
    if CSV.exists():
        return pd.read_csv(CSV)
    return pd.DataFrame(columns=COLUMNS)


def collect() -> list[dict]:
    """Scan recent press releases; store new inbound-tourism ones. Returns newly parsed releases."""
    seen = set(read_json(SEEN, []))
    pages = config.STATUZ_BACKFILL_PAGES if not seen else config.STATUZ_LIST_PAGES
    links = _list_links(config.STATUZ_LIST_URL)
    for i in range(1, pages):
        links += _list_links(f"{config.STATUZ_LIST_URL}?start={i * config.STATUZ_PAGE_SIZE}")
    links = list(dict.fromkeys(links))
    if not links:
        log.warning("stat.uz: no press-release links found (site down or layout changed)")
        return []

    df, new_releases = load(), []
    for url, title in links:
        if url in seen:
            continue
        low = title.lower()
        if "touris" not in low and "turist" not in low:
            seen.add(url)
            continue
        html = http_get(url)
        if not html:
            continue  # retry next run
        seen.add(url)
        text = BeautifulSoup(html, "html.parser").get_text("\n")
        if not is_inbound(title, text):
            continue
        rel = parse_release(text)
        if not rel:
            log.warning("stat.uz: could not parse %s", url)
            continue
        if ((df["year"] == rel["year"]) & (df["month"] == rel["month"])).any():
            continue  # same period already stored (releases are often duplicated)
        rel["problems"] = validate(rel, df)
        if rel["problems"]:
            log.warning("stat.uz: %s-%02d failed checks: %s", rel["year"], rel["month"], rel["problems"])
        note = "; ".join(rel["notes"] + [f"CHECK FAILED: {p}" for p in rel["problems"]])
        rows = [(rel["year"], rel["month"], "TOTAL", rel["total"], url, note)]
        rows += [(rel["year"], rel["month"], c, n, url, "") for c, n in rel["countries"].items()]
        df = pd.concat([df, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
        rel["url"] = url
        new_releases.append(rel)
        log.info("stat.uz: stored %s-%02d total=%s (%d countries)", rel["year"], rel["month"], rel["total"],
                 len(rel["countries"]))

    if new_releases:
        df = df.sort_values(["year", "month", "country"])
        df.to_csv(CSV, index=False)
    write_json(SEEN, sorted(seen))
    if pages == config.STATUZ_BACKFILL_PAGES:
        log.info("stat.uz: first run, %d past releases stored without posting", len(new_releases))
        return []  # don't flood the channel with a year of old releases
    return new_releases


def monthly(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Derive single-month arrivals from year-to-date figures (month m minus month m-1)."""
    df = load() if df is None else df
    if df.empty:
        return pd.DataFrame(columns=["year", "month", "country", "arrivals"])
    df = df[["year", "month", "country", "ytd"]].copy()
    prev = df.copy()
    prev["month"] = prev["month"] + 1
    merged = df.merge(prev, on=["year", "month", "country"], how="left", suffixes=("", "_prev"))
    merged.loc[merged["month"] == 1, "ytd_prev"] = 0
    merged = merged.dropna(subset=["ytd_prev"])
    merged["arrivals"] = (merged["ytd"] - merged["ytd_prev"]).astype(int)
    # a negative month means the source revised its numbers or changed definitions
    merged = merged[merged["arrivals"] >= 0]
    return merged[["year", "month", "country", "arrivals"]].sort_values(["year", "month", "country"])
