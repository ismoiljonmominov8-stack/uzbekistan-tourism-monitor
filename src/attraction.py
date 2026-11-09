"""Attraction map: for each market, where to send information and what kind.

Combines four measured things per market (no AI, fixed rules, so every recommendation can be traced):
  1. leisure segment   — leisure trips 2025 = arrivals 2025 x leisure share (purpose.py)
  2. headroom          — distant markets: leisure trips per 1000 adults who can afford a 5-day trip (affordability.py),
                         compared with the typical (median) rate of the distant markets; headroom = extra leisure trips
                         a year if the market reached the typical rate.
                         neighbours: extra leisure trips if their leisure share rose to the best neighbour's share
                         (turning some visiting-relatives trips into leisure trips).
  3. awareness         — Google search share among 5 Central Asian/Caucasus destinations (trends.py; 20% = parity)
  4. momentum          — arrivals 2025 vs 2024
Rules -> priority group and message type:
  A  "Katta imkoniyat"  headroom >= 5 000 leisure trips a year
       awareness < 25%  -> inspiration (Uzbekistan is not on their radar)
       awareness >= 25% -> practical (they know it, something stops them: flights, price, visa, planning)
  B  "Kuchli bozor"     at/above the typical rate and >= 20 000 leisure trips -> broaden (new places, repeat visits)
  C  "Konversiya"       neighbours with large headroom -> short leisure trips for people who already come
  D  "Kuzatish"         small or no headroom
Channels are general knowledge about each country's main platforms, not measured here.
"""
from __future__ import annotations

import pandas as pd

from . import config, purpose, statuz, trends

OUT = config.DATA / "attraction.csv"
AFF = config.DATA / "affordability.csv"
MIN_HEADROOM = 5000
STRONG = 20000
NEAR = {"KAZ", "KGZ", "TJK", "TKM", "AFG"}
EN = {"USA": "United States", "CHN": "China", "DEU": "Germany", "IND": "India", "JPN": "Japan", "GBR": "United Kingdom",
      "FRA": "France", "ITA": "Italy", "RUS": "Russia", "KOR": "Republic of Korea", "TUR": "Türkiye",
      "KAZ": "Kazakhstan", "KGZ": "Kyrgyzstan", "TJK": "Tajikistan", "TKM": "Turkmenistan", "AFG": "Afghanistan"}
NUM = {"USA": "840", "CHN": "156", "DEU": "276", "IND": "356", "JPN": "392", "GBR": "826", "FRA": "250", "ITA": "380",
       "RUS": "643", "KOR": "410", "TUR": "792", "KAZ": "398", "KGZ": "417", "TJK": "762", "TKM": "795", "AFG": "004"}
GEO = {"USA": "US", "CHN": "CN", "DEU": "DE", "IND": "IN", "JPN": "JP", "GBR": "GB", "FRA": "FR", "ITA": "IT",
       "RUS": "RU", "KOR": "KR", "TUR": "TR", "KAZ": "KZ"}
CHANNELS = {
    "USA": "Instagram, YouTube, Google qidiruv, sayohat bloglari (ingliz tili)",
    "GBR": "Instagram, YouTube, Google qidiruv, sayohat jurnallari (ingliz tili)",
    "DEU": "Instagram, YouTube, Google qidiruv, turoperatorlar (nemis tili)",
    "FRA": "Instagram, YouTube, Google qidiruv, turoperatorlar (fransuz tili)",
    "ITA": "Instagram, YouTube, Google qidiruv, turoperatorlar (italyan tili)",
    "JPN": "X (Twitter), Instagram, LINE, YouTube (yapon tili)",
    "KOR": "Naver, KakaoTalk, YouTube, Instagram (koreys tili)",
    "CHN": "WeChat, Douyin, Xiaohongshu — Google va Instagram bloklangan (xitoy tili)",
    "IND": "Instagram, YouTube, WhatsApp (ingliz va hind tili)",
    "TUR": "Instagram, YouTube (turk tili)",
    "RUS": "Telegram, VK, YouTube (rus tili)",
    "KAZ": "Telegram, Instagram (qozoq va rus tili)",
    "KGZ": "Telegram, Instagram (qirg'iz va rus tili)",
    "TJK": "Telegram, Instagram (tojik va rus tili)",
    "TKM": "Internet cheklangan — qarindoshlar, turoperatorlar, chegara punktlari",
    "AFG": "—",
}
# same recommendations in Russian and English (the page has a UZ / RU / EN switch)
CHANNELS_I18N = {
    "ru": {"USA": "Instagram, YouTube, поиск Google, тревел-блоги (англ.)", "GBR": "Instagram, YouTube, поиск Google, тревел-журналы (англ.)",
           "DEU": "Instagram, YouTube, поиск Google, туроператоры (нем.)", "FRA": "Instagram, YouTube, поиск Google, туроператоры (франц.)",
           "ITA": "Instagram, YouTube, поиск Google, туроператоры (итал.)", "JPN": "X (Twitter), Instagram, LINE, YouTube (япон.)",
           "KOR": "Naver, KakaoTalk, YouTube, Instagram (корейск.)", "CHN": "WeChat, Douyin, Xiaohongshu — Google и Instagram заблокированы (кит.)",
           "IND": "Instagram, YouTube, WhatsApp (англ. и хинди)", "TUR": "Instagram, YouTube (турецк.)", "RUS": "Telegram, VK, YouTube (рус.)",
           "KAZ": "Telegram, Instagram (казах. и рус.)", "KGZ": "Telegram, Instagram (кирг. и рус.)", "TJK": "Telegram, Instagram (тадж. и рус.)",
           "TKM": "Интернет ограничен — родственники, туроператоры, погранпереходы", "AFG": "—"},
    "en": {"USA": "Instagram, YouTube, Google search, travel blogs (English)", "GBR": "Instagram, YouTube, Google search, travel magazines (English)",
           "DEU": "Instagram, YouTube, Google search, tour operators (German)", "FRA": "Instagram, YouTube, Google search, tour operators (French)",
           "ITA": "Instagram, YouTube, Google search, tour operators (Italian)", "JPN": "X (Twitter), Instagram, LINE, YouTube (Japanese)",
           "KOR": "Naver, KakaoTalk, YouTube, Instagram (Korean)", "CHN": "WeChat, Douyin, Xiaohongshu — Google and Instagram are blocked (Chinese)",
           "IND": "Instagram, YouTube, WhatsApp (English and Hindi)", "TUR": "Instagram, YouTube (Turkish)", "RUS": "Telegram, VK, YouTube (Russian)",
           "KAZ": "Telegram, Instagram (Kazakh and Russian)", "KGZ": "Telegram, Instagram (Kyrgyz and Russian)", "TJK": "Telegram, Instagram (Tajik and Russian)",
           "TKM": "Internet restricted — relatives, tour operators, border crossings", "AFG": "—"},
}
MESSAGES_I18N = {
    "ru": {"inspiration": ("Вдохновение", "Познакомить с Узбекистаном: города Шёлкового пути, кухня, безопасность, гостеприимство"),
           "practical": ("Практика", "Убрать барьер: рейсы, полная стоимость, визовый режим, готовый маршрут на 5–7 дней"),
           "broaden": ("Расширение", "Новые места и повторные поездки: Хива, горы, фестивали, гастрономия"),
           "convert": ("Короткий отдых", "Тем, кто уже приезжает: пакеты выходного дня, фестивали, шопинг, оздоровление"),
           "watch": ("Наблюдение", "Отдельная кампания пока не нужна")},
    "en": {"inspiration": ("Inspiration", "Introduce Uzbekistan: Silk Road cities, food, safety, hospitality"),
           "practical": ("Practical", "Remove the barrier: flights, total cost, visa rules, a ready 5–7 day route"),
           "broaden": ("Broaden", "New places and repeat visits: Khiva, mountains, festivals, food"),
           "convert": ("Short breaks", "For people who already come: weekend packages, festivals, shopping, wellness"),
           "watch": ("Watch", "No separate campaign needed for now")},
}
WHY = {  # key -> {lang: template}; {p} = percent, {b} = best neighbour %, {s} = search %, {r}/{t} = rates
    "afg": {"uz": "Asosan tijorat safarlari; dam olish ulushi noma'lum", "ru": "В основном торговые поездки; доля отдыха неизвестна",
            "en": "Mostly trade trips; leisure share unknown"},
    "convert": {"uz": "Dam olish ulushi {p} — eng yaxshi qo'shnida {b}", "ru": "Доля отдыха {p} — у лучшего соседа {b}",
                "en": "Leisure share {p} — best neighbour {b}"},
    "best_near": {"uz": "Qo'shnilar ichida eng yuqori dam olish ulushi ({p})", "ru": "Самая высокая доля отдыха среди соседей ({p})",
                  "en": "Highest leisure share among neighbours ({p})"},
    "tkm": {"uz": "Kelganlarning {p} i dam olish uchun; internet cheklangan", "ru": "{p} приезжающих — ради отдыха; интернет ограничен",
            "en": "{p} of arrivals come for leisure; internet restricted"},
    "practical": {"uz": "Qidiruvda ulush yuqori ({s}), lekin kam keladi — to'siq amaliy", "ru": "Высокая доля в поиске ({s}), но приезжают мало — барьер практический",
                  "en": "High search share ({s}) but few visit — the barrier is practical"},
    "inspire_s": {"uz": "Qidiruvda ulush past ({s}) — O'zbekiston kam tanilgan", "ru": "Низкая доля в поиске ({s}) — Узбекистан мало известен",
                  "en": "Low search share ({s}) — Uzbekistan is little known"},
    "inspire": {"uz": "O'zbekiston kam tanilgan", "ru": "Узбекистан мало известен", "en": "Uzbekistan is little known"},
    "strong": {"uz": "Har 1000 qodir kishidan {r} dam olish safari — odatiy ({t}) darajada yoki yuqori",
               "ru": "{r} поездки на отдых на 1000 платёжеспособных — на типичном уровне ({t}) или выше",
               "en": "{r} leisure trips per 1,000 who can afford it — at or above the typical level ({t})"},
    "small": {"uz": "Imkoniyat kichik yoki allaqachon odatiy darajada", "ru": "Потенциал мал или уже на типичном уровне",
              "en": "Small headroom or already at the typical level"},
}
MESSAGES = {
    "inspiration": ("Ilhom", "O'zbekistonni tanitish: Ipak yo'li shaharlari, oshxona, xavfsizlik, mehmondo'stlik"),
    "practical": ("Amaliy", "To'siqni olib tashlash: reyslar, umumiy narx, viza tartibi, tayyor 5–7 kunlik marshrut"),
    "broaden": ("Kengaytirish", "Yangi joylar va takroriy safar: Xiva, tog'lar, festivallar, gastronomiya"),
    "convert": ("Qisqa dam olish", "Kelib turganlarga: hafta oxiri paketlari, festivallar, xarid, sog'lomlashtirish"),
    "watch": ("Kuzatish", "Hozircha alohida kampaniya shart emas"),
}


def build() -> pd.DataFrame:
    aff = pd.read_csv(AFF) if AFF.exists() else pd.DataFrame()
    ytd, yearly = statuz.load(), statuz.load_yearly()
    sh = purpose.shares(ytd, yearly)
    old = pd.read_csv(purpose.BY_COUNTRY)
    old = old[old["period"].str.startswith("2023")].set_index("country")   # Jan-Oct or Jan-Aug 2023 snapshots
    y = yearly.pivot_table(index="country", columns="year", values="arrivals", aggfunc="sum")
    tr = trends.load()
    snap = None
    if not tr.empty:
        tr["period"] = tr["period"].astype(str)
        snaps = sorted(p for p in tr["period"].unique() if p.startswith("90d-"))
        snap = snaps[-1] if snaps else None
    share_now = sh.set_index("country")["share"]
    rows = []
    for a in aff.itertuples():
        iso, en = a.iso, EN.get(a.iso)
        if not en or en not in y.index:
            continue
        arr25 = float(y.at[en, 2025]) if 2025 in y.columns else None
        arr24 = float(y.at[en, 2024]) if 2024 in y.columns else None
        if en in share_now.index:
            share, src = float(share_now[en]), "2025"
        elif en in old.index:
            share, src = float(old.at[en, "leisure"] / old.at[en, "total"]), "2023"
        else:
            share, src = None, None
        leisure = arr25 * share if (arr25 and share) else None
        search = None
        # Kazakhstan is itself one of the 5 destinations, so its own searches dominate there: not comparable
        if snap and iso in GEO and iso != "KAZ":
            s = tr[(tr["period"] == snap) & (tr["geo"] == GEO[iso]) & (tr["destination"] == "Uzbekistan")]["share"]
            search = int(s.iloc[0]) if len(s) else None
        rows.append({"iso": iso, "num": NUM[iso], "name": a.name, "near": iso in NEAR, "arrivals": arr25,
                     "growth": (arr25 / arr24 - 1) if (arr25 and arr24) else None, "leisure_share": share,
                     "share_year": src, "leisure": leisure, "affordable": float(a.afford_std_central),
                     "search": search})
    df = pd.DataFrame(rows)
    df["rate"] = df["leisure"] / df["affordable"] * 1000          # leisure trips per 1000 who can afford it
    distant = df[~df["near"] & ~df["iso"].isin(["RUS", "TUR"]) & df["rate"].notna()]
    typical = float(distant["rate"].median())
    best_near = float(df[df["iso"].isin(["KAZ", "KGZ", "TJK"])]["leisure_share"].max())
    head = []
    for r in df.itertuples():
        if r.iso in ("KGZ", "TJK", "KAZ"):
            head.append(max(0.0, (best_near - r.leisure_share) * r.arrivals))
        elif r.near or r.leisure is None or pd.isna(r.rate):
            head.append(None)
        else:
            head.append(max(0.0, (typical - r.rate) * r.affordable / 1000))
    df["headroom"] = head
    df["typical_rate"] = typical

    def classify(r):
        """-> group, message, why-key, params"""
        pc = lambda v: f"{v:.0%}"  # noqa: E731
        if r.iso == "AFG":
            return "D", "watch", "afg", {}
        if r.iso in ("KGZ", "TJK", "KAZ"):
            if r.headroom and r.headroom >= MIN_HEADROOM:
                return "C", "convert", "convert", {"p": pc(r.leisure_share), "b": pc(best_near)}
            return "B", "broaden", "best_near", {"p": pc(r.leisure_share)}
        if r.iso == "TKM":
            return "B", "broaden", "tkm", {"p": pc(r.leisure_share)}
        if r.headroom is not None and r.headroom >= MIN_HEADROOM:
            if pd.notna(r.search) and r.search >= 25:
                return "A", "practical", "practical", {"s": f"{r.search:.0f}%"}
            return ("A", "inspiration", "inspire_s", {"s": f"{r.search:.0f}%"}) if pd.notna(r.search) else ("A", "inspiration", "inspire", {})
        if r.leisure and r.leisure >= STRONG and (pd.isna(r.rate) or r.rate >= typical):
            return "B", "broaden", "strong", {"r": f"{r.rate:.2f}", "t": f"{typical:.2f}"}
        return "D", "watch", "small", {}
    cls = df.apply(lambda r: pd.Series(classify(r), index=["group", "message", "why_key", "why_params"]), axis=1)
    df = pd.concat([df, cls[["group", "message"]]], axis=1)
    for lang in ("uz", "ru", "en"):
        texts = []
        for k, prm in zip(cls["why_key"], cls["why_params"]):
            t = WHY[k][lang].format(**prm)
            texts.append(t.replace(".", ",") if lang != "en" and k == "strong" else t)
        df["why" if lang == "uz" else f"why_{lang}"] = texts
    df["message_uz"] = df["message"].map(lambda m: MESSAGES[m][0])
    df["message_detail"] = df["message"].map(lambda m: MESSAGES[m][1])
    df["channels"] = df["iso"].map(CHANNELS)
    for lang in ("ru", "en"):
        df[f"message_{lang}"] = df["message"].map(lambda m: MESSAGES_I18N[lang][m][0])
        df[f"message_detail_{lang}"] = df["message"].map(lambda m: MESSAGES_I18N[lang][m][1])
        df[f"channels_{lang}"] = df["iso"].map(CHANNELS_I18N[lang])
    order = {"A": 0, "C": 1, "B": 2, "D": 3}
    df = df.sort_values(["group", "headroom", "leisure"], key=lambda s: s.map(order) if s.name == "group" else -s.fillna(0))
    df.round(4).to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    d = build()
    print(d[["name", "group", "message_uz", "leisure", "rate", "headroom", "search", "growth", "why"]].round(2).to_string(index=False))
    print("typical rate", d["typical_rate"].iloc[0])
