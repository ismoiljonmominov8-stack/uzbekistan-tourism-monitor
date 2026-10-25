"""Conversation with the admin in the bot chat, in plain Uzbek.

- Menu buttons (always visible): 📊 Bugungi holat · 🗓 Kutilayotgan voqealar · ➕ Voqea qo'shish · ❓ Yordam
- Any normal message is read by the AI: if it describes an event (festival, flight, visa, border...),
  the bot shows what it understood and asks "✅ Ha, saqlash / ❌ Yo'q". Nothing is saved without ✅.
- Old /event and /events commands still work, but nobody has to remember a format.
"""
import hashlib
import json
import re
from datetime import date, datetime, timezone

import pandas as pd

from . import ai, config, events
from .texts import market_name
from .util import admin_id, esc, log, read_json, send_message, write_json

DRAFTS = config.DATA / "event_drafts.json"

B_STATUS = "📊 Bugungi holat"
B_UPCOMING = "🗓 Kutilayotgan voqealar"
B_ADD = "➕ Voqea qo'shish"
B_HELP = "❓ Yordam"
MENU = [[B_STATUS, B_UPCOMING], [B_ADD, B_HELP]]

TYPE_UZ = {"visa": "viza o'zgarishi", "border": "chegara ochilishi", "crossing": "yangi chegara o'tish punkti",
           "flight": "yangi reys / aviakompaniya", "event": "tadbir (festival, konferensiya, ko'rgazma)",
           "sport": "sport musobaqasi", "politics": "siyosiy voqea (sammit, kelishuv)", "price": "narx o'zgarishi",
           "infrastructure": "infratuzilma (aeroport, poyezd, mehmonxona)", "marketing": "reklama / marketing",
           "other": "boshqa"}
MONTHS_UZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr",
             "dekabr"]

HELP = (
    "Men O'zbekiston turizmini kuzatuvchi botman. Nima qila olaman:\n\n"
    f"<b>{B_STATUS}</b> — Vikipediyadagi bugungi qiziqish, yangiliklar va oxirgi rasmiy statistika.\n\n"
    f"<b>{B_UPCOMING}</b> — kelgusi voqealar va ular turistlar soniga qanday ta'sir qilishi mumkinligi.\n\n"
    f"<b>{B_ADD}</b> — voqeani <b>oddiy so'zlar bilan</b> yozing, hech qanday format kerak emas. Masalan:\n"
    "<i>«5-dekabr kuni Samarqandda Ipak yo'li festivali bo'ladi, Xitoy va Koreyadan mehmonlar kutilmoqda»</i>\n"
    "<i>«Yanvardan Seul–Samarqand to'g'ridan-to'g'ri reysi ochiladi»</i>\n"
    "<i>«2027 yil 1 martdan Yaponiya fuqarolariga 60 kunlik vizasiz rejim»</i>\n\n"
    "Men nimani tushunganimni ko'rsataman va <b>✅ Ha, saqlash</b> tugmasini bosgandagina saqlayman.\n\n"
    "ℹ️ Javoblar darhol emas, bot tekshirganda keladi: ertalab 09:50 dan keyin bir necha soniyada, "
    "boshqa paytda 1–2 soatgacha."
)


# ---------------------------------------------------------------- dates written in Uzbek
def parse_date_text(text: str, today: date | None = None):
    """'2026-12-05', '05.12.2026', '5-dekabr', '5 dekabr 2026', 'dekabr 2026', '2026-12', '2026-Q4',
    '4-chorak 2026' -> (ISO date, precision) or None. Without a year the next such date is used."""
    today = today or date.today()
    s = text.lower().replace("‘", "'").replace("’", "'")
    m = re.search(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat(), "day"
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b", s)
    if m:
        return date(int(m[3]), int(m[2]), int(m[1])).isoformat(), "day"
    m = re.search(r"\b(20\d\d)[- ]?q([1-4])\b", s) or re.search(r"\b([1-4])[- ]?chorak\D{0,4}(20\d\d)?", s)
    if m:
        if m.re.pattern.startswith(r"\b(20"):
            y, q = int(m[1]), int(m[2])
        else:
            q, y = int(m[1]), int(m[2]) if m[2] else today.year
        return pd.Period(f"{y}Q{q}", "Q").end_time.date().isoformat(), "quarter"
    m = re.search(r"\b(20\d\d)-(\d{1,2})\b", s)
    if m:
        return pd.Period(f"{m[1]}-{int(m[2]):02d}", "M").end_time.date().isoformat(), "month"
    for i, name in enumerate(MONTHS_UZ, start=1):
        m = re.search(rf"\b(\d{{1,2}})[- ]?{name}\w*(?:\D{{0,6}}(20\d\d))?", s)
        if m:
            y = int(m[2]) if m[2] else today.year
            d = date(y, i, min(int(m[1]), 28 if i == 2 else 30 if i in (4, 6, 9, 11) else 31))
            if not m[2] and d < today:
                d = date(y + 1, i, d.day)
            return d.isoformat(), "day"
        m = re.search(rf"\b{name}\w*(?:\D{{0,6}}(20\d\d))?", s)
        if m:
            y = int(m[1]) if m[1] else today.year
            if not m[1] and i < today.month:
                y += 1
            return pd.Period(f"{y}-{i:02d}", "M").end_time.date().isoformat(), "month"
    return None


def nice_date(iso: str, precision: str = "day") -> str:
    d = date.fromisoformat(iso)
    if precision == "month":
        return f"{MONTHS_UZ[d.month - 1]} {d.year} (aniq kuni noma'lum)"
    if precision == "quarter":
        return f"{(d.month - 1) // 3 + 1}-chorak {d.year} (aniq sanasi noma'lum)"
    return f"{d.day}-{MONTHS_UZ[d.month - 1]} {d.year}"


# ---------------------------------------------------------------- understanding a message
COUNTRY_WORDS = {
    "xitoy": "china", "china": "china", "koreya": "korea", "korea": "korea", "yaponiya": "japan", "japan": "japan",
    "germaniya": "germany", "germany": "germany", "turkiya": "turkey", "turkey": "turkey", "türkiye": "turkey",
    "italiya": "italy", "italy": "italy", "fransiya": "france", "france": "france", "hindiston": "india",
    "india": "india", "qozog'iston": "kazakhstan", "kazakhstan": "kazakhstan", "qirg'iziston": "kyrgyzstan",
    "kyrgyzstan": "kyrgyzstan", "tojikiston": "tajikistan", "tajikistan": "tajikistan",
    "turkmaniston": "turkmenistan", "turkmenistan": "turkmenistan", "afg'oniston": "afghanistan",
    "afghanistan": "afghanistan", "qo'shni": "neighbours", "neighbour": "neighbours", "barcha": "all",
    "hamma": "all", "all": "all", "xalqaro": "all",
}
TYPE_WORDS = [("crossing", r"o'tish punkt|punkt|checkpoint|crossing|nazorat-o'tkazish"),
              ("border", r"chegara|border"), ("visa", r"viza|visa"),
              ("flight", r"reys|parvoz|aviakompan|airline|flight|aeroport"),
              ("sport", r"chempionat|musobaqa|olimpiada|futbol|marafon|sport"),
              ("politics", r"sammit|summit|tashrif|kelishuv|forum"),
              ("event", r"festival|ko'rgazma|yarmarka|konferens|kongress|bayram|navro'z|tadbir|fair"),
              ("infrastructure", r"poyezd|afrosiyob|mehmonxona|temir yo'l|infratuzilma"),
              ("price", r"narx|chegirma|arzon"), ("marketing", r"reklama|marketing|kampaniya")]

EXTRACT_PROMPT = """Today is {today}. A tourism researcher in Uzbekistan wrote this message to a monitoring bot
(usually in Uzbek, sometimes Russian or English):

<<<{text}>>>

Does it describe a specific event that could change the number of FOREIGN tourists coming to Uzbekistan
(festival, fair, conference, sports event, new flight route or airline, visa change, border opening,
new border crossing, summit or agreement, price change, new infrastructure, marketing campaign)?

Return only JSON:
{{"is_event": true or false,
  "date": "YYYY-MM-DD" or null,          // when it starts / comes into force; only from the message
  "date_precision": "day" | "month" | "quarter",
  "type": "visa"|"border"|"crossing"|"flight"|"event"|"sport"|"politics"|"price"|"infrastructure"|"marketing"|"other",
  "countries": [ ... ],                  // English names of the source countries whose tourists are affected,
                                         // or ["all"] if international / not specified, or ["neighbours"]
  "title": "...",                        // short title in Uzbek (Latin script, o' g' sh ch), your own words
  "link": "https://..." or null}}        // only a URL that appears in the message
"border" = a closed border or visa regime with a neighbouring country is opened; "crossing" = an extra
or reopened checkpoint on a border that is already open. If only a month is given, use its last day
and "month"; if only a quarter, its last day and "quarter". A date without a year means the next such
date after today. Never invent a date: if none is given, use null."""


def understand(text: str) -> dict:
    """Message -> draft {date, precision, type, markets[], title, link} or {'error': reason}."""
    data, provider = ai.ask(EXTRACT_PROMPT.format(today=date.today().isoformat(), text=text[:1500]))
    low = text.lower().replace("‘", "'").replace("’", "'")
    link = re.search(r"https?://\S+", text)
    if data and not data.get("is_event"):
        return {"error": "not_event"}
    draft = {"provider": provider or "rules"}
    # date: AI first, then our own Uzbek date reader
    when = None
    if data and data.get("date"):
        try:
            when = (date.fromisoformat(str(data["date"])[:10]).isoformat(), data.get("date_precision") or "day")
        except ValueError:
            when = None
    when = when or parse_date_text(text)
    if not when:
        return {"error": "no_date"}
    draft["date"], draft["precision"] = when
    if draft["precision"] not in ("day", "month", "quarter"):
        draft["precision"] = "day"
    etype = (data or {}).get("type")
    if etype not in events.TYPES:
        etype = next((t for t, pat in TYPE_WORDS if re.search(pat, low)), "other")
    draft["type"] = etype
    names = [str(c).strip().lower() for c in ((data or {}).get("countries") or [])]
    names += [v for k, v in COUNTRY_WORDS.items() if re.search(rf"\b{re.escape(k)}", low)]
    if any(n in ("all",) for n in names) and len(set(names)) == 1:
        markets = ["all"]
    elif "neighbours" in names:
        markets = ["neighbours"]
    else:
        markets = sorted({events.COUNTRY_LANG[n] for n in names if n in events.COUNTRY_LANG})
        markets = markets or ["all"]
    draft["markets"] = markets
    title = (data or {}).get("title")
    if not title:  # no AI: use the message itself, shortened
        title = re.sub(r"https?://\S+", "", text).strip()
        title = title if len(title) <= 90 else title[:88].rsplit(" ", 1)[0] + "…"
    draft["title"] = title[:140]
    draft["link"] = ((data or {}).get("link") if (data or {}).get("link") and (data or {}).get("link") in text
                     else (link.group(0) if link else ""))
    return draft


def markets_text(markets: list[str]) -> str:
    if markets == ["all"]:
        return "barcha xorijiy bozorlar (aniq davlat aytilmagan)"
    if markets == ["neighbours"]:
        return "qo'shni davlatlar"
    return ", ".join(f"{config.MARKETS[m]['flag']} {market_name(m)}" for m in markets if m in config.MARKETS)


NO = "yo'q"


def confirm_card(d: dict) -> str:
    days = (date.fromisoformat(d["date"]) - date.today()).days
    when = f"{days} kundan keyin" if days > 0 else "bugun" if days == 0 else f"{-days} kun oldin"
    return (
        "Men shunday tushundim:\n\n"
        f"📝 <b>{esc(d['title'])}</b>\n"
        f"🗓 Sana: {nice_date(d['date'], d['precision'])} — {when}\n"
        f"🏷 Turi: {TYPE_UZ.get(d['type'], d['type'])}\n"
        f"🌍 Qaysi davlatlar turistlariga ta'sir qiladi: {markets_text(d['markets'])}\n"
        f"🔗 Manba: {esc(d['link']) if d.get('link') else NO}\n\n"
        "To'g'rimi? Noto'g'ri bo'lsa ❌ ni bosing va aniqroq yozing (sana, davlatlar)."
    )


# ---------------------------------------------------------------- simple explanation of the forecast
def _likely(p) -> str:
    if p is None:
        return "hali aytib bo'lmaydi"
    return "kam ehtimol" if p < 0.34 else "o'rtacha ehtimol" if p < 0.6 else "katta ehtimol"


def _round(n: int) -> str:
    v = int(round(n, -2)) if abs(n) >= 1000 else int(round(n, -1)) if abs(n) >= 100 else int(n)
    return f"{v:,}".replace(",", " ")


def explain_upcoming(u: dict, header: str = "") -> str:
    est = u["estimate"]
    i, a, x = est.get("info") or {}, est.get("arr") or {}, est.get("expected") or {}
    lines = [header] if header else []
    lines += [f"📝 <b>{esc(u['title'])}</b>",
              f"🗓 {nice_date(u['date'], u.get('precision') or 'day')} — {u['days']} kundan keyin · "
              f"{TYPE_UZ.get(u['type'], u['type'])}",
              f"🌍 {markets_text(events.expand(u['markets']) if u['markets'] not in ('all', 'neighbours') else [u['markets']])}",
              ""]
    n = max(i.get("n", 0), a.get("n", 0))
    if not n or (i.get("p") is None and a.get("p") is None):
        lines.append("ℹ️ Bunday turdagi voqealar hali kam o'lchangan, shuning uchun ta'sirini oldindan aytib "
                     "bo'lmaydi. Voqea o'tgach, haqiqiy natijani o'lchab sizga yozaman.")
    else:
        lines.append("<b>Bunday voqealar ilgari qanday ta'sir qilgan:</b>")
        if i.get("p") is not None:
            lines.append(f"📖 Odamlar O'zbekiston haqida ko'proq qidiradimi? — <b>{_likely(i['p'])}</b> "
                         f"({i['n']} ta o'xshash voqeadan {i['k']} tasida shunday bo'lgan)")
        if a.get("p") is not None:
            lines.append(f"🧳 Turistlar ko'payadimi? — <b>{_likely(a['p'])}</b> "
                         f"({a['n']} ta o'xshash voqeadan {a['k']} tasida turistlar odatdagidan ko'proq kelgan)")
        if x.get("markets"):
            lines.append("")
            lines.append("🔢 <b>Raqamlarda:</b>")
            for lang, m in sorted(x["markets"].items(), key=lambda kv: -kv[1]["base_month"])[:3]:
                name = f"{config.MARKETS[lang]['flag']} {market_name(lang)}"
                if m["mid"] == 0 or abs(m["mid"]) < m["base_month"] * 0.03:
                    change = "odatda bu sonni deyarli o'zgartirmaydi"
                elif m["mid"] > 0:
                    change = f"odatda oyiga taxminan <b>+{_round(m['mid'])}</b> qo'shimcha turist"
                else:
                    change = f"odatda oyiga taxminan <b>−{_round(-m['mid'])}</b> turist kamroq"
                lines.append(f"{name}: hozir oyiga ~{_round(m['base_month'])} turist keladi; bunday voqea {change} "
                             f"(odatiy oraliq: {('+' if m['low'] > 0 else '−' if m['low'] < 0 else '')}{_round(abs(m['low']))} "
                             f"dan {('+' if m['high'] > 0 else '−' if m['high'] < 0 else '')}{_round(abs(m['high']))} gacha)")
        lines += ["", "<i>Bu o'tgan voqealarga asoslangan taxmin, kafolat emas. Voqea o'tgach, haqiqiy "
                      "ta'sirni o'lchab sizga yozaman.</i>"]
    if u.get("source"):
        lines.append(f'🔗 <a href="{esc(u["source"])}">manba</a>')
    return "\n".join(lines)


# ---------------------------------------------------------------- status on demand
def status_text() -> str:
    from . import pageviews, posts, statuz
    from .news import PENDING
    try:
        pageviews.collect()
    except Exception as e:  # noqa: BLE001 - show what we have
        log.warning("status: pageviews collect failed: %s", e)
    df = pageviews.load()
    wide = pageviews.market_daily(df)
    parts = []
    if not wide.empty:
        day = wide.index.max()
        txt = posts.daily_text(df, wide, day)
        parts.append(txt or f"📊 Vikipediya: {day:%d.%m.%Y} uchun hali taqqoslash uchun yetarli ma'lumot yo'q.")
        parts.append("<i>Vikipediya kunlik ma'lumoti bir kun kechikib chiqadi — shuning uchun «bugungi holat» "
                     "kechagi kun bo'yicha.</i>")
    pending = read_json(PENDING, {})
    parts.append(f"📰 Yangiliklar: tasdiqlashingizni kutayotgan {len(pending)} ta yangilik bor (yuqoridagi xabarlarda ✅/❌)."
                 if pending else "📰 Yangiliklar: hozircha tasdiq kutayotgan yangilik yo'q. Yangi yangiliklar har kuni "
                                 "ertalab tekshiriladi.")
    ytd = statuz.load()
    if not ytd.empty:
        last = ytd[ytd["country"] == "TOTAL"].sort_values(["year", "month"]).iloc[-1]
        parts.append(f"🧾 Oxirgi rasmiy statistika: yanvar–{MONTHS_UZ[int(last['month']) - 1]} {int(last['year'])}, "
                     f"jami {int(last['ytd']):,} xorijiy turist.".replace(",", " "))
    ups = events.upcoming(days=31)
    parts.append(f"🗓 Keyingi 30 kunda {len(ups)} ta voqea: " + "; ".join(f"{nice_date(u['date'])} — {esc(u['title'])}" for u in ups)
                 if ups else "🗓 Keyingi 30 kunda tasdiqlangan voqea yo'q.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- entry points
def _draft_id(text: str) -> str:
    return hashlib.sha1(f"{text}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:10]


def handle_message(msg, alog) -> None:
    if str(msg.get("from", {}).get("id")) != str(admin_id()):
        alog("message ignored: not from the admin")
        return
    text = (msg.get("text") or msg.get("caption") or "").strip()
    chat = msg["chat"]["id"]
    alog(f"message received: {text[:120]!r}")
    first = text.split(maxsplit=1)[0].split("@")[0].lower() if text else ""
    if not text:
        send_message(chat, "Men faqat matnli xabarlarni o'qiy olaman. Voqeani so'zlar bilan yozing.", keyboard=MENU)
        return
    if first in ("/start", "/help", "/yordam") or text == B_HELP:
        send_message(chat, HELP, keyboard=MENU)
        return
    if text == B_STATUS or first in ("/status", "/holat"):
        send_message(chat, status_text(), keyboard=MENU)
        return
    if text == B_UPCOMING or first in ("/events", "/voqealar"):
        arg = text.split(maxsplit=1)[1].strip().lower() if first.startswith("/") and len(text.split()) > 1 else ""
        ups = events.upcoming(days=events.PERIODS.get(arg))
        if not ups:
            send_message(chat, "Hozircha kutilayotgan voqea yo'q. Qo'shish uchun voqeani oddiy so'zlar bilan yozing.",
                         keyboard=MENU)
            return
        for k, u in enumerate(ups[:8]):
            send_message(chat, explain_upcoming(u, header=f"<b>{k + 1}/{min(len(ups), 8)}</b>"), keyboard=MENU)
        return
    if text == B_ADD:
        send_message(chat, "Voqeani oddiy so'zlar bilan yozing: <b>nima</b>, <b>qachon</b> va <b>qaysi davlatlar</b> "
                           "turistlariga tegishli. Havola bo'lsa, qo'shing.\n\nMasalan: <i>«5-dekabr kuni Samarqandda "
                           "Ipak yo'li festivali, Xitoy va Koreyadan mehmonlar kutilmoqda»</i>", keyboard=MENU)
        return
    # anything else (including old /event commands): try to understand it as an event
    body = text.split(maxsplit=1)[1] if first in ("/event", "/voqea") and len(text.split(maxsplit=1)) > 1 else text
    body = body.replace("|", ", ")
    draft = understand(body)
    if draft.get("error") == "not_event":
        send_message(chat, "Bu xabarda turistlarga ta'sir qiladigan voqeani topmadim. Voqea qo'shmoqchi bo'lsangiz, "
                           "nima, qachon va qaysi davlatlar haqida ekanini yozing — yoki pastdagi tugmalardan "
                           "foydalaning.", keyboard=MENU)
        return
    if draft.get("error") == "no_date":
        send_message(chat, "Voqeani tushundim, lekin <b>sanasini</b> topmadim. Qachon bo'lishini qo'shib qayta yozing, "
                           "masalan: <i>«5-dekabr»</i>, <i>«dekabr 2026»</i> yoki <i>«2026-yil 4-chorak»</i>.",
                     keyboard=MENU)
        return
    drafts = read_json(DRAFTS, {})
    did = _draft_id(body)
    drafts[did] = draft
    write_json(DRAFTS, dict(list(drafts.items())[-30:]))
    alog(f"draft {did}: {json.dumps(draft, ensure_ascii=False)[:200]}")
    send_message(chat, confirm_card(draft), buttons=[[("✅ Ha, saqlash", f"ev:{did}"), ("❌ Yo'q", f"evx:{did}")]])


def handle_callback(cq, action: str, did: str, alog, safe) -> None:
    drafts = read_json(DRAFTS, {})
    draft = drafts.pop(did, None)
    write_json(DRAFTS, drafts)
    msg = cq.get("message") or {}
    chat = msg.get("chat", {}).get("id") or admin_id()
    if draft is None:
        safe("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "Bu allaqachon ko'rib chiqilgan"})
        return
    label = "✅ Saqlandi" if action == "ev" else "❌ Bekor qilindi"
    safe("answerCallbackQuery", {"callback_query_id": cq["id"], "text": label})
    if msg:
        safe("editMessageReplyMarkup", {"chat_id": chat, "message_id": msg["message_id"],
                                        "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": "x:x"}]]}})
    if action != "ev":
        send_message(chat, "Bekor qilindi. Qaytadan aniqroq yozishingiz mumkin (sana, davlatlar).", keyboard=MENU)
        return
    words = {"china": "China", "korea": "Korea"}
    markets = draft["markets"] if draft["markets"] in (["all"], ["neighbours"]) else [
        config.MARKETS[m]["en"] for m in draft["markets"]]
    markets = [words.get(m, m) for m in markets]
    eid = events.add_event(draft["date"], draft["type"], markets, draft["title"], draft.get("link", ""), "manual",
                           precision=draft["precision"])
    if not eid:
        send_message(chat, "Saqlab bo'lmadi: bu havola bilan voqea allaqachon bor yoki davlat aniqlanmadi.", keyboard=MENU)
        return
    alog(f"event saved from chat: {eid}")
    events.measure()
    u = next((x for x in events.upcoming() if x["id"] == eid), None)
    if u:
        send_message(chat, explain_upcoming(u, header="✅ <b>Saqlandi.</b>"), keyboard=MENU)
    else:
        send_message(chat, f"✅ Saqlandi ({nice_date(draft['date'], draft['precision'])}). Bu o'tgan voqea — uning "
                           "haqiqiy ta'siri ma'lumotlar chiqishi bilan o'lchanadi.", keyboard=MENU)
