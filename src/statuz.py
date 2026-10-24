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
COLUMNS = ["year", "month", "country", "ytd", "exact", "url", "note"]

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
# 2,844,201 | 199 048 | 6,319.1 | 2.8 | 3   (no newlines inside a number)
_NUM = r"\d{1,3}(?:[,  ]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_UNIT = r"(million|mln|thousand|ming)?"

# stat.uz spells countries in different ways; map them to one name.
COUNTRY_ALIASES = {
    "kyrgyz republic": "Kyrgyzstan", "kyrgyzstan": "Kyrgyzstan",
    "republic of korea": "Republic of Korea", "korea": "Republic of Korea", "south korea": "Republic of Korea",
    "turkey": "Türkiye", "turkiye": "Türkiye", "türkiye": "Türkiye",
    "russian federation": "Russia", "russia": "Russia",
}
OTHER = "Other countries"


def amount(num: str, unit: str | None) -> tuple[int, bool]:
    """'2,844,201' -> (2844201, exact); '2.8' + 'million' -> (2800000, rounded)."""
    num = re.sub(r"[  ]", "", num)
    unit = (unit or "").lower()
    if unit in ("million", "mln"):
        return round(float(num.replace(",", "")) * 1_000_000), False
    if unit in ("thousand", "ming"):
        # "6,319.1 thousand" (comma = thousands separator) and "851.9 thousand"
        return round(float(num.replace(",", "")) * 1_000), False
    return int(num.replace(",", "").split(".")[0]), True


def _norm_country(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" .;:-–—")
    if name.lower().startswith("other"):
        return OTHER
    return COUNTRY_ALIASES.get(name.lower(), name)


def is_inbound(title: str, text: str) -> bool:
    t = title.lower()
    if "touris" not in t and "turist" not in t and "foreign" not in t:
        return False
    if any(w in t for w in ("abroad", "went to", "travel to", "uzbeks ", "outbound")):
        return False
    return bool(re.search(r"foreign (citizens|nationals|visitors|tourists)", text, re.I))


def parse_release(text: str) -> dict | None:
    """Return {year, month, total, total_exact, countries:{name: (n, exact)}, notes:[...]} or None."""
    flat = re.sub(r"[ \t ]+", " ", text)

    # Period: "January-August 2026", "January–July 2026", "in January 2026"
    m = re.search(r"January(?:\s*[-–—]\s*([A-Za-z]+))?,?\s+(?:of\s+)?(20\d\d)", flat)
    if not m:
        return None
    end_month = (m.group(1) or "january").lower()
    if end_month not in MONTHS:
        return None
    year, month = int(m.group(2)), MONTHS.index(end_month) + 1

    tm = re.search(rf"({_NUM})\s*{_UNIT}\s+foreign (?:citizens|nationals|visitors|tourists)", flat, re.I)
    if not tm:
        return None
    total, total_exact = amount(tm.group(1), tm.group(2))

    # Only read country lines inside the article body: from the sentence with the total up to
    # the site footer. Otherwise menu items like "Eliminating bureaucracy – 2030" or
    # "Online: 168" look like countries.
    anchor = re.search(r"According to", text) or re.search(
        rf"({_NUM})\s*{_UNIT}\s+foreign (?:citizens|nationals)", text, re.I)
    body = text[anchor.start():] if anchor else text
    footer = re.search(r"National Statistics Committee of the Republic of Uzbekistan\s*\n\s*100170|Mustakillik"
                       r"|Found an error|Online:", body)
    body = body[: footer.start()] if footer else body

    notes, countries = [], {}
    line_pat = re.compile(
        rf"^[ \t]*[-•*\d\.\)]*[ \t]*([A-Z][A-Za-zÀ-ÿ'’\. ]+?)[ \t]*[-–—:][ \t]*({_NUM})[ \t]*{_UNIT}"
        rf"[ \t]*(?:people|persons|tourists)?[ \t]*[;\.,]?[ \t]*$",
        re.M,
    )
    for cm in line_pat.finditer(body):
        name = _norm_country(cm.group(1))
        if re.fullmatch(r"(19|20)\d\d", cm.group(2)) and not cm.group(3):
            continue  # a year such as "Eliminating bureaucracy – 2030", not a count
        val, exact = amount(cm.group(2), cm.group(3))
        # Known typos, e.g. "43,572,000 people" or "69,070 thousand people" meaning 43,572 and
        # 69,070. A single country can never exceed the total.
        if val > total:
            fixed = val
            while fixed > total:
                fixed //= 1000
            notes.append(f"{name}: '{cm.group(0).strip()}' read as {fixed} (source typo)")
            val, exact = fixed, True
        countries[name] = (val, exact)

    # When the release lists every country plus "Other countries", their sum is the exact total
    # (better than a rounded "7.5 million" in the text).
    if OTHER in countries and not total_exact and all(e for _, e in countries.values()):
        exact_sum = sum(v for v, _ in countries.values())
        if abs(exact_sum - total) / total < 0.05:
            notes.append(f"total {total:,} (rounded in text) replaced by the sum of all countries")
            total, total_exact = exact_sum, True
    countries.pop(OTHER, None)
    if not countries:
        notes.append("no country lines found")
    return {"year": year, "month": month, "total": total, "total_exact": total_exact,
            "countries": countries, "notes": notes}


def validate(rel: dict, df: pd.DataFrame) -> list[str]:
    """Sanity checks. Any problem means the release is stored but NOT posted to the channel."""
    problems = []
    y, m, total = rel["year"], rel["month"], rel["total"]
    per_month = total / m
    if not 200_000 <= per_month <= 4_000_000:
        problems.append(f"average {per_month:,.0f}/month is outside the plausible range")
    if len(rel["countries"]) < 5:
        problems.append(f"only {len(rel['countries'])} countries parsed")
    if sum(v for v, _ in rel["countries"].values()) > total * 1.01:
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


def revalidate(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute the CHECK FAILED notes of every period from the current table."""
    df = df.copy()
    df["note"] = df["note"].fillna("").astype(str)
    for idx, row in df[df["country"] == "TOTAL"].iterrows():
        y, m = int(row["year"]), int(row["month"])
        rows = df[(df["year"] == y) & (df["month"] == m) & (df["country"] != "TOTAL")]
        rel = {"year": y, "month": m, "total": int(row["ytd"]),
               "countries": {r.country: (int(r.ytd), bool(r.exact)) for r in rows.itertuples()},
               "notes": [n for n in row["note"].split("; ") if n and "CHECK FAILED" not in n]}
        others = df[~((df["year"] == y) & (df["month"] == m))]
        problems = validate(rel, others)
        df.at[idx, "note"] = "; ".join(rel["notes"] + [f"CHECK FAILED: {p}" for p in problems])
    return df


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
        if "touris" not in low and "turist" not in low and "foreign" not in low:
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
        same = (df["year"] == rel["year"]) & (df["month"] == rel["month"])
        if same.any():
            # Several releases cover the same period: the national top-10 release, a by-gender
            # release (no countries), single-country releases (small totals)... The national
            # release always has the LARGEST total; among equal totals prefer more countries.
            old_total = int(df.loc[same & (df["country"] == "TOTAL"), "ytd"].iloc[0])
            old_n = int((same & (df["country"] != "TOTAL")).sum())
            if rel["total"] < old_total * 0.98:
                continue
            if rel["total"] <= old_total * 1.02 and len(rel["countries"]) <= old_n:
                continue
            df = df[~same]
            new_releases = [r for r in new_releases if (r["year"], r["month"]) != (rel["year"], rel["month"])]
        note = "; ".join(rel["notes"])
        rows = [(rel["year"], rel["month"], "TOTAL", rel["total"], rel["total_exact"], url, note)]
        rows += [(rel["year"], rel["month"], c, n, e, url, "") for c, (n, e) in rel["countries"].items()]
        df = pd.concat([df, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
        rel["url"] = url
        new_releases.append(rel)
        log.info("stat.uz: stored %s-%02d total=%s (%d countries)", rel["year"], rel["month"], rel["total"],
                 len(rel["countries"]))

    # Validate every stored period against its neighbours (a later release can change them).
    if new_releases:
        df = revalidate(df)
        problems = {(int(r.year), int(r.month)): r.note for r in df[df["country"] == "TOTAL"].itertuples()}
        for rel in new_releases:
            note = str(problems.get((rel["year"], rel["month"]), "") or "")
            rel["problems"] = [p.split("CHECK FAILED: ", 1)[1] for p in note.split("; ") if "CHECK FAILED" in p]
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
        return pd.DataFrame(columns=["year", "month", "country", "arrivals", "exact"])
    df = df[["year", "month", "country", "ytd", "exact"]].copy()
    df["exact"] = df["exact"].astype(str).str.lower().eq("true")
    prev = df.copy()
    prev["month"] = prev["month"] + 1
    merged = df.merge(prev, on=["year", "month", "country"], how="left", suffixes=("", "_prev"))
    merged.loc[merged["month"] == 1, "ytd_prev"] = 0
    merged = merged.dropna(subset=["ytd_prev"])
    merged.loc[merged["month"] == 1, "exact_prev"] = True
    merged["arrivals"] = (merged["ytd"] - merged["ytd_prev"]).astype(int)
    # exact only if both year-to-date figures were exact (not "2.8 million"-style rounding)
    merged["exact"] = merged["exact"] & merged["exact_prev"].astype(bool)
    # a negative month means the source revised its numbers or changed definitions
    merged = merged[merged["arrivals"] >= 0]
    return merged[["year", "month", "country", "arrivals", "exact"]].sort_values(["year", "month", "country"])


# ---------------------------------------------------------------- yearly, by country (SIAT)
YEARLY_CSV = config.DATA / "arrivals_yearly_by_country.csv"
SIAT_BY_COUNTRY = 1031   # "Distribution by country of foreign citizens arriving for tourist purposes"


def parse_siat_yearly(text: str) -> pd.DataFrame:
    """SIAT CSV (one row per country, one column per year) -> long table year,country,arrivals."""
    from io import StringIO
    raw = pd.read_csv(StringIO(text), dtype={"Code": str})
    years = [c for c in raw.columns if re.fullmatch(r"(19|20)\d\d", str(c))]
    raw["code"] = raw["Code"].astype(str).str.zfill(3).replace({"736": "729"})  # Sudan: old ISO code
    long = raw.melt(id_vars=["Klassifikator_en", "Klassifikator", "code"], value_vars=years,
                    var_name="year", value_name="arrivals")
    long["country"] = long["Klassifikator_en"].map(_norm_country)
    long["name_uz"] = long["Klassifikator"]
    long["year"] = long["year"].astype(int)
    long = long.dropna(subset=["arrivals"])
    long["arrivals"] = long["arrivals"].astype(float).round().astype(int)
    total = long.groupby("year", as_index=False)["arrivals"].sum().assign(country="TOTAL", code="", name_uz="Jami")
    cols = ["year", "country", "arrivals", "code", "name_uz"]
    return pd.concat([long[cols], total[cols]], ignore_index=True).sort_values(["year", "country"])


def collect_yearly(max_age_days: int = 7) -> pd.DataFrame | None:
    """Refresh yearly arrivals by country from SIAT (open data, CC BY 4.0) about once a week."""
    import json
    import time as _time
    if YEARLY_CSV.exists() and _time.time() - YEARLY_CSV.stat().st_mtime < max_age_days * 86400:
        return pd.read_csv(YEARLY_CSV)
    meta = http_get(f"https://api.siat.stat.uz/sdmx/{SIAT_BY_COUNTRY}/table/download/?download_format=csv", timeout=60)
    try:
        url = json.loads(meta)["file"]
    except Exception:  # noqa: BLE001
        log.warning("SIAT: unexpected answer for dataset %s", SIAT_BY_COUNTRY)
        return None
    text = http_get(url, timeout=60)
    if not text:
        return None
    df = parse_siat_yearly(text)
    # sanity: the national total must be in a plausible range for recent years
    recent = df[(df["country"] == "TOTAL") & (df["year"] >= 2022)]
    if recent.empty or not recent["arrivals"].between(1_000_000, 50_000_000).all():
        log.warning("SIAT: yearly totals look wrong, not saved")
        return None
    df.to_csv(YEARLY_CSV, index=False)
    log.info("SIAT: yearly arrivals by country saved (%d rows)", len(df))
    return df


def load_yearly() -> pd.DataFrame:
    if not YEARLY_CSV.exists():
        return pd.DataFrame(columns=["year", "country", "arrivals", "code", "name_uz"])
    return pd.read_csv(YEARLY_CSV, dtype={"code": str})
