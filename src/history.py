"""Builds docs/index.html: every day of collected data in interactive charts, plus CSV downloads.
Published by GitHub Pages and rebuilt after each daily run."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import config, events, pageviews, statuz
from .util import log

DOCS = config.ROOT / "docs"
import shutil  # noqa: E402

# Charting library kept in the repo (vendor/), served next to the page: no outside CDN needed.
VENDOR_JS = config.ROOT / "vendor" / "plotly.min.js"
PLOTLY = "plotly.min.js"
COLORS = {"zh": "#a23b2a", "ko": "#2f5d7c", "ja": "#c47f2c", "de": "#3d6b45", "tr": "#7a3b6b",
          "it": "#5b7f99", "fr": "#8a6d3b", "en": "#6e6e6e", "ru": "#9a9a9a"}


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

    data = {"dates": dates, "series": series, "monthly": monthly,
            "events": ev_list, "effects": ev_rows, "ev_summary": ev_summary,
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "first": dates[0], "last": dates[-1]}
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))) \
                   .replace("__PLOTLY__", PLOTLY)
    path = DOCS / "index.html"
    path.write_text(html, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    target = DOCS / "plotly.min.js"
    if not target.exists() or target.stat().st_size != VENDOR_JS.stat().st_size:
        shutil.copyfile(VENDOR_JS, target)
    log.info("history: wrote %s (%d days)", path, len(dates))
    return path


def standalone(out_path):
    """One self-contained HTML file (library inlined) that opens anywhere, even offline."""
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    js = VENDOR_JS.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    html = html.replace(f'<script src="{PLOTLY}"></script>', f"<script>{js}</script>", 1)
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
<script src="__PLOTLY__"></script>
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
#events-box a{color:var(--accent)}
.pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:13px;border:1px solid var(--rule)}
.up{background:#3d6b4522}.down{background:#a23b2a22}
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
  <h2>Voqealar ta'siri</h2>
  <p class="note">Har bir voqea (viza, reys, tadbir, sport...) uchun: <b>Vikipediya</b> — keyingi 7 kunda qiziqish odatdagidan necha baravar;
  <b>turistlar</b> — o'sha davlatdan kelganlar o'zgarishi, umumiy oqimga nisbatan ("farq": ×1,2 dan yuqori = ko'proq o'sdi).
  Bu bog'liqlik, isbot emas. Oylik natijalar boshqa yilning xuddi shu oylari bilan solishtirib mavsumdan tozalanadi. Kulrang qatorlar — boshqa voqealar bilan aralash, COVID davri yoki mavsum tekshirib bo'lmagan; xulosaga qo'shilmaydi.</p>
  <div id="ev-summary"></div>
  <div style="overflow-x:auto"><table id="ev-table"></table></div>
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
    const [page, lib] = await Promise.all([fetch(location.href).then(r => r.text()), fetch("plotly.min.js").then(r => r.text())]);
    const END = "</scr" + "ipt>";
    const inline = "<scr" + "ipt>" + lib.split(END).join("<\\/scr" + "ipt>") + END;
    const html = page.replace('<script src="plotly.min.js">' + END, () => inline);  // function: "$" in the library stays literal
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
