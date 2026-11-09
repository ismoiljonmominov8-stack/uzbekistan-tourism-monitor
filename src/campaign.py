"""Campaign test results: reads the counts from the Cloudflare worker (GET /stats) every day and compares
version A (inspiration) with version B (practical).

Measures, per version: views, engaged readers (half the page or 30 s), clicks on "Plan your trip" (main goal),
on entry rules and on train tickets. Main comparison: share of views that clicked "Plan your trip", U.S.
visitors only (the target market), with a two-proportion z-test. Until each version has MIN_VIEWS U.S. views
the result is reported as "too early".
The worker address is read from docs/visit/track.js (window.TRACK_URL), the same file the pages use.
"""
from __future__ import annotations

import math
import re

import pandas as pd

from . import config
from .util import http_get, log

TRACK_JS = config.ROOT / "docs" / "visit" / "track.js"
OUT = config.DATA / "campaign_hits.csv"
MIN_VIEWS = 100
EVENTS = ["view", "engaged", "cta_plan", "cta_rules", "cta_route"]


def worker_url() -> str:
    if not TRACK_JS.exists():
        return ""
    m = re.search(r'TRACK_URL\s*=\s*"([^"]*)"', TRACK_JS.read_text(encoding="utf-8"))
    return (m.group(1) if m else "").rstrip("/")


def collect() -> int:
    url = worker_url()
    if not url:
        log.info("campaign: counting not configured (docs/visit/track.js is empty)")
        return 0
    data = http_get(url + "/stats", as_json=True)
    if not data or "rows" not in data:
        log.warning("campaign: no answer from %s/stats", url)
        return 0
    df = pd.DataFrame(data["rows"], columns=["day", "v", "e", "country", "src", "n"])
    df.to_csv(OUT, index=False)
    log.info("campaign: %d count rows saved", len(df))
    return len(df)


def load() -> pd.DataFrame:
    return pd.read_csv(OUT, keep_default_na=False) if OUT.exists() else pd.DataFrame(columns=["day", "v", "e", "country", "src", "n"])


def ztest(k1: int, n1: int, k2: int, n2: int) -> float | None:
    """Two-sided p-value for 'the two click rates are equal'."""
    if min(n1, n2) == 0:
        return None
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def summary(df: pd.DataFrame | None = None, country: str | None = "US") -> dict:
    df = load() if df is None else df
    if df.empty:
        return {"rows": [], "verdict": "no_data", "p": None, "days": 0}
    d = df if country is None else df[df["country"] == country]
    t = d.pivot_table(index="v", columns="e", values="n", aggfunc="sum", fill_value=0).reindex(index=["a", "b"], columns=EVENTS, fill_value=0)
    rows = []
    for v, r in t.iterrows():
        views = int(r["view"])
        rows.append({"v": v, **{e: int(r[e]) for e in EVENTS},
                     "engaged_rate": r["engaged"] / views if views else None, "plan_rate": r["cta_plan"] / views if views else None})
    a, b = rows
    p = ztest(a["cta_plan"], a["view"], b["cta_plan"], b["view"])
    if min(a["view"], b["view"]) < MIN_VIEWS:
        verdict = "too_early"
    elif p is not None and p < 0.05:
        verdict = "a_wins" if a["plan_rate"] > b["plan_rate"] else "b_wins"
    else:
        verdict = "no_difference"
    return {"rows": rows, "p": p, "verdict": verdict, "days": int(df["day"].nunique()),
            "first": df["day"].min(), "last": df["day"].max(), "country": country,
            "by_source": df.groupby(["src"])["n"].sum().to_dict() if not df.empty else {}}


COUNTRY_UZ = {"US": "AQSh", "UZ": "O'zbekiston", "GB": "Buyuk Britaniya", "RU": "Rossiya", "KZ": "Qozog'iston",
              "KG": "Qirg'iziston", "TJ": "Tojikiston", "DE": "Germaniya", "FR": "Fransiya", "IT": "Italiya",
              "JP": "Yaponiya", "KR": "Janubiy Koreya", "CN": "Xitoy", "IN": "Hindiston", "TR": "Turkiya",
              "CA": "Kanada", "AU": "Avstraliya", "XX": "noma'lum"}
SOURCE_UZ = {"direct": "to'g'ridan-to'g'ri", "other": "boshqa"}


def _flag(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code) if len(code) == 2 and code.isalpha() and code != "XX" else "🌐"


def _country(code: str) -> str:
    return f"{_flag(code)} {COUNTRY_UZ.get(code, code)}"


def bot_text(refresh: bool = True, today: str | None = None) -> str:
    """Bot reply for the "site visits" button: today, the last 7 days, totals for A and B, countries, sources
    and the U.S. verdict. Fetches fresh counts from the worker first (falls back to the saved file)."""
    from datetime import date, timedelta
    if not worker_url():
        return "📈 Sahifalarga tashriflarni hisoblash hali yoqilmagan (docs/visit/track.js bo'sh)."
    if refresh:
        try:
            collect()
        except Exception as e:  # noqa: BLE001 — show the saved counts instead
            log.warning("campaign: refresh failed: %s", e)
    df = load()
    if df.empty:
        return ("📈 <b>Sahifalarga tashriflar</b>\n\nHozircha birorta tashrif yo'q. Havolalar:\n"
                "A — …/visit/a.html\nB — …/visit/b.html")
    df = df.copy()
    df["n"] = df["n"].astype(int)
    today = today or date.today().isoformat()
    n = lambda d, e: int(d.loc[d["e"] == e, "n"].sum())  # noqa: E731
    fmt = lambda x: f"{x:,}".replace(",", " ")  # noqa: E731
    lines = ["📈 <b>Sahifalarga tashriflar</b> (A — ilhom, B — amaliy)"]

    t = df[df["day"] == today]
    lines.append(f"\n<b>Bugun ({today[8:10]}.{today[5:7]})</b>: 👁 {fmt(n(t, 'view'))} ko'rish · "
                 f"📖 {fmt(n(t, 'engaged'))} o'qigan · 🧭 {fmt(n(t, 'cta_plan'))} «Plan your trip»")

    lines.append("\n<b>Oxirgi 7 kun</b> (ko'rish / o'qigan / «Plan»):")
    d0 = date.fromisoformat(today)
    for k in range(6, -1, -1):
        d = (d0 - timedelta(days=k)).isoformat()
        x = df[df["day"] == d]
        lines.append(f"{d[8:10]}.{d[5:7]} — {fmt(n(x, 'view'))} / {fmt(n(x, 'engaged'))} / {fmt(n(x, 'cta_plan'))}")

    first = df["day"].min()
    lines.append(f"\n<b>Jami</b> ({first[8:10]}.{first[5:7]} dan beri):")
    for v, name in (("a", "A ilhom"), ("b", "B amaliy")):
        x = df[df["v"] == v]
        views = n(x, "view")
        rate = f" ({n(x, 'cta_plan') / views:.0%})" if views else ""
        lines.append(f"<b>{name}</b>: 👁 {fmt(views)} · 📖 {fmt(n(x, 'engaged'))} · 🧭 {fmt(n(x, 'cta_plan'))}{rate} · "
                     f"kirish qoidalari {fmt(n(x, 'cta_rules'))} · poyezd {fmt(n(x, 'cta_route'))}")

    views = df[df["e"] == "view"]
    by_c = views.groupby("country")["n"].sum().sort_values(ascending=False)
    if len(by_c):
        lines.append("\n<b>Davlatlar</b> (ko'rish): " + ", ".join(f"{_country(c)} {fmt(int(k))}" for c, k in by_c.head(6).items())
                     + (f", yana {len(by_c) - 6} ta" if len(by_c) > 6 else ""))
    by_s = views.groupby("src")["n"].sum().sort_values(ascending=False)
    if len(by_s):
        lines.append("<b>Qayerdan kelgan</b>: " + ", ".join(f"{SOURCE_UZ.get(s, s)} {fmt(int(k))}" for s, k in by_s.items()))

    us = summary(df, "US")
    a, b = us["rows"]
    verdict = {"too_early": f"hali erta — har bir versiyada kamida {MIN_VIEWS} ta AQSh ko'rishi kerak "
                            f"(hozir A: {a['view']}, B: {b['view']})",
               "no_difference": "A va B o'rtasida ishonchli farq yo'q",
               "a_wins": "A (ilhom) ishonchli darajada ko'proq bosish olgan — gipoteza tasdiqlandi",
               "b_wins": "B (amaliy) ishonchli darajada ko'proq bosish olgan — gipoteza tasdiqlanmadi",
               "no_data": "ma'lumot yo'q"}[us["verdict"]]
    if us["verdict"] in ("no_difference", "a_wins", "b_wins") and us["p"] is not None:
        verdict += " (p < 0,001)" if us["p"] < 0.001 else f" (p = {us['p']:.3f})".replace(".", ",")
    lines.append(f"\n🇺🇸 <b>AQSh sinovi</b>: {verdict}.")
    lines.append("\n<i>Faqat sonlar saqlanadi: ism, IP-manzil va cookie yo'q. Bot va qidiruv robotlari hisobga olinmaydi.</i>")
    return "\n".join(lines)


if __name__ == "__main__":
    collect()
    print(summary())
    print(summary(country=None))
