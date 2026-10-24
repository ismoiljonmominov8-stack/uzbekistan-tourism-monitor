"""Builds docs/index.html: every day of collected data in interactive charts, plus CSV downloads.
Published by GitHub Pages and rebuilt after each daily run."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import config, events, pageviews, statuz
from .util import log

DOCS = config.ROOT / "docs"
import shutil  # noqa: E402

# Libraries kept in the repo (vendor/), served next to the page: no outside CDN needed.
VENDOR = config.ROOT / "vendor"
VENDOR_JS = VENDOR / "plotly.min.js"
PLOTLY = "plotly.min.js"
LIBS = ["plotly.min.js", "d3.min.js", "topojson-client.min.js"]
MARKET_ISO = {"zh": "156", "ko": "410", "ja": "392", "de": "276", "tr": "792", "it": "380", "fr": "250", "hi": "356", "ru": "643"}
COLORS = {"zh": "#a23b2a", "ko": "#2f5d7c", "ja": "#c47f2c", "de": "#3d6b45", "tr": "#7a3b6b",
          "it": "#5b7f99", "fr": "#8a6d3b", "hi": "#c06a2b", "en": "#6e6e6e", "ru": "#9a9a9a"}


def _clean(v):
    return None if (isinstance(v, float) and pd.isna(v)) else v


def map_data(wide, proj, mon) -> dict:
    """Everything the world map needs: boundaries, arrivals by country and year, Wikipedia interest
    for the tracked markets, 2026 monthly arrivals, events and upcoming events per country."""
    topo = json.loads((VENDOR / "countries-110m.json").read_text(encoding="utf-8"))
    yearly = statuz.load_yearly()
    countries, name_to_iso = {}, {}
    if not yearly.empty:
        y = yearly[(yearly["country"] != "TOTAL") & (yearly["year"] >= 2016)].copy()
        y["code"] = y["code"].astype(str).str.zfill(3)
        for code, g in y.groupby("code"):
            first = g.iloc[0]
            countries[code] = {"n": first["name_uz"], "e": first["country"],
                               "y": {int(r.year): int(r.arrivals) for r in g.itertuples()}}
            name_to_iso[first["country"]] = code
    totals = {}
    if not yearly.empty:
        t = yearly[yearly["country"] == "TOTAL"]
        totals = {int(r.year): int(r.arrivals) for r in t.itertuples() if r.year >= 2016}

    markets = {}
    if not wide.empty:
        last = wide.index.max()
        win = slice(last - pd.Timedelta(days=29), last)
        ly = last - pd.DateOffset(years=1)
        win_ly = slice(ly - pd.Timedelta(days=29), ly)
        for lang, iso in MARKET_ISO.items():
            if lang not in wide.columns:
                continue
            v30, v30ly = float(wide.loc[win, lang].sum()), float(wide.loc[win_ly, lang].sum())
            share = share_ly = None
            if not proj.empty and lang in proj.columns:
                # MEDIAN daily share: one freak day (e.g. Japan, 30 Sep 2026) must not move the map
                d_now = (wide.loc[win, lang] / proj.loc[win, lang].reindex(wide.loc[win].index)).dropna()
                d_ly = (wide.loc[win_ly, lang] / proj.loc[win_ly, lang].reindex(wide.loc[win_ly].index)).dropna()
                share = float(d_now.median()) * 1e6 if len(d_now) >= 20 else None
                share_ly = float(d_ly.median()) * 1e6 if len(d_ly) >= 20 else None
            markets[iso] = {"lang": lang, "views30": int(v30), "share30": None if share is None else round(share, 1),
                            "change": None if not (share and share_ly) else round(share / share_ly - 1, 3),
                            "raw_change": None if not v30ly else round(v30 / v30ly - 1, 3)}

    monthly = {}
    if not mon.empty:
        m = mon[mon["year"] == mon["year"].max()]
        for country, g in m.groupby("country"):
            iso = name_to_iso.get(country)
            if iso:
                monthly[iso] = [{"m": f"{int(r.year)}-{int(r.month):02d}", "v": int(r.arrivals), "x": bool(r.exact)}
                                for r in g.sort_values("month").itertuples()]

    by_iso_effects = {}
    if events.EFFECTS.exists():
        for r in pd.read_csv(events.EFFECTS).to_dict("records"):
            iso = MARKET_ISO.get(r["lang"])
            if iso:
                by_iso_effects.setdefault(iso, []).append({k: _clean(v) for k, v in r.items()})
    ups = []
    for u in events.upcoming():
        langs = events.DISTANT if u["markets"] == "all" else u["markets"].split("|")
        ups.append(u | {"isos": [MARKET_ISO[l] for l in langs if l in MARKET_ISO],
                        "estimate": json.loads(json.dumps(u["estimate"], default=str))})
    return {"topo": topo, "countries": countries, "totals": totals, "markets": markets,
            "monthly": monthly, "effects": by_iso_effects, "upcoming": ups,
            "years": sorted(totals) if totals else []}


def build():
    df = pageviews.load()
    wide = pageviews.market_daily(df)
    if wide.empty:
        log.info("history: no data")
        return None
    DOCS.mkdir(exist_ok=True)
    proj = pageviews.project_wide()

    # downloadable CSVs
    out = wide.copy()
    out.columns = [config.MARKETS[c]["en"] for c in out.columns]
    out.index.name = "date"
    out.to_csv(DOCS / "daily_views_by_market.csv")
    arr = statuz.load()
    if not arr.empty:
        arr.drop(columns=["url"], errors="ignore").to_csv(DOCS / "official_arrivals_ytd.csv", index=False)
    mon = statuz.monthly()
    if not mon.empty:
        mon.to_csv(DOCS / "official_arrivals_monthly.csv", index=False)

    dates = [d.strftime("%Y-%m-%d") for d in wide.index]
    series = []
    for lang in wide.columns:
        info = config.MARKETS[lang]
        vals = wide[lang]
        share = None
        if not proj.empty and lang in proj.columns:
            p = proj[lang].reindex(wide.index)
            share = (vals / p * 1e6).round(2)  # views per million of that Wikipedia's views
        series.append({
            "lang": lang, "name": f"{info['flag']} {info['uz']}", "color": COLORS.get(lang, "#555"),
            "dash": "dot" if info["flag"] == "🌐" else "solid",
            "daily": [None if pd.isna(v) else int(v) for v in vals],
            "avg7": [None if pd.isna(v) else round(float(v), 1) for v in vals.rolling(7, min_periods=4).mean()],
            "share": None if share is None else [None if pd.isna(v) else round(float(v), 1) for v in share.rolling(7, min_periods=4).mean()],
        })

    monthly = {}
    if not mon.empty:
        mon = mon.copy()
        mon["period"] = mon["year"].astype(int).astype(str) + "-" + mon["month"].astype(int).map("{:02d}".format)
        # full month range so missing months show as gaps instead of straight lines across them
        months = pd.period_range(mon["period"].min(), mon["period"].max(), freq="M").astype(str).tolist()
        for country in ["TOTAL", "China", "Republic of Korea", "Türkiye", "India", "Germany", "Russia"]:
            sub = mon[mon["country"] == country].set_index("period")
            if len(sub):
                monthly[country] = {
                    "x": [f"{m}-01" for m in months],
                    "y": [int(sub.at[m, "arrivals"]) if m in sub.index else None for m in months],
                    "exact": [bool(sub.at[m, "exact"]) if m in sub.index else True for m in months]}

    ev_list, ev_rows, ev_summary = [], [], []
    evs = events.load_events()
    if not evs.empty:
        ev_list = [{"id": e.id, "date": e.date, "type": e.type, "title": e.title, "source": e.source,
                    "markets": e.markets} for e in evs.itertuples()]
        eff = pd.read_csv(events.EFFECTS) if events.EFFECTS.exists() else pd.DataFrame()
        for r in eff.to_dict("records"):
            clean = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()}
            clean["market"] = config.MARKETS.get(clean["lang"], {}).get("uz", clean["lang"])
            ev_rows.append(clean)
        if not eff.empty:
            ev_summary = events.summary_by_type(eff).to_dict("records")
            ev_summary = [{k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()}
                          for r in ev_summary]
        eff.to_csv(DOCS / "event_effects.csv", index=False)

    data = {"dates": dates, "series": series, "monthly": monthly, "map": map_data(wide, proj, mon),
            "events": ev_list, "effects": ev_rows, "ev_summary": ev_summary,
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "first": dates[0], "last": dates[-1]}
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))) \
                   .replace("__PLOTLY__", PLOTLY)
    path = DOCS / "index.html"
    path.write_text(html, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    for lib in LIBS:
        target = DOCS / lib
        if not target.exists() or target.stat().st_size != (VENDOR / lib).stat().st_size:
            shutil.copyfile(VENDOR / lib, target)
    log.info("history: wrote %s (%d days)", path, len(dates))
    return path


def standalone(out_path):
    """One self-contained HTML file (library inlined) that opens anywhere, even offline."""
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    for lib in LIBS:
        js = (VENDOR / lib).read_text(encoding="utf-8").replace("</script>", "<\\/script>")
        html = html.replace(f'<script src="{lib}"></script>', f"<script>{js}</script>", 1)
    html = html.replace('<a class="btn" id="offline"', '<a class="btn" style="display:none" id="offline"')
    out_path.write_text(html, encoding="utf-8")
    return out_path


TEMPLATE = r"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uzbekistan Tourism Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:wght@400;500&display=swap" rel="stylesheet">
<script src="plotly.min.js"></script>
<script src="d3.min.js"></script>
<script src="topojson-client.min.js"></script>
<style>
:root{--paper:#f3ead7;--paper2:#ebdfc4;--ink:#2b2117;--muted:#6b5a45;--rule:#b9a27c;--accent:#8c3b22;--card:#f8f1e1}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--paper:#1f1a14;--paper2:#2a231b;--ink:#efe4cf;--muted:#b9a88c;--rule:#5a4a35;--accent:#d98a5f;--card:#262019}}
:root[data-theme="dark"]{--paper:#1f1a14;--paper2:#2a231b;--ink:#efe4cf;--muted:#b9a88c;--rule:#5a4a35;--accent:#d98a5f;--card:#262019}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 "EB Garamond",Georgia,serif;
  background-image:radial-gradient(circle at 20% 10%,rgba(140,59,34,.05),transparent 40%),radial-gradient(circle at 80% 90%,rgba(61,107,69,.05),transparent 40%)}
.wrap{max-width:1100px;margin:0 auto;padding:28px 16px 60px}
header{border-bottom:3px double var(--rule);padding-bottom:14px;margin-bottom:22px}
h1{font:700 clamp(28px,5vw,44px)/1.1 "Cormorant Garamond",serif;margin:0;letter-spacing:.02em}
h1 small{display:block;font-size:.45em;font-weight:500;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin-top:6px}
h2{font:600 26px/1.2 "Cormorant Garamond",serif;margin:0 0 4px}
.meta{color:var(--muted);font-size:15px}
section{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:18px 18px 10px;margin:0 0 22px;
  box-shadow:0 1px 0 var(--paper2) inset}
.note{color:var(--muted);font-size:15px;margin:2px 0 10px}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 6px}
button,.btn{font:500 15px "EB Garamond",serif;background:transparent;color:var(--ink);border:1px solid var(--rule);
  border-radius:3px;padding:5px 11px;cursor:pointer;text-decoration:none}
button.on{background:var(--accent);color:var(--paper);border-color:var(--accent)}
.chart{width:100%;height:460px}
.downloads{display:flex;flex-wrap:wrap;gap:8px}
table{border-collapse:collapse;width:100%;font-size:15px;margin-top:10px}
th,td{border-bottom:1px solid var(--rule);padding:6px 8px;text-align:left;vertical-align:top}
th{font-weight:600;color:var(--muted)}
tr.mixed td{color:var(--muted);opacity:.7}
#events-box a,#upcoming-box a{color:var(--accent)}
.pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:13px;border:1px solid var(--rule)}
.up{background:#3d6b4522}.down{background:#a23b2a22}
.sect{font:600 30px/1.2 "Cormorant Garamond",serif;margin:30px 0 12px;border-bottom:1px solid var(--rule);padding-bottom:6px}
.yearrow{display:flex;align-items:center;gap:10px;margin:4px 0 8px}
.yearrow input{flex:1;max-width:360px;accent-color:var(--accent)}
.mapgrid{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:16px;align-items:start}
.mapwrap{position:relative;border:1px solid var(--rule);border-radius:3px;background:#e7dcc3;overflow:hidden}
#map{width:100%;height:auto;display:block;cursor:grab}
#map .land{stroke:#8d7a5b;stroke-width:.4;vector-effect:non-scaling-stroke}
#map .land.nodata{fill:#efe6d2}
#map .land.sel{stroke:var(--ink);stroke-width:1.6}
#map .land.uzb{fill:var(--accent) !important;stroke:var(--ink);stroke-width:1.2}
#map .grat{fill:none;stroke:#b9a27c55;stroke-width:.5;vector-effect:non-scaling-stroke}
#map .sphere{fill:#dfe3d6}
.tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--rule);padding:6px 9px;font-size:14px;border-radius:3px;box-shadow:0 2px 8px #0002;max-width:240px}
.legend{position:absolute;left:10px;bottom:10px;background:#f8f1e1e6;border:1px solid var(--rule);padding:6px 8px;font-size:12px;border-radius:3px;color:#2b2117}
.legend .bar{height:9px;width:180px;border:1px solid #8d7a5b}
.legend .ticks{display:flex;justify-content:space-between;width:180px}
.panel{border:1px solid var(--rule);border-radius:3px;padding:12px 14px;background:var(--card);min-height:300px}
.panel h3{font:700 24px/1.15 "Cormorant Garamond",serif;margin:0 0 6px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;font-size:15px;margin:6px 0 8px}
.kv dt{color:var(--muted)}.kv dd{margin:0;text-align:right;font-variant-numeric:tabular-nums}
.mini{height:170px}
.evlist{font-size:14px;margin:6px 0 0;padding-left:18px}
.evlist li{margin-bottom:5px}
details summary{cursor:pointer;list-style:none}
details summary::before{content:"▸ ";color:var(--accent);font-size:22px}
details[open] summary::before{content:"▾ "}
.exp{width:100%;font-size:14px;margin-top:6px}.exp td,.exp th{padding:3px 6px}
.upcard{border:1px solid var(--rule);border-radius:3px;padding:10px 12px;margin:0 0 10px;background:var(--card)}
.upcard .p{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;align-items:center;font-size:15px;margin-top:6px}
.meter{height:9px;background:var(--paper2);border:1px solid var(--rule);border-radius:5px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--accent)}
code{font-size:14px;background:var(--paper2);padding:1px 4px;border-radius:3px}
@media (max-width:800px){.mapgrid{grid-template-columns:1fr}.legend{position:static;border:0;border-top:1px solid #8d7a5b;border-radius:0}}
footer{color:var(--muted);font-size:14px;border-top:1px solid var(--rule);padding-top:12px}
@media (max-width:600px){.chart{height:620px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Uzbekistan Tourism Monitor<small>O'zbekistonga xalqaro qiziqish — har bir kun</small></h1>
  <div class="meta" id="meta"></div>
</header>

<section id="upcoming-box">
  <h2>Kutilayotgan voqealar va ularning kutilgan ta'siri</h2>
  <p class="note">Telegram botga <code>/event SANA | TURI | DAVLATLAR | NOMI | HAVOLA</code> yuboring yoki yangilikni ✅ bilan tasdiqlang. Ehtimollar — o'tgan o'lchangan o'xshash voqealarga asoslangan ulush, bashorat emas. Voqea o'tgach, haqiqiy ta'sir o'zi o'lchanadi.</p>
  <div id="upcoming"></div>
</section>

<section id="map-box">
  <h2>Dunyo xaritasi — O'zbekistonga kim keladi va kim qiziqadi</h2>
  <p class="note">Mamlakatni bosing — yonida (telefonda pastida) uning statistikasi, grafiklari va voqealari chiqadi. Xaritani surish va kattalashtirish mumkin.</p>
  <div class="controls" id="metric-btns">
    <button data-metric="arrivals" class="on">Turistlar soni</button>
    <button data-metric="growth">O'sish (oldingi yilga)</button>
    <button data-metric="share">Vikipediya qiziqishi</button>
    <button data-metric="change">Qiziqish o'zgarishi (yillik)</button>
  </div>
  <div class="yearrow" id="yearrow"><span>Yil:</span><input type="range" id="year" step="1"><b id="yearlbl"></b></div>
  <div class="mapgrid">
    <div class="mapwrap"><svg id="map" role="img" aria-label="Dunyo xaritasi"></svg>
      <div id="tip" class="tip" hidden></div><div id="legend" class="legend"></div></div>
    <aside id="panel" class="panel"></aside>
  </div>
</section>



<h2 class="sect">Batafsil grafiklar</h2>
<section>
  <h2>Vikipediya ko'rishlari — har kuni</h2>
  <p class="note">O'zbekiston, Samarqand, Buxoro, Xiva, Toshkent sahifalari, har bir til = bir bozor. Yuqoridagi kamera belgisi grafikni PNG qilib yuklaydi.</p>
  <div class="controls">
    <button data-mode="avg7" class="on">7 kunlik o'rtacha</button>
    <button data-mode="daily">Kunlik (har bir kun)</button>
    <button data-scale="log" class="on">Log shkala</button>
    <button data-scale="linear">Oddiy shkala</button>
  </div>
  <div id="views" class="chart"></div>
</section>

<section id="share-box">
  <h2>Qiziqish ulushi (Vikipediya trafigiga nisbatan)</h2>
  <p class="note">Har 1 million Vikipediya ko'rishidan nechtasi O'zbekiston sahifalariga to'g'ri keladi (7 kunlik o'rtacha). Vikipediyaning umumiy trafigi kamayib borayotgani sababli uzoq muddatli taqqoslash uchun shu grafik to'g'riroq.</p>
  <div id="share" class="chart"></div>
</section>

<section>
  <h2>Rasmiy statistika — oyma-oy kelgan turistlar</h2>
  <p class="note">Manba: O'zbekiston Milliy statistika qo'mitasi (yil boshidan jamlangan raqamlardan hisoblangan). Ochiq nuqtalar — manbada yaxlitlangan (≈) raqamlar.</p>
  <div id="arrivals" class="chart"></div>
</section>

<section id="events-box">
  <details>
  <summary><h2 style="display:inline">Tarixiy asos: o'tgan voqealar ta'siri</h2></summary>
  <p class="note"><b>Nega eski voqealar?</b> Kutilayotgan voqea qanday ta'sir qilishini faqat o'xshash o'tgan voqealar natijasidan bilish mumkin. Yuqoridagi ehtimollar va raqamlar shu jadvaldan hisoblanadi.</p>
  <p class="note">Har bir voqea (viza, reys, tadbir, sport...) uchun: <b>Vikipediya</b> — keyingi 7 kunda qiziqish odatdagidan necha baravar;
  <b>turistlar</b> — o'sha davlatdan kelganlar o'zgarishi, umumiy oqimga nisbatan ("farq": ×1,2 dan yuqori = ko'proq o'sdi).
  Bu bog'liqlik, isbot emas. Oylik natijalar boshqa yilning xuddi shu oylari bilan solishtirib mavsumdan tozalanadi. Kulrang qatorlar — boshqa voqealar bilan aralash, COVID davri yoki mavsum tekshirib bo'lmagan; xulosaga qo'shilmaydi.</p>
  <div id="ev-summary"></div>
  <div style="overflow-x:auto"><table id="ev-table"></table></div>
  </details>
</section>

<section>
  <h2>Ma'lumotlarni yuklab olish</h2>
  <div class="downloads">
    <a class="btn" href="daily_views_by_market.csv" download>Kunlik ko'rishlar (bozorlar bo'yicha), CSV</a>
    <a class="btn" href="https://raw.githubusercontent.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor/main/data/pageviews_daily.csv">Kunlik ko'rishlar (sahifalar bo'yicha), CSV</a>
    <a class="btn" href="official_arrivals_monthly.csv" download>Rasmiy statistika (oylik), CSV</a>
    <a class="btn" href="official_arrivals_ytd.csv" download>Rasmiy statistika (yil boshidan), CSV</a>
    <a class="btn" href="event_effects.csv" download>Voqealar ta'siri, CSV</a>
    <a class="btn" id="offline" href="#">Grafiklar — oflayn HTML fayl (internetsiz ochiladi)</a>
  </div>
</section>

<footer>
  Manbalar: Wikimedia Pageviews API (CC0); O'zbekiston Milliy statistika qo'mitasi, stat.uz (CC BY 4.0).
  Bir kunlik keskin sakrashlar (masalan, 2026-yil 30-sentabr, Yaponiya) avtomatik trafik yoki tarqalgan havola bo'lishi mumkin — tahlilda chetlab o'ting.
</footer>
</div>

<script>
if (typeof Plotly === "undefined") {
  document.querySelectorAll(".chart").forEach(c => c.innerHTML =
    '<p style="padding:20px">Grafik kutubxonasi yuklanmadi. Sahifani brauzerda (Chrome/Safari) oching yoki oflayn faylni yuklab oling.</p>');
}
const D = __DATA__;
document.getElementById("meta").textContent =
  `${D.first} — ${D.last} · ${D.dates.length.toLocaleString()} kun · yangilangan ${D.updated}`;
const NARROW = window.innerWidth < 600;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function layout(ytitle, ylog){
  return {paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{family:"EB Garamond, Georgia, serif", color:css("--ink"), size:14},
    margin: NARROW ? {l:46,r:8,t:10,b:230} : {l:58,r:12,t:10,b:40}, hovermode:"x unified",
    legend: NARROW ? {orientation:"h", x:0, y:-0.12, yanchor:"top", font:{size:12}} : {orientation:"h", y:-0.18},
    xaxis:{gridcolor:css("--rule")+"55", rangeslider:{visible:true, thickness:0.06},
      rangeselector:{bgcolor:css("--paper2"), activecolor:css("--accent"), font:{color:css("--ink")},
        buttons:[{count:1,label:"1 oy",step:"month",stepmode:"backward"},{count:6,label:"6 oy",step:"month",stepmode:"backward"},
                 {count:1,label:"1 yil",step:"year",stepmode:"backward"},{count:3,label:"3 yil",step:"year",stepmode:"backward"},
                 {step:"all",label:"Hammasi"}]}},
    yaxis:{title:ytitle, gridcolor:css("--rule")+"55", type: ylog ? "log" : "linear"}};
}
const cfg = {responsive:true, displaylogo:false,
  toImageButtonOptions:{format:"png", filename:"uzbekistan_tourism_monitor", width:1600, height:800, scale:2}};
let mode = "avg7", scale = "log";
function drawViews(){
  const tr = D.series.map(s => ({x:D.dates, y:s[mode], name:s.name, type:"scattergl", mode:"lines",
    line:{color:s.color, width: mode==="daily" ? 1 : 1.8, dash:s.dash}}));
  const L = layout("ko'rishlar / kun", scale==="log");
  L.shapes = (D.events||[]).map(e => ({type:"line", xref:"x", yref:"paper", x0:e.date, x1:e.date, y0:0, y1:1,
    line:{color:css("--accent"), width:1, dash:"dot"}}));
  L.annotations = (D.events||[]).map((e,i) => ({x:e.date, y:1, yref:"paper", text:e.id, showarrow:false,
    font:{size:10, color:css("--accent")}, yshift: (i%2)*12 - 2, hovertext:e.title}));
  Plotly.react("views", tr, L, cfg);
}
function drawShare(){
  const has = D.series.some(s => s.share && s.share.some(v => v !== null));
  if (!has) { document.getElementById("share-box").style.display = "none"; return; }
  const tr = D.series.filter(s => s.share).map(s => ({x:D.dates, y:s.share, name:s.name, type:"scattergl",
    mode:"lines", line:{color:s.color, width:1.6, dash:s.dash}}));
  Plotly.react("share", tr, layout("1 mln ko'rishga", true), cfg);
}
function drawArrivals(){
  const names = {"TOTAL":"Jami","China":"🇨🇳 Xitoy","Republic of Korea":"🇰🇷 Koreya","Türkiye":"🇹🇷 Turkiya",
                 "India":"🇮🇳 Hindiston","Germany":"🇩🇪 Germaniya","Russia":"🇷🇺 Rossiya"};
  const tr = Object.entries(D.monthly).map(([k,v]) => ({x:v.x, y:v.y, name:names[k]||k, type:"scatter",
    mode:"lines+markers", yaxis: k==="TOTAL" ? "y2" : "y", connectgaps:false,
    marker:{symbol:v.exact.map(e => e ? "circle" : "circle-open"), size:8},
    line:{width: k==="TOTAL" ? 3 : 1.6, dash: k==="TOTAL" ? "dash" : "solid"}}));
  const L = layout("turistlar / oy (davlatlar)", false);
  L.xaxis = {gridcolor:css("--rule")+"55", type:"date", tickformat:"%Y-%m", dtick:"M2"};
  L.yaxis.rangemode = "tozero";
  L.yaxis2 = {title:"jami / oy", overlaying:"y", side:"right", showgrid:false, rangemode:"tozero"};
  L.margin.r = 60;
  Plotly.react("arrivals", tr, L, cfg);
}
document.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => {
  mode = b.dataset.mode; document.querySelectorAll("[data-mode]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });
document.querySelectorAll("[data-scale]").forEach(b => b.onclick = () => {
  scale = b.dataset.scale; document.querySelectorAll("[data-scale]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });
if (typeof Plotly !== "undefined") { drawViews(); drawShare(); drawArrivals(); }
(function worldMap(){
  if (typeof d3 === "undefined" || typeof topojson === "undefined" || !D.map) { document.getElementById("map-box").style.display = "none"; return; }
  const M = D.map, svg = d3.select("#map"), W = 960, H = 500;
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  const proj = d3.geoNaturalEarth1().fitExtent([[6, 6], [W - 6, H - 6]], {type: "Sphere"});
  const path = d3.geoPath(proj);
  const g = svg.append("g");
  g.append("path").attr("class", "sphere").attr("d", path({type: "Sphere"}));
  g.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule10()));
  const feats = topojson.feature(M.topo, M.topo.objects.countries).features;
  const years = M.years.length ? M.years : [2025];
  let metric = "arrivals", year = years[years.length - 1], selected = "156";
  const slider = document.getElementById("year");
  slider.min = years[0]; slider.max = years[years.length - 1]; slider.value = year;
  const fmt = d3.format(",d"), pct = d3.format("+.0%");
  const nm = id => (M.countries[id] && M.countries[id].n) || (feats.find(f => f.id === id) || {properties:{}}).properties.name || id;
  const MARKET_ISO_JS = {zh:"156", ko:"410", ja:"392", de:"276", tr:"792", it:"380", fr:"250", hi:"356", ru:"643"};
  const MK = {zh:"🇨🇳", ko:"🇰🇷", ja:"🇯🇵", de:"🇩🇪", tr:"🇹🇷", it:"🇮🇹", fr:"🇫🇷", hi:"🇮🇳", ru:"🇷🇺"};
  const warm = d3.interpolateRgbBasis(["#f3e6c8", "#e2c38d", "#c98e52", "#a3542c", "#6e2814"]);
  const div = d3.interpolateRgbBasis(["#8c3b22", "#d9a77c", "#f3ead7", "#9bbf8f", "#2f6b3f"]);
  function value(id){
    const c = M.countries[id];
    if (metric === "arrivals") return c && c.y[year] > 0 ? c.y[year] : null;
    if (metric === "growth") { if (!c || !(c.y[year] > 0) || !(c.y[year-1] > 0)) return null; return c.y[year] / c.y[year-1]; }
    const m = M.markets[id]; if (!m) return null;
    return metric === "share" ? m.share30 : (m.change == null ? null : 1 + m.change);
  }
  function scale(){
    const vals = feats.map(f => value(f.id)).filter(v => v != null && v > 0);
    if (metric === "arrivals") { const s = d3.scaleSequentialLog([10, d3.max(vals) || 10], warm); return s; }
    if (metric === "share") { return d3.scaleSequentialLog([Math.max(1, d3.min(vals) || 1), d3.max(vals) || 10], warm); }
    const s = d3.scaleDivergingLog([0.25, 1, 4], div).clamp(true); return s;
  }
  const lands = g.append("g").selectAll("path").data(feats).join("path")
    .attr("class", d => "land" + (d.id === "860" ? " uzb" : "")).attr("d", path)
    .on("mousemove", (ev, d) => tip(ev, d)).on("mouseleave", () => { document.getElementById("tip").hidden = true; })
    .on("click", (ev, d) => { selected = d.id; paint(); panel(); });
  svg.call(d3.zoom().scaleExtent([1, 8]).translateExtent([[0, 0], [W, H]]).on("zoom", e => g.attr("transform", e.transform)));
  function label(v){
    if (v == null) return "ma'lumot yo'q";
    if (metric === "arrivals") return fmt(v) + " turist";
    if (metric === "growth") return pct(v - 1) + " oldingi yilga";
    if (metric === "share") return v.toFixed(1) + " / 1 mln ko'rish";
    return pct(v - 1) + " (o'tgan yilga)";
  }
  function tip(ev, d){
    const t = document.getElementById("tip"), box = document.querySelector(".mapwrap").getBoundingClientRect();
    t.innerHTML = `<b>${nm(d.id)}</b><br>${d.id === "860" ? "O'zbekiston" : label(value(d.id))}`;
    t.hidden = false; t.style.left = Math.min(ev.clientX - box.left + 12, box.width - 200) + "px"; t.style.top = (ev.clientY - box.top + 12) + "px";
  }
  function paint(){
    const sc = scale();
    lands.attr("fill", d => { const v = value(d.id); return v == null ? null : sc(v); })
         .classed("nodata", d => value(d.id) == null).classed("sel", d => d.id === selected);
    lands.filter(d => d.id === selected).raise();
    document.getElementById("yearrow").style.display = (metric === "arrivals" || metric === "growth") ? "flex" : "none";
    document.getElementById("yearlbl").textContent = year + (metric === "growth" ? ` (${year-1} ga nisbatan)` : "");
    legend(sc);
  }
  function legend(sc){
    const el = document.getElementById("legend"), dom = sc.domain(), n = 6;
    const stops = d3.range(n).map(i => { const v = metric === "arrivals" || metric === "share"
      ? Math.exp(Math.log(dom[0]) + i/(n-1) * (Math.log(dom[dom.length-1]) - Math.log(dom[0])))
      : Math.exp(Math.log(0.25) + i/(n-1) * Math.log(16)); return v; });
    const grad = stops.map((v,i) => `${sc(v)} ${i/(n-1)*100}%`).join(",");
    const ticks = metric === "arrivals" ? [stops[0], stops[n-1]].map(v => d3.format(".2s")(v))
      : metric === "share" ? [stops[0], stops[n-1]].map(v => v.toFixed(0)) : ["−75%", "0", "+300%"];
    const title = {arrivals:`Turistlar, ${year}`, growth:`O'sish, ${year}`, share:"Vikipediya: 1 mln ko'rishga (30 kunlik mediana)", change:"Qiziqish o'zgarishi"}[metric];
    el.innerHTML = `<div>${title}</div><div class="bar" style="background:linear-gradient(90deg,${grad})"></div><div class="ticks">${ticks.map(t=>`<span>${t}</span>`).join("")}</div>` +
      (metric === "share" || metric === "change" ? "<div style='margin-top:3px'>Faqat kuzatilayotgan 9 bozor</div>" : "");
  }
  function panel(){
    const id = selected, c = M.countries[id], m = M.markets[id], el = document.getElementById("panel");
    if (id === "860") { el.innerHTML = `<h3>O'zbekiston</h3><p class="note">Jami xorijiy turistlar:</p><dl class="kv">${Object.entries(M.totals).map(([y,v])=>`<dt>${y}</dt><dd>${fmt(v)}</dd>`).join("")}</dl>`; return; }
    let h = `<h3>${MK[m && m.lang] || ""} ${nm(id)}</h3><dl class="kv">`;
    if (c) {
      const ly = years[years.length-1], v = c.y[ly], v0 = c.y[ly-1], share = M.totals[ly] ? v / M.totals[ly] : null;
      h += `<dt>Turistlar ${ly}</dt><dd>${v ? fmt(v) : "—"}</dd>`;
      if (v0) h += `<dt>${ly-1} ga nisbatan</dt><dd>${pct(v / v0 - 1)}</dd>`;
      if (share) h += `<dt>Jami oqimdagi ulushi</dt><dd>${(share*100).toFixed(2)}%</dd>`;
    } else h += `<dt>Turistlar</dt><dd>ma'lumot yo'q</dd>`;
    const mm = M.monthly[id];
    if (mm && mm.length) h += `<dt>${mm[0].m.slice(0,4)}: ${mm.length} oyda</dt><dd>${fmt(d3.sum(mm, x => x.v))}</dd>`;
    if (m) {
      h += `<dt>Vikipediya, 30 kun</dt><dd>${fmt(m.views30)} ko'rish</dd>`;
      if (m.share30 != null) h += `<dt>1 mln ko'rishga (mediana)</dt><dd>${m.share30}</dd>`;
      if (m.change != null) h += `<dt>Qiziqish, yillik</dt><dd>${pct(m.change)}</dd>`;
    }
    h += `</dl><div id="mini1" class="mini"></div>`;
    if (m) h += `<div id="mini2" class="mini"></div>`;
    const effs = (M.effects[id] || []);
    const ups = (M.upcoming || []).filter(u => u.isos.includes(id));
    if (effs.length) h += `<b>O'tgan voqealar</b><ul class="evlist">` + effs.map(e => `<li>${e.date}: ${e.title} — Vikipediya ${e.wiki_ratio == null ? "—" : "×" + e.wiki_ratio}, turistlar ${e.excess == null ? "kutilmoqda" : "×" + e.excess}${(e.arr_verdict||"").includes("(") ? " <i>(ishonchsiz)</i>" : ""}</li>`).join("") + `</ul>`;
    if (ups.length) h += `<b>Kutilayotgan</b><ul class="evlist">` + ups.map(u => `<li>${u.date}: ${u.title} — ${pp(u.estimate.info)} qiziqish, ${pp(u.estimate.arr)} turistlar</li>`).join("") + `</ul>`;
    if (!m) h += `<p class="note">Bu mamlakat uchun Vikipediya qiziqishi kuzatilmaydi (faqat 9 bozor).</p>`;
    el.innerHTML = h;
    if (typeof Plotly === "undefined") return;
    // a fresh layout object per chart: Plotly writes axis ranges into the object it is given
    const mini = (title, xtype) => ({paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)", margin:{l:44,r:6,t:22,b:26},
      font:{family:"EB Garamond, Georgia, serif", size:12, color:css("--ink")}, showlegend:false,
      title:{text:title, font:{size:13}}, xaxis:{type:xtype, gridcolor:css("--rule")+"44"},
      yaxis:{gridcolor:css("--rule")+"44", rangemode:"tozero"}});
    if (c) { const L1 = mini("Turistlar, yillar bo'yicha", "linear"); L1.xaxis.dtick = 2; L1.xaxis.tickformat = "d";
      Plotly.react("mini1", [{type:"bar", x:Object.keys(c.y).map(Number), y:Object.values(c.y), marker:{color:"#a3542c"}}],
      L1, {displayModeBar:false, responsive:true}); }
    if (m) { const s = D.series.find(x => x.lang === m.lang), n = 730;
      Plotly.react("mini2", [{type:"scatter", mode:"lines", x:D.dates.slice(-n), y:s.avg7.slice(-n), line:{color:"#2f5d7c", width:1.4}}],
      mini("Vikipediya, 7 kunlik o'rtacha (2 yil)", "date"), {displayModeBar:false, responsive:true}); }
  }
  function pp(x){ return x && x.p != null ? "~" + Math.round(x.p*100) + "%" : "ma'lumot yetarli emas"; }
  document.querySelectorAll("[data-metric]").forEach(b => b.onclick = () => { metric = b.dataset.metric;
    document.querySelectorAll("[data-metric]").forEach(x => x.classList.toggle("on", x === b)); paint(); });
  slider.oninput = () => { year = +slider.value; paint(); };
  paint(); panel();

  // upcoming events list
  const box = document.getElementById("upcoming"), U = M.upcoming || [];
  const sg = v => (v > 0 ? "+" : v < 0 ? "−" : "±") + fmt(Math.abs(v));
  function expect(u){
    const x = u.estimate.expected || {};
    if (!x.markets || !Object.keys(x.markets).length) return `<p class="note">🔢 Turistlar soniga ta'sir: o'xshash voqealar yetarli emas (${x.n||0} ta).</p>`;
    const rows = Object.entries(x.markets).sort((a,b) => b[1].base_month - a[1].base_month).map(([l,m]) =>
      `<tr><td>${MK[l]||""} ${nm(MARKET_ISO_JS[l])}</td><td>${fmt(m.base_month)}</td><td><b>${sg(m.mid)}</b></td><td>${sg(m.low)} … ${sg(m.high)}</td><td class="note">${m.basis}</td></tr>`).join("");
    const concl = x.q25 > 1.05 ? "Shu turdagi voqealar odatda turistlar oqimini oshirgan." : "Shu turdagi voqealar odatda turistlar sonini sezilarli o'zgartirmagan.";
    return `<p style="margin:8px 0 0"><b>🔢 Turistlar soniga kutilgan ta'sir, oyiga</b> <span class="note">(${x.n} ta o'xshash voqea; o'rtacha natija va o'rtadagi yarmining oralig'i)</span></p>` +
      `<table class="exp"><tr><th>Bozor</th><th>Hozir/oy</th><th>Kutilgan</th><th>Oraliq</th><th>Asos</th></tr>${rows}</table><p class="note" style="margin:4px 0 0">${concl}</p>`;
  }
  const tn = {visa:"viza", flight:"reys", event:"tadbir", sport:"sport", politics:"siyosat", price:"narx", infrastructure:"infratuzilma", marketing:"marketing", other:"boshqa"};
  const conf = {low:"past", medium:"o'rta", high:"yuqori"};
  const row = (label, x) => x && x.p != null
    ? `<span>${label}</span><span><div class="meter"><i style="width:${Math.round(x.p*100)}%"></i></div> <b>~${Math.round(x.p*100)}%</b> — ${x.k}/${x.n} o'xshash holatda (ishonch: ${conf[x.conf]})</span>`
    : `<span>${label}</span><span>ma'lumot yetarli emas (${x ? x.n : 0} ta o'xshash voqea)</span>`;
  box.innerHTML = U.length ? U.map(u => `<div class="upcard"><b>${u.title}</b><div class="note">${u.date} · ${u.days} kundan keyin · ${tn[u.type]||u.type} · ` +
      `${u.markets === "all" ? "barcha uzoq bozorlar" : u.isos.map(nm).join(", ")}${u.source ? ` · <a href="${u.source}" target="_blank" rel="noopener">manba</a>` : ""}</div>` +
      `<div class="p">${row("📖 Ma'lumot qidirish", u.estimate.info)}${row("🧳 Turistlar kelishi", u.estimate.arr)}</div>` + expect(u) + `</div>`).join("")
    : `<p class="note">Hozircha kutilayotgan voqea yo'q.</p>`;
})();
(function renderEvents(){
  const box = document.getElementById("events-box");
  if (!D.effects || !D.effects.length) { box.style.display = "none"; return; }
  const tn = {visa:"viza", flight:"reys", event:"tadbir", sport:"sport", politics:"siyosat", price:"narx",
              infrastructure:"infratuzilma", marketing:"marketing", other:"boshqa"};
  const wv = {strong:"kuchli", some:"biroz", none:"yo'q"};
  const av = v => (!v || v === "—") ? "kutilmoqda" : v.startsWith("rose") ? "ko'proq o'sdi" : v.startsWith("fell") ? "kamaydi" : "aniq o'zgarish yo'q";
  const esc = x => String(x ?? "").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
  const src = Object.fromEntries((D.events||[]).map(e => [e.id, e.source]));
  let h = "<tr><th>Voqea</th><th>Sana</th><th>Turi</th><th>Bozor</th><th>Vikipediya, 7 kun</th><th>Turistlar (oldin → keyin)</th><th>Farq</th><th>Natija</th></tr>";
  for (const r of D.effects) {
    const mixed = (r.arr_verdict||"").includes("(");
    const wiki = r.wiki_ratio == null ? "—" : `×${r.wiki_ratio} (${wv[r.wiki_verdict]||"—"})`;
    const arr = r.arr_before == null ? "kutilmoqda" : `${Math.round(r.arr_before).toLocaleString()} → ${Math.round(r.arr_after).toLocaleString()}` +
      (r.arr_method === "monthly" ? " /oy" : ` (${esc((r.arr_window||"").split(" (")[0])})`);
    const ex = r.excess == null ? "—" : `<span class="pill ${r.excess>=1.2?"up":r.excess<=0.83?"down":""}">×${r.excess}</span>`;
    const v = r.arr_verdict||"";
    const note = v.includes("mixed") ? " — boshqa voqea bilan aralash" : v.includes("COVID") ? " — COVID davri"
               : v.includes("season") ? " — mavsum hisobga olinmagan" : (r.season_year ? ` (mavsum: ${r.season_year})` : "");
    h += `<tr class="${mixed?"mixed":""}"><td><a href="${esc(src[r.id])}" target="_blank" rel="noopener">${esc(r.title)}</a></td><td>${esc(r.date)}</td>` +
         `<td>${tn[r.type]||esc(r.type)}</td><td>${esc(r.market)}</td><td>${wiki}</td><td>${arr}</td><td>${ex}</td><td>${av(r.arr_verdict)}${note}</td></tr>`;
  }
  document.getElementById("ev-table").innerHTML = h;
  let s = "<table><tr><th>Turi</th><th>Voqealar</th><th>Vikipediya reaksiyasi</th><th>Turistlar ko'proq o'sgan</th><th>O'rtacha farq</th></tr>";
  for (const r of (D.ev_summary||[])) s += `<tr><td>${tn[r.type]||esc(r.type)}</td><td>${r.events}</td>` +
    `<td>${r.wiki_reacted} / ${r.measured_wiki}</td><td>${r.arrivals_rose} / ${r.measured_arrivals}</td><td>${r.median_excess==null?"—":"×"+r.median_excess}</td></tr>`;
  document.getElementById("ev-summary").innerHTML = s + "</table>";
})();
const off = document.getElementById("offline");
if (off) off.onclick = async e => {
  e.preventDefault(); off.textContent = "Tayyorlanmoqda…";
  try {
    const END = "</scr" + "ipt>";
    const libs = ["plotly.min.js", "d3.min.js", "topojson-client.min.js"];
    let html = await fetch(location.href).then(r => r.text());
    for (const name of libs) {
      const code = await fetch(name).then(r => r.text());
      const inline = "<scr" + "ipt>" + code.split(END).join("<\\/scr" + "ipt>") + END;
      html = html.replace('<script src="' + name + '">' + END, () => inline);  // function: "$" stays literal
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([html], {type: "text/html"}));
    a.download = "uzbekistan_tourism_monitor_" + D.last + ".html"; a.click();
    off.textContent = "Grafiklar — oflayn HTML fayl (internetsiz ochiladi)";
  } catch (err) { off.textContent = "Xato: sahifani GitHub Pages orqali oching"; }
};
</script>
</body>
</html>
"""
