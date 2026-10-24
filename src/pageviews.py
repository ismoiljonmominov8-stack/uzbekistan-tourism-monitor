"""Collector 1: daily Wikipedia pageviews of Uzbekistan articles, per language (= per market)."""
from datetime import date, datetime, timedelta
from urllib.parse import quote

import pandas as pd

from . import config
from .util import http_get, log, read_json, write_json

CSV = config.DATA / "pageviews_daily.csv"
TITLES = config.DATA / "titles.json"
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def resolve_titles() -> dict:
    """{lang: {en_title: local_title}} via English Wikipedia langlinks. Cached in data/titles.json."""
    cached = read_json(TITLES, {})
    missing = [a for a in config.ARTICLES_EN if any(a not in cached.get(l, {}) for l in config.MARKETS)]
    if not missing:
        return cached
    for article in missing:
        data = http_get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": article, "prop": "langlinks", "lllimit": "500",
                    "format": "json", "redirects": "1"},
            as_json=True,
        )
        links = {}
        if data:
            for page in data.get("query", {}).get("pages", {}).values():
                for ll in page.get("langlinks", []):
                    links[ll["lang"]] = ll["*"]
        for lang in config.MARKETS:
            title = article if lang == "en" else links.get(lang)
            if title:
                cached.setdefault(lang, {})[article] = title
            else:
                log.warning("No %s title for %s", lang, article)
    write_json(TITLES, cached)
    return cached


def _fetch(lang, title, start: date, end: date):
    url = (f"{API}/{lang}.wikipedia/all-access/user/"
           f"{quote(title.replace(' ', '_'), safe='')}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00")
    data = http_get(url, as_json=True)
    if not data:
        return []
    return [(datetime.strptime(i["timestamp"][:8], "%Y%m%d").date(), i["views"]) for i in data.get("items", [])]


def load() -> pd.DataFrame:
    if CSV.exists():
        df = pd.read_csv(CSV, parse_dates=["date"])
        df["date"] = df["date"].dt.date
        return df
    return pd.DataFrame(columns=["date", "lang", "article", "views"])


def collect() -> pd.DataFrame:
    """Fetch everything new since the last stored day. First run backfills from PAGEVIEWS_START."""
    titles = resolve_titles()
    df = load()
    yesterday = date.today() - timedelta(days=1)
    rows = []
    for lang in config.MARKETS:
        for article, title in titles.get(lang, {}).items():
            have = df[(df["lang"] == lang) & (df["article"] == article)]
            start = (max(have["date"]) + timedelta(days=1)) if len(have) else date.fromisoformat(config.PAGEVIEWS_START)
            if start > yesterday:
                continue
            got = _fetch(lang, title, start, yesterday)
            rows += [(d, lang, article, v) for d, v in got]
            log.info("pageviews %s/%s: +%d days", lang, article, len(got))
    if rows:
        new = pd.DataFrame(rows, columns=["date", "lang", "article", "views"])
        df = pd.concat([df, new], ignore_index=True)
        df = df.drop_duplicates(["date", "lang", "article"], keep="last").sort_values(["date", "lang", "article"])
        config.DATA.mkdir(exist_ok=True)
        df.to_csv(CSV, index=False)
    return df


def market_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Wide table: rows = date, columns = lang, values = total views of all tracked articles."""
    if df.empty:
        return pd.DataFrame()
    wide = df.groupby(["date", "lang"])["views"].sum().unstack("lang").sort_index()
    wide.index = pd.to_datetime(wide.index)
    return wide


def movers(wide: pd.DataFrame, day=None) -> list[dict]:
    """Change of `day` (default: last day) vs the average of the BASELINE_DAYS before it."""
    if wide.empty:
        return []
    day = pd.Timestamp(day) if day is not None else wide.index.max()
    base = wide.loc[day - pd.Timedelta(days=config.BASELINE_DAYS): day - pd.Timedelta(days=1)]
    if day not in wide.index or len(base) < 7:
        return []
    out = []
    for lang in wide.columns:
        # MEDIAN, not mean: one freak day (e.g. 18,041 Japanese views on 30 Sep 2026, ~14x normal)
        # would otherwise inflate the baseline for a month and make normal days look like crashes.
        series = base[lang].dropna()
        today_v, med = wide.at[day, lang], series.median()
        if pd.isna(today_v) or pd.isna(med) or med < 20:  # too few views to say anything
            continue
        # "unusual" = outside the normal day-to-day range: more than 3 robust standard deviations
        # (1.4826 x median absolute deviation) from the median. Small markets are noisy, so a fixed
        # ±30 % rule would flag them almost daily.
        mad = (series - med).abs().median() * 1.4826
        z = (today_v - med) / mad if mad > 0 else 0.0
        out.append({"lang": lang, "views": int(today_v), "avg": float(med), "change": today_v / med - 1,
                    "z": float(z), "unusual": abs(z) >= 3 and abs(today_v / med - 1) >= 0.15})
    return sorted(out, key=lambda m: abs(m["change"]), reverse=True)


def most_viewed_article(df: pd.DataFrame, day) -> str | None:
    d = df[df["date"] == pd.Timestamp(day).date()]
    if d.empty:
        return None
    return d.groupby("article")["views"].sum().idxmax()


def trend_7d(wide: pd.DataFrame) -> tuple[int, int]:
    """(markets rising, markets total): last 7 days average vs the 7 days before."""
    if len(wide) < 14:
        return 0, 0
    last, prev = wide.iloc[-7:].mean(), wide.iloc[-14:-7].mean()
    valid = [l for l in wide.columns if prev.get(l, 0) >= 20]
    return sum(1 for l in valid if last[l] > prev[l]), len(valid)
