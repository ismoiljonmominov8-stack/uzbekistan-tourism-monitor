"""Weekly Word report (Uzbek): daily Wikipedia interest, official statistics, forecast, Google Trends,
events, news, data health, conclusions and next steps.

Conclusions and next steps are produced by fixed rules from the numbers (no AI), so the report never
states something the data does not show. Output: docs/reports/hisobot-<end date>.docx (+ latest.docx).
Python builds the content (report.json) and a chart; report/docx_report.js writes the .docx file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config, events, forecast, pageviews, statuz, trends  # noqa: E402
from .util import admin_id, dry_run, log  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "reports"
WORK = ROOT / "build"
OY = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
HAFTA = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
TYPE_UZ = {"visa": "viza", "border": "chegara", "crossing": "o'tish punkti", "flight": "reys", "event": "tadbir",
           "sport": "sport", "politics": "siyosat", "price": "narx", "infrastructure": "infratuzilma",
           "marketing": "marketing", "other": "boshqa"}


def n(x) -> str:
    """12 345 678 (Uzbek thousands separator)."""
    return f"{int(round(x)):,}".replace(",", " ")


def pct(x, sign=True) -> str:
    return (f"{x:+.0%}" if sign else f"{x:.0%}").replace("+-", "−").replace("-", "−")


def d_uz(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.day}-{OY[d.month - 1]} {d.year}"


def market_name(lang) -> str:
    m = config.MARKETS[lang]
    return m["uz"]


class Report:
    def __init__(self):
        self.blocks, self.findings, self.steps, self.health = [], [], [], []

    def h(self, text, level=1):
        self.blocks.append({"type": f"h{level}", "text": text})

    def p(self, text, style=None):
        self.blocks.append({"type": "p", "text": text, "style": style})

    def bullets(self, items):
        if items:
            self.blocks.append({"type": "bullets", "items": items})

    def table(self, header, rows, widths, align=None):
        self.blocks.append({"type": "table", "header": header, "rows": rows, "widths": widths, "align": align})

    def image(self, path, w, h, alt):
        self.blocks.append({"type": "image", "path": str(path), "w": w, "h": h, "alt": alt})


# ---------------------------------------------------------------- sections
def wiki_section(r: Report, df, wide):
    end = wide.index.max()
    days = pd.date_range(end - pd.Timedelta(days=6), end)
    langs = [l for l in config.DISTANT if l in wide.columns] + [l for l in ("en", "ru") if l in wide.columns]
    r.h("1. Vikipediya: kunlik qiziqish")
    r.p(f"Davr: {d_uz(days[0])} – {d_uz(end)}. Raqamlar — O'zbekiston, Samarqand, Buxoro, Xiva va Toshkent "
        "maqolalarining shu tildagi kunlik ko'rishlari yig'indisi. «Hafta o'zgarishi» — oldingi 7 kunga nisbatan; "
        "«4 haftalik me'yor» — oldingi 28 kun medianasiga nisbatan.")
    header = ["Bozor"] + [f"{HAFTA[d.weekday()]} {d.day}" for d in days] + ["Hafta jami", "Hafta o'zgarishi", "Me'yorga nisbatan"]
    rows, changes = [], []
    for l in langs:
        week = wide.loc[days, l]
        prev = wide.loc[days - pd.Timedelta(days=7), l]
        base = wide.loc[days[0] - pd.Timedelta(days=28): days[0] - pd.Timedelta(days=1), l].median() * 7
        ch = week.sum() / prev.sum() - 1 if prev.sum() > 0 else None
        vs = week.sum() / base - 1 if base and base > 0 else None
        if l in config.DISTANT and ch is not None and prev.sum() >= 350:   # >= 50 views/day: small markets are noise
            changes.append((l, ch, vs))
        rows.append([market_name(l) + (" (global)" if config.MARKETS[l]["flag"] == "🌐" else "")]
                    + [n(v) if pd.notna(v) else "—" for v in week]
                    + [n(week.sum()), pct(ch) if ch is not None else "—", pct(vs) if vs is not None else "—"])
    r.table(header, rows, [1500] + [700] * 7 + [1000, 1000, 1000], align="right")

    # unusual days
    unusual = []
    for d in days:
        for m in pageviews.movers(wide, d):
            if m["unusual"]:
                art = None
                sub = df[(df["date"] == d.date()) & (df["lang"] == m["lang"])]
                if not sub.empty:
                    art = sub.groupby("article")["views"].sum().idxmax()
                unusual.append(f"{d_uz(d)}, {market_name(m['lang'])}: {n(m['views'])} ko'rish "
                               f"(odatdagidan {pct(m['change'])}; eng ko'p o'qilgan: {art or '—'})")
    r.h("Odatdan tashqari kunlar", 2)
    if unusual:
        r.bullets(unusual)
        r.p("Bir kunlik sakrash ko'pincha yangilik, sport yoki havola tarqalishidan bo'ladi; turistlar sonini anglatmaydi.", "note")
    else:
        r.p("Bu hafta hech bir bozorda odatdan keskin farq qiladigan kun bo'lmadi (|z| ≥ 3 va ±15% chegarasi).")

    up, total = pageviews.trend_7d(wide)
    if changes:
        best = max(changes, key=lambda c: c[1])
        worst = min(changes, key=lambda c: c[1])
        r.findings.append(f"Vikipediya: kuzatilgan {total} ta tildan (qo'shnilarsiz) {up} tasida qiziqish o'tgan haftaga nisbatan oshdi. "
                          f"Eng ko'p o'sish — {market_name(best[0])} ({pct(best[1])}), eng ko'p pasayish — "
                          f"{market_name(worst[0])} ({pct(worst[1])}).")
    if unusual:
        r.findings.append(f"Haftada {len(unusual)} ta odatdan tashqari kun qayd etildi — sababini yangiliklardan tekshirish kerak.")
    return days


def wiki_chart(wide) -> Path:
    langs = [l for l in config.DISTANT if l in wide.columns]
    end = wide.index.max()
    sub = wide.loc[end - pd.Timedelta(days=12 * 7 - 1): end, langs].rolling(7, min_periods=4).mean().iloc[6:]
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    for l in langs:
        ax.plot(sub.index, sub[l], lw=1.6, label=market_name(l))
    ax.set_yscale("log")
    ax.set_ylabel("ko'rishlar / kun (7 kunlik o'rtacha)")
    ax.grid(alpha=.25)
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12))
    ax.set_title("So'nggi 12 hafta: uzoq bozorlarda Vikipediya qiziqishi", fontsize=11)
    fig.tight_layout()
    path = WORK / "wiki_12w.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def official_section(r: Report):
    r.h("2. Rasmiy statistika va prognoz")
    ytd = statuz.load()
    tot = ytd[ytd["country"] == "TOTAL"].sort_values(["year", "month"])
    if tot.empty:
        r.p("Rasmiy ma'lumot yo'q.")
        return None
    last = tot.iloc[-1]
    y, m = int(last.year), int(last.month)
    mon = statuz.monthly()
    this_m = mon[(mon.year == y) & (mon.month == m) & (mon.country == "TOTAL")]
    prev_y = mon[(mon.year == y - 1) & (mon.month == m) & (mon.country == "TOTAL")]
    lines = [f"Oxirgi rasmiy davr: {y} yil yanvar–{OY[m - 1]}. Yil boshidan {n(last.ytd)} xorijiy safar."]
    if not this_m.empty:
        line = f"{OY[m - 1].capitalize()} oyining o'zi: {n(this_m.arrivals.iloc[0])}"
        if not prev_y.empty:
            g = this_m.arrivals.iloc[0] / prev_y.arrivals.iloc[0] - 1
            line += f" (o'tgan yilning shu oyiga nisbatan {pct(g)})"
        lines.append(line + ".")
    prev_ytd = tot[(tot.year == y - 1) & (tot.month == m)]
    if not prev_ytd.empty:
        lines.append(f"Yil boshidan o'sish: {pct(last.ytd / prev_ytd.ytd.iloc[0] - 1)}.")
    r.bullets(lines)

    # top countries of the latest month
    c = mon[(mon.year == y) & (mon.month == m) & (mon.country != "TOTAL")].sort_values("arrivals", ascending=False).head(10)
    if not c.empty:
        r.h(f"{OY[m - 1].capitalize()} {y}: eng ko'p kelgan davlatlar", 2)
        r.table(["Davlat", "Kelganlar", "Aniqlik"],
                [[row.country, n(row.arrivals), "aniq" if row.exact else "≈ yaxlitlangan"] for row in c.itertuples()],
                [4200, 2400, 2400], align="right")

    f = forecast.build()
    bt = forecast.backtest()
    meth, yr = f.get("method"), None
    if meth:
        yr = f["years"][meth["year"]]
        r.h(f"{meth['year']} yil prognozi", 2)
        r.bullets([
            f"Yil yakuni: ≈ {n(yr['v'])} (oraliq {n(yr['lo'])} – {n(yr['hi'])}); {meth['through']} oyda {n(yr['ytd'])} kelgan.",
            f"Usul: qolgan oylar = o'tgan yilning shu oylari × oxirgi 3 oy o'sishi (×{meth['central']}).",
            "Oylik o'sish: " + ", ".join(f"{k[5:]}-oy ×{v}" for k, v in meth["ratios"].items()) + ".",
        ] + ([("Usul tekshiruvi: " + "; ".join(f"{b['year']}: {b['error_pct']:+.1f}%".replace("-", "−") for b in bt)
               + " (yil yakuni xatosi).")] if bt else []))
        rat = list(meth["ratios"].values())
        if len(rat) >= 4:
            trend = "sekinlashmoqda" if rat[-1] < rat[0] else "tezlashmoqda"
            r.findings.append(f"Rasmiy statistika: {y} yil yanvar–{OY[m - 1]} oylarida {n(last.ytd)} safar; oylik o'sish "
                              f"{trend} (×{rat[0]} dan ×{rat[-1]} gacha). Yil prognozi ≈ {n(yr['v'])}.")
    return {"y": y, "m": m}


def trends_section(r: Report):
    df = trends.load()
    if df.empty:
        return
    from .history import TRENDS_GEO
    df = df[df["geo"].isin(TRENDS_GEO) & (df["destination"] == "Uzbekistan")]
    df["period"] = df["period"].astype(str)
    snaps = sorted(p for p in df["period"].unique() if p.startswith("90d-"))
    if not snaps:
        return
    r.h("3. Google qidiruvlari: raqobatchilar orasidagi ulush")
    r.p("Har bir davlatda O'zbekiston, Qozog'iston, Qirg'iziston, Gruziya va Tojikiston haqidagi qidiruvlar 100% deb "
        "olinganda O'zbekiston ulushi (so'nggi 90 kun). Barcha qidiruvlar — sayohat bilan cheklanmaydi.")
    cur = df[df["period"] == snaps[-1]].set_index("geo")["share"]
    prev = df[df["period"] == snaps[-2]].set_index("geo")["share"] if len(snaps) > 1 else None
    year = str(date.today().year - 1)
    last_year = df[df["period"] == year].set_index("geo")["share"]
    rows = []
    for geo, name in TRENDS_GEO.items():
        if geo not in cur.index:
            continue
        rows.append([name.split(" ", 1)[1], f"{int(cur[geo])}%",
                     f"{int(prev[geo])}%" if prev is not None and geo in prev.index else "—",
                     f"{int(last_year[geo])}%" if geo in last_year.index else "—"])
    rows.sort(key=lambda x: -int(x[1][:-1]))
    r.table(["Davlat", f"Hozir ({snaps[-1][4:]})", "Oldingi o'lchov", f"{year} yil"], rows, [3600, 1800, 1800, 1800], align="right")
    far = [x for x in rows if x[0] not in ("Qozog'iston", "Rossiya")]
    if far:
        rows_f = far
        r.findings.append(f"Google qidiruvlari (uzoq bozorlar): O'zbekiston ulushi eng yuqori — {rows_f[0][0]} ({rows_f[0][1]}), "
                          f"eng past — {rows_f[-1][0]} ({rows_f[-1][1]}).")


def events_section(r: Report):
    r.h("4. Kutilayotgan voqealar (60 kun)")
    up = events.upcoming(days=60)
    if not up:
        r.p("Yaqin 60 kunda ro'yxatga olingan voqea yo'q. Botga yangi voqealarni yozing.")
        r.steps.append("Yaqin 2 oy uchun voqealar ro'yxati bo'sh — festival, reys va viza yangiliklarini botga qo'shing.")
        return
    rows = []
    for u in up:
        e = u["estimate"]
        w = e.get("info", {}) if isinstance(e, dict) else {}
        a = e.get("arr", {}) if isinstance(e, dict) else {}
        fmt = lambda x: (f"~{x['p']:.0%} ({x['k']}/{x['n']})" if x and x.get("p") is not None else "ma'lumot kam")  # noqa: E731
        rows.append([d_uz(u["date"]) + (" (taxminiy)" if u.get("precision") not in (None, "day") else ""),
                     u["title"], TYPE_UZ.get(u["type"], u["type"]), fmt(w), fmt(a)])
    r.table(["Sana", "Voqea", "Turi", "Qiziqish oshishi", "Turistlar oshishi"], rows, [1700, 3700, 1100, 1250, 1250])
    r.p("Ehtimollar — o'xshash o'tgan voqealar ulushi (o'lchangan holatlar soni qavsda), bashorat emas.", "note")
    soon = [u for u in up if u["days"] <= 31]
    for u in soon:
        r.steps.append(f"{d_uz(u['date'])}: «{u['title']}» — voqeadan keyin 7 kunlik Vikipediya reaksiyasi avtomatik o'lchanadi; "
                       "rasmiy oylik natija keyingi oy statistikasidan so'ng chiqadi.")


def news_section(r: Report, days):
    r.h("5. Yangiliklar")
    path = config.DATA / "predictions.csv"
    if not path.exists():
        r.p("Yangiliklar jurnali yo'q.")
        return
    p = pd.read_csv(path)
    p["date"] = pd.to_datetime(p["date"], errors="coerce")
    wk = p[(p["date"] >= days[0]) & (p["date"] <= days[-1] + pd.Timedelta(days=1))]
    if wk.empty:
        r.p("Bu hafta AI tanlagan yangilik bo'lmadi.")
        return
    cnt = wk["status"].value_counts().to_dict()
    r.p(f"AI tanlagan yangiliklar: {len(wk)} ta — kanalga chiqqan: {cnt.get('posted', 0)}, rad etilgan: "
        f"{cnt.get('rejected', 0)}, tasdiq kutmoqda: {cnt.get('pending', 0)}.")
    imp = {"positive": "▲", "negative": "▼", "mixed": "◆", "unclear": "?"}
    items = [f"{imp.get(str(x.impact), '?')} {x.headline} ({x.date:%d.%m})" for x in wk[wk["status"] == "posted"].itertuples()]
    r.bullets(items[:10])
    if cnt.get("pending", 0):
        r.steps.append(f"{cnt['pending']} ta yangilik tasdiq kutmoqda — botda ✅ yoki ❌ bosing.")


def health_section(r: Report, wide):
    r.h("6. Ma'lumotlar holati (diagnostika)")
    today = pd.Timestamp(date.today())
    rows = []
    lag = (today - wide.index.max()).days
    ok = lag <= 2
    rows.append(["Vikipediya", d_uz(wide.index.max()), "✓" if ok else f"⚠ {lag} kun kechikish"])
    if not ok:
        r.steps.append("Vikipediya ma'lumotlari 2 kundan ortiq yangilanmagan — GitHub Actions'da «Daily collect & post» jurnalini tekshiring.")
    tot = statuz.load()
    tot = tot[tot["country"] == "TOTAL"].sort_values(["year", "month"])
    if not tot.empty:
        y, m = int(tot.iloc[-1].year), int(tot.iloc[-1].month)
        nxt_y, nxt_m = (y, m + 1) if m < 12 else (y + 1, 1)
        due = pd.Timestamp(nxt_y + (nxt_m == 12), (nxt_m % 12) + 1, 20)   # usually by ~20th of the following month
        late = today > due
        rows.append(["stat.uz (oylik)", f"{y} yanvar–{OY[m - 1]}",
                     f"⚠ {OY[nxt_m - 1]} relizi kechikmoqda" if late else f"keyingisi: {OY[nxt_m - 1]} (≈ {d_uz(due)} gacha)"])
        r.steps.append(f"Keyingi rasmiy statistika: {nxt_y} yil yanvar–{OY[nxt_m - 1]} — taxminan {d_uz(due)} gacha; "
                       "chiqqach prognoz avtomatik yangilanadi.")
        note = str(tot.iloc[-1].note or "")
        if "CHECK FAILED" in note:
            rows.append(["stat.uz tekshiruvi", f"{y}-{m:02d}", "⚠ " + note.split("CHECK FAILED:", 1)[1][:60]])
    y = statuz.load_yearly()
    if not y.empty:
        rows.append(["SIAT (yillik)", str(int(y.year.max())), "✓"])
    t = trends.load()
    if not t.empty:
        snaps = sorted(p for p in t["period"].astype(str).unique() if p.startswith("90d-"))
        if snaps:
            age = (today - pd.Timestamp(snaps[-1][4:])).days
            rows.append(["Google Trends", snaps[-1][4:], "✓" if age <= 8 else f"⚠ {age} kun eski"])
            if age > 8:
                r.steps.append("Google Trends bir haftadan ortiq yangilanmagan — Google so'rovni bloklagan bo'lishi mumkin; "
                               "«Google Trends (manual run)» ni qo'lda ishga tushiring.")
    r.table(["Manba", "Oxirgi ma'lumot", "Holat"], rows, [2800, 2800, 3400])


# ---------------------------------------------------------------- build
def build(send=True) -> Path | None:
    df = pageviews.load()
    wide = pageviews.market_daily(df)
    if wide.empty:
        log.info("report: no data")
        return None
    WORK.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    r = Report()
    end = wide.index.max()
    days = wiki_section(r, df, wide)
    r.image(wiki_chart(wide), 600, 280, "So'nggi 12 hafta Vikipediya qiziqishi grafigi")
    official_section(r)
    trends_section(r)
    events_section(r)
    news_section(r, days)
    health_section(r, wide)
    r.steps += [
        "Dissertatsiya uchun: Google Trends ulushi keyingi yil turistlar o'zgarishini oldindan ko'rsatadimi — sinov o'tkazish.",
        "Chet elliklar O'zbekiston haqida nimani bilishini o'lchash uchun qisqa so'rovnoma (quiz) — hali qurilmagan.",
    ]

    title = f"O'zbekiston turizm monitori — haftalik hisobot"
    period = f"{d_uz(days[0])} – {d_uz(end)}"
    head = [{"type": "title", "text": title}, {"type": "subtitle", "text": period},
            {"type": "h1", "text": "Asosiy xulosalar"}, {"type": "bullets", "items": r.findings or ["Xulosa uchun ma'lumot yetarli emas."]},
            {"type": "h1", "text": "Keyingi qadamlar"}, {"type": "numbers", "items": r.steps},
            {"type": "pagebreak"}]
    tail = [{"type": "h1", "text": "Manbalar va usul"},
            {"type": "bullets", "items": [
                "Wikimedia Pageviews API (CC0) — kunlik ko'rishlar.",
                "O'zbekiston Milliy statistika qo'mitasi: stat.uz press-relizlari va SIAT ochiq ma'lumotlari (CC BY 4.0).",
                "Google Trends — mavzular bo'yicha qidiruv ulushi (nisbiy ko'rsatkich, son emas).",
                "Yangiliklar: kun.uz, gazeta.uz, UzDaily, Google News; AI (Gemini/Groq) baholaydi, siz tasdiqlaysiz.",
                "Xulosalar va qadamlar qat'iy qoidalar asosida raqamlardan avtomatik yoziladi (AI emas).",
                "Bog'liqlik sabab degani emas; Vikipediya va Google qiziqishi turistlar soni bilan bir xil emas."]},
            {"type": "p", "text": "Jonli sahifa: " + config.CHART_URL, "style": "note"}]
    doc = {"title": title, "period": period, "blocks": head + r.blocks + tail}
    jpath = WORK / "report.json"
    jpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    out = OUT_DIR / f"hisobot-{end:%Y-%m-%d}.docx"
    subprocess.run(["node", str(ROOT / "report" / "docx_report.js"), str(jpath), str(out)], check=True)
    (OUT_DIR / "latest.docx").write_bytes(out.read_bytes())
    log.info("report: wrote %s", out)
    if send and not dry_run() and admin_id():
        from .util import _tg
        with open(out, "rb") as f:
            _tg("sendDocument", {"chat_id": admin_id(),
                                 "caption": f"📄 Haftalik hisobot: {period}\nJonli sahifa: {config.CHART_URL}"},
                files={"document": (out.name, f)})
    return out


if __name__ == "__main__":
    build(send="--no-send" not in sys.argv)
