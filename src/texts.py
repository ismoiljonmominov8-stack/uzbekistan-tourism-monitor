"""Post wording in Uzbek and English. POST_LANG in config picks one."""
from . import config

T = {
    "uz": {
        "daily_title": "📊 O'zbekistonga qiziqish indeksi — {date}",
        "movers": "Eng katta o'zgarishlar (oxirgi 30 kunning odatiy kuniga — medianaga nisbatan):",
        "most_viewed": "Eng ko'p ko'rilgan sahifa: {article} (barcha tillarda)",
        "trend": "7 kunlik trend: {n} ta bozordan {up} tasida o'sish",
        "spike": "⚠️ Odatdan tashqari: {markets} — sababini tekshiring (bayram? yangi reys? yangilik?)",
        "quiet": "📊 {date}: sezilarli o'zgarish yo'q.",
        "all_normal": "✔️ Barcha o'zgarishlar odatiy kunlik tebranish chegarasida — alohida e'tibor talab qilmaydi.",
        "why_title": "🔎 Izoh (ma'lumotlarga asoslangan):",
        "why_weekday": "• {market}: {weekday} kunlari ko'rishlar odatda {pct:.0%} {dir} (oxirgi 8 hafta)",
        "why_small": "• {market}: kichik bozor (kuniga ~{n} ko'rish) — kunlik tebranish tabiiy ravishda katta",
        "why_yoy": "• O'tgan yilning shu haftasiga nisbatan (uzoq bozorlar): {raw:+.0%}. Biroq shu tillardagi butun Vikipediya trafigi {wiki:+.0%} o'zgargan; buni hisobga olsak, O'zbekistonga qiziqish ulushi {pct:+.0%}",
        "dir_down": "pastroq", "dir_up": "yuqoriroq",
        "concl_normal": "Xulosa: kunlik o'zgarishlar odatiy tebranish. {yoy_text}",
        "yoy_up": "O'tgan yilga nisbatan qiziqish yuqoriroq.", "yoy_down": "O'tgan yilga nisbatan qiziqish pastroq.",
        "yoy_flat": "O'tgan yilga nisbatan qiziqish deyarli o'zgarmagan.",
        "concl_unusual": "Xulosa: {markets} — odatdan tashqari o'zgarish; sababini yangiliklardan qidiring.",
        "weekdays": ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"],
        "chart_link": "📈 Barcha kunlar grafigi: {url}",
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
        "review": "📝 Ko'rib chiqish uchun (kanalga hali chiqmagan). Tugmani bir marta bosing — 15 daqiqagacha bajariladi:",
        "check_failed": "⚠️ Tekshiruvdan o'tmadi — kanalga joylanmadi. Manbani qo'lda tekshiring:",
        "bot_warning": "ℹ️ {market}: o'sishning deyarli hammasi bitta sahifada ({article}) — bot trafigi yoki bitta tarqalgan havola bo'lishi mumkin.",
    },
    "en": {
        "daily_title": "📊 Uzbekistan interest index — {date}",
        "movers": "Top movers (vs a typical day of the last 30 — the median):",
        "most_viewed": "Most viewed page: {article} (all languages)",
        "trend": "7-day trend: rising in {up} of {n} markets",
        "spike": "⚠️ Unusual: {markets} — check why (holiday? new flight? news?)",
        "quiet": "📊 {date}: no significant changes.",
        "all_normal": "✔️ All changes are within normal day-to-day variation — nothing unusual.",
        "why_title": "🔎 Why (from the data):",
        "why_weekday": "• {market}: on {weekday}s views are usually {pct:.0%} {dir} (last 8 weeks)",
        "why_small": "• {market}: small market (~{n} views a day) — large daily swings are normal",
        "why_yoy": "• Vs the same week last year (distant markets): {raw:+.0%}. But total Wikipedia traffic in these languages changed {wiki:+.0%}; adjusting for that, Uzbekistan's share of attention is {pct:+.0%}",
        "dir_down": "lower", "dir_up": "higher",
        "concl_normal": "Conclusion: the daily changes are normal variation. {yoy_text}",
        "yoy_up": "Interest is higher than a year ago.", "yoy_down": "Interest is lower than a year ago.",
        "yoy_flat": "Interest is about the same as a year ago.",
        "concl_unusual": "Conclusion: unusual change in {markets}; look for the cause in the news.",
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "chart_link": "📈 Chart of every day: {url}",
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
        "review": "📝 For review (not posted yet). Press a button once — it is handled within 15 minutes:",
        "check_failed": "⚠️ Failed checks — NOT posted to the channel. Please verify the source by hand:",
        "bot_warning": "ℹ️ {market}: almost all of the jump is on one page ({article}) — may be automated traffic or one viral link.",
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
