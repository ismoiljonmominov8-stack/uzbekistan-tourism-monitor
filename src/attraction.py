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
        if r.iso == "AFG":
            return "D", "watch", "Asosan tijorat safarlari; dam olish ulushi noma'lum"
        if r.iso in ("KGZ", "TJK", "KAZ"):
            if r.headroom and r.headroom >= MIN_HEADROOM:
                return "C", "convert", f"Dam olish ulushi {r.leisure_share:.0%} — eng yaxshi qo'shnida {best_near:.0%}"
            return "B", "broaden", f"Qo'shnilar ichida eng yuqori dam olish ulushi ({r.leisure_share:.0%})"
        if r.iso == "TKM":
            return "B", "broaden", f"Kelganlarning {r.leisure_share:.0%} i dam olish uchun; internet cheklangan"
        if r.headroom is not None and r.headroom >= MIN_HEADROOM:
            if pd.notna(r.search) and r.search >= 25:
                return "A", "practical", f"Qidiruvda ulush yuqori ({r.search:.0f}%), lekin kam keladi — to'siq amaliy"
            return "A", "inspiration", (f"Qidiruvda ulush past ({r.search:.0f}%) — O'zbekiston kam tanilgan" if pd.notna(r.search)
                                        else "O'zbekiston kam tanilgan")
        if r.leisure and r.leisure >= STRONG and (pd.isna(r.rate) or r.rate >= typical):
            return "B", "broaden", (f"Har 1000 qodir kishidan {r.rate:.2f} dam olish safari — odatiy ({typical:.2f}) darajada yoki yuqori"
                                    .replace(".", ","))
        return "D", "watch", "Imkoniyat kichik yoki allaqachon odatiy darajada"
    out = df.apply(lambda r: pd.Series(classify(r), index=["group", "message", "why"]), axis=1)
    df = pd.concat([df, out], axis=1)
    df["message_uz"] = df["message"].map(lambda m: MESSAGES[m][0])
    df["message_detail"] = df["message"].map(lambda m: MESSAGES[m][1])
    df["channels"] = df["iso"].map(CHANNELS)
    order = {"A": 0, "C": 1, "B": 2, "D": 3}
    df = df.sort_values(["group", "headroom", "leisure"], key=lambda s: s.map(order) if s.name == "group" else -s.fillna(0))
    df.round(4).to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    d = build()
    print(d[["name", "group", "message_uz", "leisure", "rate", "headroom", "search", "growth", "why"]].round(2).to_string(index=False))
    print("typical rate", d["typical_rate"].iloc[0])
