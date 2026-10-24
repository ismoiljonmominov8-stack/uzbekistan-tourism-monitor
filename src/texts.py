"""Post wording in Uzbek and English. POST_LANG in config picks one."""
from . import config

T = {
    "uz": {
        "daily_title": "📊 O'zbekistonga qiziqish indeksi — {date}",
        "movers": "Eng katta o'zgarishlar (30 kunlik o'rtachaga nisbatan):",
        "most_viewed": "Eng ko'p ko'rilgan sahifa: {article} (barcha tillarda)",
        "trend": "7 kunlik trend: {n} ta bozordan {up} tasida o'sish",
        "spike": "⚠️ Odatdan tashqari: {markets} — sababini tekshiring (bayram? yangi reys? yangilik?)",
        "quiet": "📊 {date}: sezilarli o'zgarish yo'q.",
        "no_data": "📊 {date}: Vikipediya ma'lumotlari hali chiqmagan.",
        "footnote": "Manba: Vikipediya sahifa ko'rishlari (O'zbekiston, Samarqand, Buxoro, Xiva, Toshkent).",
        "news_impact": "Ta'sir",
        "news_market": "Bozor",
        "news_when": "Qachon",
        "news_conf": "Ishonch",
        "news_why": "Nega",
        "news_source": "Manba",
        "news_no_ai": "(tahlil mavjud emas — AI javob bermadi)",
        "impact": {"positive": "▲ Ijobiy", "negative": "▼ Salbiy", "mixed": "◆ Aralash", "unclear": "? Noaniq"},
        "conf": {"low": "Past", "medium": "O'rta", "high": "Yuqori"},
        "weekly_title": "📈 Haftalik hisobot — {start} – {end}",
        "weekly_line": "{flag} {name}: {change:+.0%} (oldingi haftaga nisbatan)",
        "weekly_caption": "Qiziqish indeksi, oxirgi 12 hafta (har bir bozor = 100, 12 hafta oldin)",
        "monthly_title": "🧾 Rasmiy statistika: {period}",
        "monthly_total": "Jami xorijiy turistlar (yil boshidan): {total:,} ta",
        "monthly_month": "Shu oyning o'zi: {n:,} ta",
        "monthly_markets": "Uzoq bozorlar — shu oyda kelgan turistlar | Vikipediya ko'rishlari:",
        "monthly_row": "{flag} {name}: {arrivals} | {views}",
        "monthly_note": "⚠️ Manbadagi xato tuzatildi: {note}",
        "monthly_src": "Manba: O'zbekiston Milliy statistika qo'mitasi",
        "approve": "✅ Kanalga", "reject": "❌ Rad etish",
        "approved": "✅ Kanalga joylandi", "rejected": "❌ Rad etildi",
        "review": "📝 Ko'rib chiqish uchun (kanalga hali chiqmagan):",
    },
    "en": {
        "daily_title": "📊 Uzbekistan interest index — {date}",
        "movers": "Top movers (vs 30-day average):",
        "most_viewed": "Most viewed page: {article} (all languages)",
        "trend": "7-day trend: rising in {up} of {n} markets",
        "spike": "⚠️ Unusual: {markets} — check why (holiday? new flight? news?)",
        "quiet": "📊 {date}: no significant changes.",
        "no_data": "📊 {date}: Wikipedia data not published yet.",
        "footnote": "Source: Wikipedia pageviews (Uzbekistan, Samarkand, Bukhara, Khiva, Tashkent).",
        "news_impact": "Impact",
        "news_market": "Market",
        "news_when": "When",
        "news_conf": "Confidence",
        "news_why": "Why",
        "news_source": "Source",
        "news_no_ai": "(no analysis — AI did not respond)",
        "impact": {"positive": "▲ Positive", "negative": "▼ Negative", "mixed": "◆ Mixed", "unclear": "? Unclear"},
        "conf": {"low": "Low", "medium": "Medium", "high": "High"},
        "weekly_title": "📈 Weekly report — {start} – {end}",
        "weekly_line": "{flag} {name}: {change:+.0%} (vs previous week)",
        "weekly_caption": "Interest index, last 12 weeks (each market = 100 twelve weeks ago)",
        "monthly_title": "🧾 Official statistics: {period}",
        "monthly_total": "Total foreign tourists (year to date): {total:,}",
        "monthly_month": "This month alone: {n:,}",
        "monthly_markets": "Distant markets — tourists this month | Wikipedia views:",
        "monthly_row": "{flag} {name}: {arrivals} | {views}",
        "monthly_note": "⚠️ Source typo corrected: {note}",
        "monthly_src": "Source: National Statistics Committee of Uzbekistan",
        "approve": "✅ Post", "reject": "❌ Reject",
        "approved": "✅ Posted to channel", "rejected": "❌ Rejected",
        "review": "📝 For review (not posted yet):",
    },
}

MONTHS = {
    "uz": ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
}


def t(key):
    return T.get(config.POST_LANG, T["en"])[key]


def market_name(lang):
    m = config.MARKETS[lang]
    return m.get(config.POST_LANG, m["en"])


def month_name(m):
    return MONTHS.get(config.POST_LANG, MONTHS["en"])[m - 1]
