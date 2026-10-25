"""One-off: add past monthly releases (saved texts in reports/statuz_archive/raw) to data/arrivals_ytd.csv.

Same rules as the daily collector: only inbound-tourism releases, the national release of a period is
the one with the LARGEST total (single-country and by-gender releases have smaller totals), and every
period is validated against its neighbours. Periods already in the table are never overwritten.
A year is kept only if its December year-to-date figure (when present) is within 3% of the official
SIAT yearly total; otherwise the whole year is dropped, so one misread release cannot bend the series.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import statuz

RAW = Path("reports/statuz_archive/raw")
YEARS = range(2022, 2025)   # 2020-21: only scattered COVID-period releases
# releases about one purpose (relatives, treatment...) or one country/group are not the national total
PART = re.compile(r"relatives|leisure|recreation|treatment|medical|commercial|business|stud(y|ying)|education|official"
                  r"|\bfrom\b|citizens of (?!the Republic of Uzbekistan)|Shanghai|\bSCO\b|member"
                  r"|Chinese|German|Indian|French|Italian|Japanese|Korean|Russian|Kazakh|Kyrgyz|Tajik|Turkish|American|British|Spanish",
                  re.I)
TABLE_HEAD = re.compile(r"\(?January\s*[-–—]\s*([A-Za-z]+)\)?")
TABLE_ROW = re.compile(r"^(20\d\d)\s*[-–—]\s*([\d.,]+)\s*(million|thousand)", re.M)
TOLERANCE = 0.03


def releases() -> list[dict]:
    found = []
    for f in sorted(RAW.glob("*.txt"), key=lambda p: int(p.stem)):
        text = f.read_text(encoding="utf-8")
        url = re.search(r"^URL: (.+)$", text, re.M).group(1)
        title = re.search(r"^TITLE: (.*)$", text, re.M).group(1)
        if not statuz.is_inbound(title, text) or PART.search(title):
            continue
        rel = statuz.parse_release(text)
        if rel and rel["year"] in YEARS:
            rel["url"], rel["id"], rel["title"] = url, int(f.stem), title
            found.append(rel)
        found += table_rows(text, url, int(f.stem), title)
    return found


def table_rows(text: str, url: str, nid: int, title: str) -> list[dict]:
    """'The number ... (January-September):  2022 - 3.6 million people; 2023 - 4.9 million ...'"""
    head = TABLE_HEAD.search(text)
    rows = TABLE_ROW.findall(text)
    if not head or len(rows) < 3 or head.group(1).lower() not in statuz.MONTHS:
        return []
    month = statuz.MONTHS.index(head.group(1).lower()) + 1
    out = []
    for y, num, unit in rows:
        if int(y) in YEARS:
            total, _ = statuz.amount(num, unit)
            out.append({"year": int(y), "month": month, "total": total, "total_exact": False, "countries": {},
                        "notes": ["from a comparison table (rounded)"], "table": True, "url": url, "id": nid, "title": title})
    return out


def _zeros(n: int) -> int:
    """Trailing zeros: 5,200,000 -> 5 (rounded to 0.1 million), 5,232,800 -> 2 (more precise)."""
    z = 0
    while n and n % 10 == 0:
        n //= 10
        z += 1
    return z


def pick(found: list[dict]) -> dict[tuple[int, int], dict]:
    best = {}
    direct = {(r["year"], r["month"]) for r in found if not r.get("table")}
    for r in found:
        if r.get("table") and (r["year"], r["month"]) in direct:
            continue  # a rounded table value only fills a month that has no release of its own
        k = (r["year"], r["month"])
        b = best.get(k)
        if b is None or r["total"] > b["total"] * 1.02:
            best[k] = dict(r)
            continue
        if r["total"] < b["total"] * 0.98:
            continue
        # same period, same total within 2%: keep the exact total and the longest country list
        merged = dict(b)
        if (r["total_exact"], -_zeros(r["total"])) > (b["total_exact"], -_zeros(b["total"])):
            merged.update(total=r["total"], total_exact=r["total_exact"], url=r["url"], id=r["id"])
        if len(r["countries"]) > len(b["countries"]):
            merged["countries"] = r["countries"]
        best[k] = merged
    return best


def run(write: bool = True) -> dict:
    df = statuz.load()
    have = {(int(r.year), int(r.month)) for r in df[df["country"] == "TOTAL"].itertuples()}
    best = {k: v for k, v in pick(releases()).items() if k not in have}
    yearly = statuz.load_yearly()
    official = {int(r.year): int(r.arrivals) for r in yearly[yearly["country"] == "TOTAL"].itertuples()}

    report = {"added": [], "dropped_years": {}}
    for y in sorted({k[0] for k in best}):
        dec = best.get((y, 12))
        if dec and y in official:
            diff = dec["total"] / official[y] - 1
            if abs(diff) > TOLERANCE:
                report["dropped_years"][y] = f"December {dec['total']:,} vs SIAT {official[y]:,} ({diff:+.1%})"
                best = {k: v for k, v in best.items() if k[0] != y}

    rows = []
    for (y, m), r in sorted(best.items()):
        note = "; ".join(r["notes"] + ["backfilled from archive"])
        rows.append((y, m, "TOTAL", r["total"], r["total_exact"], r["url"], note))
        rows += [(y, m, c, n, e, r["url"], "") for c, (n, e) in r["countries"].items()]
        report["added"].append((y, m, r["total"], len(r["countries"]), r["id"]))
    if rows:
        df = pd.concat([df, pd.DataFrame(rows, columns=statuz.COLUMNS)], ignore_index=True)
        df = statuz.revalidate(df).sort_values(["year", "month", "country"])
        report["check_failed"] = [(int(r.year), int(r.month), r.note) for r in df[df["country"] == "TOTAL"].itertuples()
                                  if "CHECK FAILED" in str(r.note) and int(r.year) < 2025]
        if write:
            df.to_csv(statuz.CSV, index=False)
    return report


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(run(write="--write" in sys.argv), indent=1, default=str))
