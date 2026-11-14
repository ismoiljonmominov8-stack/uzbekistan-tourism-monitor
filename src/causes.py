"""Possible causes of an unusual jump or fall in one market's interest (Wikipedia views).

Instead of "cause not found", the daily post lists what could explain the change, strongest first:
  1. data checks (always, no AI): a known event near the date, which pages carry the change (one city or
     the whole country), whether other markets moved the same day (global vs local cause), whether it is
     the first day or a continuing change, and what the language edition really covers (ru = all Russian
     readers, not only Russia);
  2. news the system already recorded for that market in the last 3 days — shown as "same time", which
     is not proof of cause;
  3. optional web search (Gemini with Google Search): news from the last days that could explain it.
     Only links that Google itself returned are kept; the rest is dropped. Labelled "not verified".
"""
from __future__ import annotations

import json
import os
from urllib.parse import urlparse

import pandas as pd

from . import config
from .util import http_post_json, log

EVENTS = config.DATA / "events.csv"
PREDICTIONS = config.DATA / "predictions.csv"
LANG_NOTE = {
    "uz": {
        "ru": "Rus tilidagi Vikipediya: Rossiya bilan birga Qozog'iston, Qirg'iziston, O'zbekistonning o'zi va boshqa "
              "rusiyzabon o'quvchilar ham kiradi — o'sish faqat Rossiyadan bo'lmasligi mumkin",
        "en": "Ingliz tilidagi Vikipediya butun dunyodan o'qiladi — o'sish bitta mamlakatga tegishli bo'lmasligi mumkin",
    },
    "en": {
        "ru": "Russian-language Wikipedia: readers in Kazakhstan, Kyrgyzstan, Uzbekistan itself and other Russian "
              "speakers count too — the change may not come from Russia alone",
        "en": "English Wikipedia is read worldwide — the change may not belong to one country",
    },
}
W = {
    "uz": {
        "event": "Ma'lum voqea: {title} ({when})",
        "today": "shu kuni", "days_before": "{n} kun oldin", "days_after": "{n} kundan keyin",
        "focus": "O'zgarish asosan «{article}» sahifasida ({share:.0%}) — shu shahar haqidagi ko'rsatuv, maqola, video "
                 "yoki post bo'lishi mumkin",
        "focus_country": "O'zgarish asosan «{article}» sahifasida ({share:.0%}) — mamlakat haqidagi umumiy yangilik, "
                         "ko'rsatuv yoki xabar bo'lishi mumkin",
        "focus_two": "O'zgarish asosan ikki sahifada: «{a}» ({sa:.0%}) va «{b}» ({sb:.0%}) — «{a}» haqidagi ko'rsatuv, "
                     "maqola yoki video bo'lishi mumkin",
        "broad": "O'zgarish barcha sahifalarda ({pages}) — O'zbekiston haqidagi umumiy yangilik yoki xabar bo'lishi mumkin",
        "global": "Shu kuni yana {n} ta bozorda xuddi shunday o'zgarish ({names}) — umumiy sabab: xalqaro yangilik yoki "
                  "Vikipediya bosh sahifasi",
        "local": "Boshqa bozorlarda bunday o'zgarish yo'q — sabab shu til yoki mamlakatga tegishli",
        "second": "{n}-kun ketma-ket — tasodif emas, davomli o'zgarish",
        "first": "Birinchi kun — davom etadimi, keyingi kunlar ko'rsatadi",
        "news": "Shu vaqtdagi yangilik: {headline} ({source}) — bir vaqtda bo'lgani sabab ekanini isbotlamaydi",
    },
    "en": {
        "event": "Known event: {title} ({when})",
        "today": "same day", "days_before": "{n} days before", "days_after": "in {n} days",
        "focus": "The change is mostly on the «{article}» page ({share:.0%}) — a TV show, article, video or post about "
                 "that city is likely",
        "focus_country": "The change is mostly on the «{article}» page ({share:.0%}) — general news, a show or a report "
                         "about the country is likely",
        "focus_two": "The change is mostly on two pages: «{a}» ({sa:.0%}) and «{b}» ({sb:.0%}) — a show, article or "
                     "video about «{a}» is likely",
        "broad": "The change is on every page ({pages}) — general news about Uzbekistan is likely",
        "global": "{n} more markets moved the same way that day ({names}) — a shared cause: international news or the "
                  "Wikipedia main page",
        "local": "No other market moved like this — the cause belongs to this language or country",
        "second": "Day {n} in a row — not chance, a continuing change",
        "first": "First day — the next days will show whether it lasts",
        "news": "News at the same time: {headline} ({source}) — happening together does not prove it is the cause",
    },
}


def _w(key):
    return W.get(config.POST_LANG, W["en"])[key]


def _article_split(df: pd.DataFrame, lang: str, day: pd.Timestamp):
    d = df[df["lang"] == lang].copy()
    d["date"] = pd.to_datetime(d["date"])
    today = d[d["date"] == day].groupby("article")["views"].sum()
    base = d[(d["date"] < day) & (d["date"] >= day - pd.Timedelta(days=config.BASELINE_DAYS))]
    med = base.groupby(["article", "date"])["views"].sum().groupby("article").median()
    return today, med


def data_causes(df: pd.DataFrame, wide: pd.DataFrame, day, m: dict, movers: list[dict]) -> list[dict]:
    """m: one entry of pageviews.movers(). Returns [{"text", "strength"}], strongest first."""
    day = pd.Timestamp(day)
    lang, up = m["lang"], m["change"] > 0
    out = []
    # 1. known events for this market close to the date
    if EVENTS.exists():
        ev = pd.read_csv(EVENTS)
        ev["d"] = pd.to_datetime(ev["date"], errors="coerce")
        ev = ev[ev["markets"].fillna("").str.split("|").apply(lambda xs: lang in xs or "all" in xs)]
        near = ev[(ev["d"] >= day - pd.Timedelta(days=7)) & (ev["d"] <= day + pd.Timedelta(days=1))]
        for _, e in near.sort_values("d", ascending=False).head(2).iterrows():
            n = (day - e["d"]).days
            when = _w("today") if n == 0 else _w("days_before").format(n=n) if n > 0 else _w("days_after").format(n=-n)
            out.append({"text": _w("event").format(title=str(e["title"]).strip(), when=when),
                        "strength": "strong" if 0 <= n <= 2 else "possible"})
    # 2. which pages carry the change
    today, med = _article_split(df, lang, day)
    diff = (today - med).dropna()
    total = diff.sum()
    if total and (total > 0) == up:
        share = (diff / total).sort_values(ascending=False)
        top = share.index[0]
        if share.iloc[0] >= 0.6:
            key = "focus_country" if top == "Uzbekistan" else "focus"
            out.append({"text": _w(key).format(article=top, share=share.iloc[0]), "strength": "possible"})
        elif len(share) > 1 and share.iloc[0] + share.iloc[1] >= 0.8:
            a, b = share.index[0], share.index[1]
            if a == "Uzbekistan":   # name the city, the country page follows any city story
                a, b = b, a
            out.append({"text": _w("focus_two").format(a=a, sa=share[a], b=b, sb=share[b]), "strength": "possible"})
        else:
            pct = (today / med - 1).dropna().sort_values(ascending=not up)
            pages = ", ".join(f"{a} {v:+.0%}" for a, v in pct.head(3).items())
            out.append({"text": _w("broad").format(pages=pages), "strength": "possible"})
    # 3. other markets the same day
    same = [x for x in movers if x["lang"] != lang and x["unusual"] and (x["change"] > 0) == up]
    if len(same) >= 2:
        from .texts import market_name
        out.append({"text": _w("global").format(n=len(same), names=", ".join(market_name(x["lang"]) for x in same[:4])),
                    "strength": "possible"})
    else:
        out.append({"text": _w("local"), "strength": "info"})
    # 4. first day or continuing
    run = 1
    from . import pageviews
    for k in range(1, 4):
        prev = [x for x in pageviews.movers(wide, day - pd.Timedelta(days=k)) if x["lang"] == lang]
        if prev and prev[0]["unusual"] and (prev[0]["change"] > 0) == up:
            run += 1
        else:
            break
    out.append({"text": _w("second").format(n=run) if run > 1 else _w("first"), "strength": "info"})
    # 5. what the language edition covers
    note = LANG_NOTE.get(config.POST_LANG, LANG_NOTE["en"]).get(lang)
    if note:
        out.append({"text": note, "strength": "info"})
    # 6. news recorded for this market in the last 3 days
    if PREDICTIONS.exists():
        p = pd.read_csv(PREDICTIONS)
        p["d"] = pd.to_datetime(p["date"], errors="coerce")
        # only news tagged for THIS market; "All markets" news is too general to point at one market's jump
        names = {config.MARKETS[lang]["en"], *config.MARKETS[lang].get("stat_names", [])}
        hit = p[(p["d"] >= day - pd.Timedelta(days=3)) & (p["d"] <= day + pd.Timedelta(days=1))
                & p["markets"].fillna("").apply(lambda s: bool(names & {x.strip() for x in s.split(",")}))]
        for _, r in hit.drop_duplicates("headline").head(2).iterrows():
            out.append({"text": _w("news").format(headline=r["headline"], source=r.get("source", "")),
                        "strength": "weak"})
    order = {"strong": 0, "possible": 1, "weak": 2, "info": 3}
    return sorted(out, key=lambda c: order[c["strength"]])


SEARCH_PROMPT = """Find news that could explain why interest in Uzbekistan among {audience} readers changed
by {change:+.0%} on {date} (views of Wikipedia pages about Uzbekistan in {language}; the change was mostly on:
{pages}). Search news from {start} to {date}: TV shows or documentaries, viral videos, travel articles, flights,
visas, sport matches, concerts, political or international news, holidays — anything about Uzbekistan or
its cities that {audience} readers would have seen.

Return only JSON: {{"items": [{{"headline": "...", "why": "...", "url": "...", "date": "YYYY-MM-DD"}}]}}
- at most 3 items, most likely first; "headline" and "why" in {out_lang}, one short sentence each
- only items you actually found in the search results, with their real URL; do not guess
- if nothing plausible was published in that period, return {{"items": []}}"""


def search_causes(m: dict, day, pages: str) -> list[dict]:
    """Gemini with Google Search. Keeps only items whose link's site is among the sources Google returned."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return []
    day = pd.Timestamp(day)
    lang = m["lang"]
    language = {"ru": "Russian", "en": "English", "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "de": "German",
                "tr": "Turkish", "it": "Italian", "fr": "French", "hi": "Hindi"}.get(lang, lang)
    audience = {"ru": "Russian-speaking", "en": "English-speaking"}.get(lang, config.MARKETS[lang]["en"])
    prompt = SEARCH_PROMPT.format(audience=audience, change=m["change"], date=day.date(), language=language,
                                  pages=pages, start=(day - pd.Timedelta(days=3)).date(),
                                  out_lang="Uzbek (Latin script)" if config.POST_LANG == "uz" else "English")
    model = os.getenv("GEMINI_SEARCH_MODEL", config.GEMINI_SEARCH_MODEL)
    try:
        data = http_post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}],
             "generationConfig": {"temperature": 0.2}},
            headers={"x-goog-api-key": key})
        cand = data["candidates"][0]
        text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        chunks = (cand.get("groundingMetadata") or {}).get("groundingChunks") or []
        sites = {(c.get("web") or {}).get("title", "").lower().removeprefix("www.") for c in chunks}
        from .ai import _extract_json
        items = _extract_json(text).get("items", [])
    except Exception as e:  # noqa: BLE001 — optional: the post goes out without it
        log.warning("causes: web search failed: %s", e)
        return []
    out = []
    for it in items[:3]:
        url = str(it.get("url", ""))
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if any(ch in url for ch in "\"<> '"):
            continue
        if not url.startswith("http") or not host or not any(s and (host == s or host.endswith("." + s) or s in host)
                                                               for s in sites):
            continue  # not among the pages Google actually returned: drop it
        out.append({"headline": str(it.get("headline", ""))[:200], "why": str(it.get("why", ""))[:240],
                    "url": url, "date": str(it.get("date", ""))[:10]})
    return out


def pages_text(df: pd.DataFrame, lang: str, day) -> str:
    today, med = _article_split(df, lang, pd.Timestamp(day))
    pct = (today / med - 1).dropna().sort_values(ascending=False)
    return ", ".join(f"{a} {v:+.0%}" for a, v in pct.head(3).items()) or "—"


if __name__ == "__main__":
    from . import pageviews
    df = pageviews.load()
    wide = pageviews.market_daily(df)
    day = wide.index.max()
    mv = pageviews.movers(wide, day)
    for m in [x for x in mv if x["unusual"]]:
        print(m["lang"], json.dumps(data_causes(df, wide, day, m, mv), ensure_ascii=False, indent=1))
