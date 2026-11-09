"""HTML template of docs/index.html (filled by history.build).

Structure (a story for outside readers): summary with key numbers -> how the system works -> 6 chapters:
  1 how many come and will come · 2 why they come · 3 where to attract them · 4 who is interested now ·
  5 what changes the flow (events) · 6 data, methods and limits.
All text comes from page_i18n.STRINGS (UZ / RU / EN switch, remembered per viewer, ?lang=ru also works).
Placeholders: __DATA__, __I18N__, __A2__.
"""

TEMPLATE = r"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uzbekistan Tourism Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:wght@400;500;600&display=swap" rel="stylesheet">
<script src="plotly.min.js"></script>
<script src="d3.min.js"></script>
<script src="topojson-client.min.js"></script>
<style>
:root{color-scheme:dark;--paper:#0a1424;--paper2:#132540;--ink:#ece3cc;--muted:#a8a084;--rule:#8a7236;--accent:#d4af37;--gold2:#f2d27a;--blue:#6f9fd8;--card:#0f1d33;--land:#1b2c47;--sea:#0c1a2e}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 "EB Garamond",Georgia,serif;
  background-image:radial-gradient(circle at 15% 0%,rgba(212,175,55,.08),transparent 45%),radial-gradient(circle at 85% 100%,rgba(111,159,216,.07),transparent 45%)}
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
#views{height:540px}
.downloads{display:flex;flex-wrap:wrap;gap:8px}
table{border-collapse:collapse;width:100%;font-size:15px;margin-top:10px}
th,td{border-bottom:1px solid var(--rule);padding:6px 8px;text-align:left;vertical-align:top}
th{font-weight:600;color:var(--muted)}
tr.mixed td{color:var(--muted);opacity:.7}
#events-box a,#upcoming-box a{color:var(--accent)}
.pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:13px;border:1px solid var(--rule)}
.up{background:#d4af3726}.down{background:#6f9fd826}
.sect{font:600 30px/1.2 "Cormorant Garamond",serif;margin:30px 0 12px;border-bottom:1px solid var(--rule);padding-bottom:6px}
.yearrow{display:flex;align-items:center;gap:10px;margin:4px 0 8px}
.yearrow input{flex:1;max-width:360px;accent-color:var(--accent)}
.mapgrid{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:16px;align-items:start}
.mapwrap{position:relative;border:1px solid var(--rule);border-radius:3px;background:var(--sea);overflow:hidden}
#map{width:100%;height:auto;display:block;cursor:grab}
#map .land{stroke:#8a723688;stroke-width:.4;vector-effect:non-scaling-stroke}
#map .land.nodata{fill:var(--land)}
#map .land.sel{stroke:var(--ink);stroke-width:1.6}
#map .land.uzb{fill:var(--accent) !important;stroke:var(--ink);stroke-width:1.2}
#map .grat{fill:none;stroke:#d4af3722;stroke-width:.5;vector-effect:non-scaling-stroke}
#map .sphere{fill:var(--sea)}
.tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--rule);padding:6px 9px;font-size:14px;border-radius:3px;box-shadow:0 2px 10px #0008;max-width:260px}
.legend{position:absolute;left:10px;bottom:10px;background:#0f1d33e6;border:1px solid var(--rule);padding:6px 8px;font-size:12px;border-radius:3px;color:var(--ink)}
.legend .bar{height:9px;width:180px;border:1px solid var(--rule)}
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
@media (max-width:800px){.mapgrid{grid-template-columns:1fr}.legend{position:static;border:0;border-top:1px solid var(--rule);border-radius:0}}
footer{color:var(--muted);font-size:14px;border-top:1px solid var(--rule);padding-top:12px}
@media (max-width:600px){.chart{height:620px}}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px}
h3.sub{font-size:16px;margin:6px 0 2px;font-weight:600}
#trends-latest,#trends-years{min-height:420px}
.tbl{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}.tbl th,.tbl td{border-bottom:1px solid var(--rule);padding:5px 8px;text-align:right;white-space:nowrap}.tbl th:first-child,.tbl td:first-child{text-align:left}.tbl th{color:var(--muted);font-weight:600}
.tablewrap{overflow-x:auto}
#amap{width:100%;height:auto;display:block}#amap .land{stroke:#8a723666;stroke-width:.4;vector-effect:non-scaling-stroke;fill:var(--land)}
#amap .land.uzb{fill:var(--gold2);stroke:var(--accent);stroke-width:1.2}#amap .sphere{fill:var(--sea)}#amap .grat{fill:none;stroke:#d4af371c;stroke-width:.5;vector-effect:non-scaling-stroke}
.gdot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px;border:1px solid #0006}
#attr-table td{white-space:normal;vertical-align:top}#attr-table td:last-child,#attr-table th:last-child{text-align:left;min-width:280px}#attr-table td.num{white-space:nowrap}#attr-table .why{font-size:13px;color:var(--muted)}
.stack2{display:flex;flex-direction:column;gap:18px}.tbl .rng{font-size:12px;color:var(--muted)}
/* ---- story layout ---- */
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;border-bottom:3px double var(--rule);padding-bottom:14px;margin-bottom:8px}
.top h1 small{text-transform:none;letter-spacing:.04em}
.langs{display:flex;gap:6px}.langs button{min-width:84px}
.hero{background:linear-gradient(180deg,#132540,#0f1d33);padding:22px 20px 16px}
.lead{font-size:19px;margin:0 0 16px;max-width:900px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px}
.kpi{border:1px solid var(--rule);border-radius:4px;padding:12px 14px;background:#0a1424aa}
.kpi .v{font:700 34px/1.1 "Cormorant Garamond",serif;color:var(--accent)}
.kpi .l{font-size:15px;margin-top:4px}.kpi .s{font-size:13px;color:var(--muted);margin-top:2px}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:12px;margin-top:10px;counter-reset:st}
.step{border:1px solid var(--rule);border-radius:4px;padding:12px 14px;position:relative;background:#0a142466}
.step b{display:block;font:600 19px/1.2 "Cormorant Garamond",serif;color:var(--gold2);margin-bottom:4px}
.step .n{position:absolute;top:10px;right:12px;font:700 26px "Cormorant Garamond",serif;color:var(--rule)}
.step p{margin:0;font-size:15px}
.toc{position:sticky;top:0;z-index:5;background:#0a1424f2;border-bottom:1px solid var(--rule);display:flex;gap:6px;flex-wrap:wrap;padding:8px 0;margin:0 0 18px}
.toc a{color:var(--ink);text-decoration:none;border:1px solid var(--rule);border-radius:14px;padding:3px 11px;font-size:14px;white-space:nowrap}
.toc a:hover{background:var(--accent);color:var(--paper)}
.chapter{margin:34px 0 14px;scroll-margin-top:60px}
.chapter h2{font:700 32px/1.15 "Cormorant Garamond",serif;display:flex;align-items:center;gap:12px;margin:0}
.chapter .num{display:inline-grid;place-items:center;width:40px;height:40px;border-radius:50%;background:var(--accent);color:var(--paper);font-size:24px;flex:none}
.chapter p{margin:6px 0 0 52px;color:var(--muted);max-width:860px}
section h3.title{font:600 25px/1.2 "Cormorant Garamond",serif;margin:0 0 2px}
section .what{margin:0 0 8px;font-size:16px}
details.howto{margin:8px 0 6px;border-top:1px dashed var(--rule);padding-top:6px}
details.howto summary{color:var(--accent);font-size:15px}
details.howto summary::before{font-size:16px}
details.howto>div{color:var(--muted);font-size:15px;margin-top:4px}
.methods ul{margin:6px 0 10px;padding-left:20px}.methods li{margin-bottom:4px}
#ev-summary,.upcard{overflow-x:auto}
#attr-table th{white-space:normal;vertical-align:bottom}#attr-table td:last-child{min-width:260px}
@media (max-width:600px){.chapter p{margin-left:0}.langs button{min-width:0}.kpi .v{font-size:28px}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <h1>Uzbekistan Tourism Monitor<small data-i18n="tagline"></small></h1>
  <div class="langs" role="group" aria-label="Language">
    <button data-lang="uz">O'zbekcha</button><button data-lang="ru">Русский</button><button data-lang="en">English</button>
  </div>
</header>
<p class="meta" id="meta"></p>

<section class="hero">
  <p class="lead" data-i18n-html="hero_lead"></p>
  <div class="kpis" id="kpis"></div>
</section>

<section>
  <h3 class="title" data-i18n="how_title"></h3>
  <div class="flow">
    <div class="step"><span class="n">1</span><b data-i18n="step1_t"></b><p data-i18n="step1_p"></p></div>
    <div class="step"><span class="n">2</span><b data-i18n="step2_t"></b><p data-i18n="step2_p"></p></div>
    <div class="step"><span class="n">3</span><b data-i18n="step3_t"></b><p data-i18n="step3_p"></p></div>
    <div class="step"><span class="n">4</span><b data-i18n="step4_t"></b><p data-i18n="step4_p"></p></div>
  </div>
</section>

<nav class="toc">
  <a href="#ch1" data-i18n="toc1"></a><a href="#ch2" data-i18n="toc2"></a><a href="#ch3" data-i18n="toc3"></a>
  <a href="#ch4" data-i18n="toc4"></a><a href="#ch5" data-i18n="toc5"></a><a href="#ch6" data-i18n="toc6"></a>
</nav>

<!-- 1 -->
<div class="chapter" id="ch1"><h2><span class="num">1</span><span data-i18n="ch1_t"></span></h2><p data-i18n="ch1_p"></p></div>
<section id="overall-box">
  <h3 class="title" data-i18n="overall_t"></h3>
  <p class="what" data-i18n="overall_what"></p>
  <div class="controls">
    <button data-og="day" data-i18n="g_day"></button><button data-og="week" data-i18n="g_week"></button>
    <button data-og="month" class="on" data-i18n="g_month"></button><button data-og="year" data-i18n="g_year"></button>
  </div>
  <div id="overall" class="chart"></div>
  <p class="note" id="overall-method"></p>
  <details class="howto"><summary data-i18n="howto"></summary><div data-i18n-html="overall_note"></div></details>
</section>
<section id="score-box">
  <h3 class="title" data-i18n="score_t"></h3>
  <p class="what" data-i18n="score_what"></p>
  <div class="stack2">
    <div><h3 class="sub" data-i18n="acc_t"></h3><div class="tablewrap"><table class="tbl" id="acc-table"></table></div>
      <p class="note" id="live-note"></p></div>
    <div><h3 class="sub" id="fc-title" data-i18n="fc_t"></h3><div class="tablewrap"><table class="tbl" id="fc-table"></table></div></div>
  </div>
  <details class="howto"><summary data-i18n="howto"></summary><div data-i18n-html="score_note"></div></details>
</section>
<section id="arrivals-box">
  <h3 class="title" data-i18n="arr_t"></h3>
  <p class="what" data-i18n="arr_what"></p>
  <div id="arrivals" class="chart"></div>
</section>

<!-- 2 -->
<div class="chapter" id="ch2"><h2><span class="num">2</span><span data-i18n="ch2_t"></span></h2><p data-i18n="ch2_p"></p></div>
<section id="leisure-box">
  <h3 class="title" data-i18n="leis_t"></h3>
  <p class="what" data-i18n="leis_what"></p>
  <div class="grid2">
    <div><h3 class="sub" data-i18n="purpose_years_t"></h3><div id="purpose-years" class="chart"></div></div>
    <div><h3 class="sub" data-i18n="leis_months_t"></h3><div id="leisure-months" class="chart"></div></div>
  </div>
  <h3 class="sub" id="leisure-title"></h3>
  <div class="tablewrap"><table class="tbl" id="leisure-table"></table></div>
  <details class="howto"><summary data-i18n="howto"></summary><div><span data-i18n-html="leis_note"></span> <span id="leisure-note"></span></div></details>
</section>

<!-- 3 -->
<div class="chapter" id="ch3"><h2><span class="num">3</span><span data-i18n="ch3_t"></span></h2><p data-i18n="ch3_p"></p></div>
<section id="attr-box">
  <h3 class="title" data-i18n="attr_t"></h3>
  <p class="what" data-i18n="attr_what"></p>
  <div class="controls" id="attr-legend"></div>
  <div class="mapwrap"><svg id="amap" role="img" aria-label="map"></svg><div class="tip" id="atip" hidden></div></div>
  <div class="tablewrap"><table class="tbl" id="attr-table"></table></div>
  <details class="howto"><summary data-i18n="howto"></summary><div><span data-i18n-html="attr_note"></span> <span id="attr-note"></span></div></details>
</section>
<section id="trends-box">
  <h3 class="title" data-i18n="trends_t"></h3>
  <p class="what" data-i18n="trends_what"></p>
  <div class="grid2">
    <div><h3 class="sub" id="trends-latest-title"></h3><div id="trends-latest" class="chart"></div></div>
    <div><h3 class="sub" data-i18n="trends_years_t"></h3><div id="trends-years" class="chart"></div></div>
  </div>
  <details class="howto"><summary data-i18n="howto"></summary><div data-i18n-html="trends_note"></div></details>
</section>

<!-- 4 -->
<div class="chapter" id="ch4"><h2><span class="num">4</span><span data-i18n="ch4_t"></span></h2><p data-i18n="ch4_p"></p></div>
<section id="map-box">
  <h3 class="title" data-i18n="map_t"></h3>
  <p class="what" data-i18n="map_what"></p>
  <div class="controls" id="metric-btns">
    <button data-metric="arrivals" class="on" data-i18n="m_arrivals"></button>
    <button data-metric="growth" data-i18n="m_growth"></button>
    <button data-metric="share" data-i18n="m_share"></button>
    <button data-metric="change" data-i18n="m_change"></button>
  </div>
  <div class="yearrow" id="yearrow"><span data-i18n="year_lbl"></span><input type="range" id="year" step="1"><b id="yearlbl"></b></div>
  <div class="mapgrid">
    <div class="mapwrap"><svg id="map" role="img" aria-label="map"></svg>
      <div id="tip" class="tip" hidden></div><div id="legend" class="legend"></div></div>
    <aside id="panel" class="panel"></aside>
  </div>
</section>
<section id="views-box">
  <h3 class="title" data-i18n="views_t"></h3>
  <p class="what" data-i18n="views_what"></p>
  <div class="controls">
    <button data-gran="day" data-i18n="g_day"></button><button data-gran="week" class="on" data-i18n="g_week"></button>
    <button data-gran="month" data-i18n="g_month"></button><button data-gran="year" data-i18n="g_year"></button>
    <button data-scale="log" class="on" data-i18n="scale_log"></button>
    <button data-scale="linear" data-i18n="scale_lin"></button>
  </div>
  <div id="views" class="chart"></div>
  <details class="howto"><summary data-i18n="howto"></summary><div data-i18n-html="views_note"></div></details>
</section>
<section id="share-box">
  <h3 class="title" data-i18n="share_t"></h3>
  <p class="what" data-i18n="share_what"></p>
  <div id="share" class="chart"></div>
</section>

<!-- 5 -->
<div class="chapter" id="ch5"><h2><span class="num">5</span><span data-i18n="ch5_t"></span></h2><p data-i18n="ch5_p"></p></div>
<section id="upcoming-box">
  <div class="controls" id="period-btns" style="float:right;margin:0">
    <button data-dir="next" class="on" data-i18n="dir_next"></button><button data-dir="past" data-i18n="dir_past"></button>
  </div>
  <h3 class="title" data-i18n="up_t"></h3>
  <p class="what" data-i18n="up_what"></p>
  <div class="controls" id="win-btns">
    <button data-win="1" data-i18n="w_day"></button><button data-win="7" data-i18n="w_week"></button><button data-win="31" data-i18n="w_month"></button>
    <button data-win="366" class="on" data-i18n="w_year"></button><button data-win="99999" data-i18n="w_all"></button>
  </div>
  <div id="upcoming"></div>
  <details class="howto"><summary data-i18n="howto"></summary><div data-i18n-html="up_note"></div></details>
</section>
<section id="events-box">
  <h3 class="title" data-i18n="ev_t"></h3>
  <p class="what" data-i18n="ev_what"></p>
  <div id="ev-summary"></div>
  <details class="howto"><summary data-i18n="ev_all"></summary>
    <div data-i18n-html="ev_note"></div>
    <div style="overflow-x:auto"><table id="ev-table"></table></div>
  </details>
</section>

<!-- 6 -->
<div class="chapter" id="ch6"><h2><span class="num">6</span><span data-i18n="ch6_t"></span></h2><p data-i18n="ch6_p"></p></div>
<section class="methods">
  <h3 class="title" data-i18n="src_t"></h3>
  <div data-i18n-html="src_html"></div>
  <h3 class="title" data-i18n="lim_t"></h3>
  <div data-i18n-html="lim_html"></div>
</section>
<section>
  <h3 class="title" data-i18n="dl_t"></h3>
  <div class="downloads">
    <a class="btn" href="reports/latest.docx" download data-i18n="dl_report"></a>
    <a class="btn" href="daily_views_by_market.csv" download data-i18n="dl_views_m"></a>
    <a class="btn" href="https://raw.githubusercontent.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor/main/data/pageviews_daily.csv" data-i18n="dl_views_p"></a>
    <a class="btn" href="official_arrivals_monthly.csv" download data-i18n="dl_month"></a>
    <a class="btn" href="official_arrivals_ytd.csv" download data-i18n="dl_ytd"></a>
    <a class="btn" href="https://raw.githubusercontent.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor/main/data/purpose_yearly.csv" data-i18n="dl_purpose"></a>
    <a class="btn" href="https://raw.githubusercontent.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor/main/data/leisure_estimates.csv" data-i18n="dl_leisure"></a>
    <a class="btn" href="https://raw.githubusercontent.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor/main/data/attraction.csv" data-i18n="dl_attr"></a>
    <a class="btn" href="event_effects.csv" download data-i18n="dl_events"></a>
    <a class="btn" id="offline" href="#" data-i18n="dl_offline"></a>
  </div>
</section>
<footer data-i18n-html="footer"></footer>
</div>

<script>
const D = __DATA__;
const I18N = __I18N__;
const A2 = __A2__;
// ---------------------------------------------------------------- language
let LANG = (() => { try { const q = new URLSearchParams(location.search).get("lang"); if (q && I18N[q]) return q;
  const s = localStorage.getItem("utm_lang"); if (s && I18N[s]) return s; } catch (e) {} return "uz"; })();
const t = (k, v) => { const s = (I18N[LANG] && I18N[LANG][k]) ?? I18N.uz[k] ?? k;
  return v ? s.replace(/\{(\w+)\}/g, (_, n) => v[n] ?? "") : s; };
const LOC = {uz: "ru-RU", ru: "ru-RU", en: "en-US"};
const nf = v => v == null || isNaN(v) ? "—" : Math.round(v).toLocaleString(LOC[LANG]);
const dec = (v, d = 1) => v == null ? "—" : (LANG === "en" ? v.toFixed(d) : v.toFixed(d).replace(".", ","));
const mln = v => dec(v / 1e6, v >= 1e7 ? 1 : 2) + " " + t("mln");
const months = () => t("months").split(",");
const lab = m => months()[+m.slice(5) - 1] + " " + m.slice(0, 4);
// country names: Uzbek from our own list, Russian/English from the browser's built-in country names
const LANG_A2 = {zh:"CN", ko:"KR", ja:"JP", de:"DE", tr:"TR", it:"IT", fr:"FR", hi:"IN", kk:"KZ", ky:"KG", tg:"TJ", tk:"TM", ps:"AF", ru:"RU"};
const EN_A2 = {"China":"CN", "Republic of Korea":"KR", "Türkiye":"TR", "India":"IN", "Germany":"DE", "Russia":"RU", "Kazakhstan":"KZ",
  "Kyrgyzstan":"KG", "Tajikistan":"TJ", "Turkmenistan":"TM", "Afghanistan":"AF", "Italy":"IT", "France":"FR", "Japan":"JP",
  "United States":"US", "United Kingdom":"GB", "Uzbekistan":"UZ", "Georgia":"GE"};
const UZ_N = {CN:"Xitoy", KR:"Janubiy Koreya", JP:"Yaponiya", DE:"Germaniya", TR:"Turkiya", IT:"Italiya", FR:"Fransiya", IN:"Hindiston",
  KZ:"Qozog'iston", KG:"Qirg'iziston", TJ:"Tojikiston", TM:"Turkmaniston", AF:"Afg'oniston", RU:"Rossiya", US:"AQSH",
  GB:"Buyuk Britaniya", UZ:"O'zbekiston", GE:"Gruziya"};
const flag = a2 => a2 && a2.length === 2 ? String.fromCodePoint(...[...a2].map(c => 127397 + c.charCodeAt(0))) : "";
let DN = null;
function cname(a2, fallback){
  if (!a2) return fallback || "";
  if (LANG === "uz") return UZ_N[a2] || fallback || a2;
  try { DN = DN && DN._l === LANG ? DN : Object.assign(new Intl.DisplayNames([LANG], {type: "region"}), {_l: LANG}); return DN.of(a2) || fallback || a2; }
  catch (e) { return fallback || a2; }
}
function ckey(key){            // 'TOTAL' / 'OTHER' / English name / 2-letter code -> name in current language
  if (key === "TOTAL") return t("total");
  if (key === "OTHER") return t("other_countries");
  const a2 = EN_A2[key] || (key && key.length === 2 ? key : null);
  return cname(a2, key);
}
const seriesName = s => s.lang === "en" ? "🌐 " + t("series_en") : s.lang === "ru" ? "🌐 " + t("series_ru") : flag(LANG_A2[s.lang]) + " " + cname(LANG_A2[s.lang]);
function applyStatic(){
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach(e => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach(e => { e.innerHTML = t(e.dataset.i18nHtml); });
  document.querySelectorAll("[data-lang]").forEach(b => b.classList.toggle("on", b.dataset.lang === LANG));
  document.getElementById("meta").textContent = t("meta", {first: D.first, last: D.last, n: nf(D.dates.length), upd: D.updated});
  document.title = "Uzbekistan Tourism Monitor — " + t("tagline");
}
// ---------------------------------------------------------------- summary numbers
function drawKpis(){
  const O = D.overall, M = O && O.method, Y = M && O.years[M.year], el = document.getElementById("kpis"), k = [];
  if (Y) k.push([mln(Y.v), t("kpi_fc", {y: M.year}), t("kpi_fc_s", {lo: mln(Y.lo), hi: mln(Y.hi)})]);
  if (Y) k.push([mln(Y.ytd), t("kpi_ytd", {y: M.year, m: months()[M.through - 1]}), t("kpi_ytd_s")]);
  const P = D.leisure && D.leisure.yearly && D.leisure.yearly[D.leisure.yearly.length - 1];
  if (P) k.push([Math.round(P.leisure / P.total * 100) + "%", t("kpi_leis", {y: P.year}), t("kpi_leis_s", {v: mln(P.leisure * 1000), r: Math.round(P.relatives / P.total * 100) + "%"})]);
  const acc = D.score && D.score.accuracy.find(r => r.level === "TOTAL"), b = acc && acc.backtest && acc.backtest[1];
  if (b) k.push([dec(b.mae * 100) + "%", t("kpi_acc"), t("kpi_acc_s", {n: b.n})]);
  el.innerHTML = k.map(([v, l, s]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div><div class="s">${s}</div></div>`).join("");
}
// ---------------------------------------------------------------- charts
const NARROW = window.innerWidth < 600;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function layout(ytitle, ylog){
  return {paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)", separators: LANG === "en" ? ".," : ", ",
    colorway:["#d4af37", "#6f9fd8", "#f2d27a", "#a9c4e8", "#b8862b", "#4f78b0", "#e8c66a", "#8a9bb3"],
    hoverlabel:{bgcolor:css("--card"), bordercolor:css("--accent"), font:{color:css("--ink")}},
    font:{family:"EB Garamond, Georgia, serif", color:css("--ink"), size:14},
    margin: NARROW ? {l:46,r:8,t:10,b:230} : {l:58,r:12,t:10,b:40}, hovermode:"x unified",
    legend: NARROW ? {orientation:"h", x:0, y:-0.12, yanchor:"top", font:{size:12}} : {orientation:"h", y:-0.18},
    xaxis:{gridcolor:css("--rule")+"55", rangeslider:{visible:true, thickness:0.06},
      rangeselector:{bgcolor:css("--paper2"), activecolor:css("--accent"), font:{color:css("--ink")},
        buttons:[{count:1,label:t("rs_1m"),step:"month",stepmode:"backward"},{count:6,label:t("rs_6m"),step:"month",stepmode:"backward"},
                 {count:1,label:t("rs_1y"),step:"year",stepmode:"backward"},{count:3,label:t("rs_3y"),step:"year",stepmode:"backward"},
                 {step:"all",label:t("rs_all")}]}},
    yaxis:{title:ytitle, gridcolor:css("--rule")+"55", type: ylog ? "log" : "linear"}};
}
const cfg = {responsive:true, displaylogo:false,
  toImageButtonOptions:{format:"png", filename:"uzbekistan_tourism_monitor", width:1600, height:800, scale:2}};
let gran = "week", scale = "log";
function aggregate(dates, vals, g){
  if (g === "day") return {x:dates, y:vals};
  const key = d => g === "year" ? d.slice(0,4) : g === "month" ? d.slice(0,7) + "-01" : (() => {
    const x = new Date(d + "T00:00:00Z"); const wd = (x.getUTCDay() + 6) % 7; x.setUTCDate(x.getUTCDate() - wd);
    return x.toISOString().slice(0,10); })();
  const m = new Map(), n = new Map();
  dates.forEach((d,i) => { const k = key(d); if (vals[i] != null) { m.set(k, (m.get(k)||0) + vals[i]); } n.set(k, (n.get(k)||0) + 1); });
  const full = g === "week" ? 7 : g === "month" ? 28 : 365;
  const keys = [...m.keys()].filter((k,i,a) => i < a.length - 1 || n.get(k) >= full);
  return {x: g === "year" ? keys.map(k => k + "-07-01") : keys, y: keys.map(k => m.get(k))};
}
function drawViews(){
  const tr = D.series.map(s => { const a = aggregate(D.dates, s.daily, gran);
    return {x:a.x, y:a.y, name:seriesName(s), type: gran === "day" ? "scattergl" : "scatter", mode: gran === "year" ? "lines+markers" : "lines",
      visible: s.group === "neighbour" ? "legendonly" : true,
      line:{color:s.color, width: gran==="day" ? 1 : 1.8, dash:s.dash}}; });
  const L = layout(t("views_per", {u: t("u_" + gran)}), scale==="log");
  L.shapes = (D.events||[]).map(e => ({type:"line", xref:"x", yref:"paper", x0:e.date, x1:e.date, y0:0, y1:1,
    line:{color:css("--accent"), width:1, dash:"dot"}}));
  const ev = D.events || [];
  tr.push({x: ev.map(e => e.date), y: ev.map(() => 1), yaxis: "y2", type: "scatter", mode: "markers", name: t("events_lbl"),
    marker: {symbol: "triangle-down", size: 9, color: css("--accent")}, hovertext: ev.map(e => e.date + ": " + e.title),
    hoverinfo: "text", showlegend: true});
  L.yaxis2 = {overlaying: "y", range: [0, 1.02], visible: false, fixedrange: true};
  L.xaxis.rangeslider = {visible: false};
  L.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}};
  L.margin.b = NARROW ? 260 : 120;
  Plotly.react("views", tr, L, cfg);
}
function drawScore(){
  const S = D.score, box = document.getElementById("score-box");
  if (!S) { box.style.display = "none"; return; }
  const pctf = v => dec(v * 100) + "%";
  const at = document.getElementById("acc-table");
  at.innerHTML = `<thead><tr><th>${t("c_market")}</th><th>${t("c_h1")}</th><th>${t("c_h2")}</th><th>${t("c_h3")}</th><th>${t("c_bias")}</th></tr></thead>`;
  const tb = document.createElement("tbody");
  S.accuracy.forEach(r => {
    const b = r.backtest || {};
    if (!b[1]) return;
    const tr = document.createElement("tr");
    const cells = [ckey(r.level) + (b[1].n < 8 ? " *" : ""), pctf(b[1].mae) + " (" + b[1].n + ")", b[2] ? pctf(b[2].mae) : "—", b[3] ? pctf(b[3].mae) : "—",
                   (b[1].bias > 0 ? "+" : "") + pctf(b[1].bias)];
    cells.forEach((c, i) => { const td = document.createElement("td"); td.textContent = c; if (i === 0 && r.level === "TOTAL") td.style.fontWeight = "600"; tr.appendChild(td); });
    tb.appendChild(tr);
  });
  at.appendChild(tb);
  document.getElementById("live-note").textContent = t("live_note", {a: S.live_logged, b: S.live_scored});
  const ft = document.getElementById("fc-table");
  const first = S.forecasts.find(f => f.rows.length);
  const targets = first ? first.rows.map(r => r.target) : [];
  ft.innerHTML = `<thead><tr><th>${t("c_market")}</th><th>${t("c_last")}</th>` + targets.map(x => "<th>" + lab(x) + "</th>").join("") + "</tr></thead>";
  const fb = document.createElement("tbody");
  S.forecasts.forEach(f => {
    const tr = document.createElement("tr");
    const td0 = document.createElement("td"); td0.textContent = ckey(f.level); if (f.level === "TOTAL") td0.style.fontWeight = "600"; tr.appendChild(td0);
    const td1 = document.createElement("td"); td1.textContent = f.last ? lab(f.last) + ": " + nf(f.last_value) : "—"; tr.appendChild(td1);
    targets.forEach(x => {
      const r = f.rows.find(q => q.target === x); const td = document.createElement("td");
      if (r) {
        const v = document.createElement("div"); v.textContent = nf(r.forecast);
        const rg = document.createElement("div"); rg.className = "rng"; rg.textContent = nf(r.lo) + "–" + nf(r.hi);
        td.append(v, rg);
      } else { td.textContent = t("not_enough"); td.style.color = css("--muted"); }
      tr.appendChild(td);
    });
    fb.appendChild(tr);
  });
  ft.appendChild(fb);
}
function drawLeisure(){
  const P = D.leisure, box = document.getElementById("leisure-box");
  if (!P) { box.style.display = "none"; return; }
  const pct = v => v == null ? "—" : Math.round(v * 100) + "%";
  const yrs = P.yearly.map(r => r.year);
  const parts = [["leisure", t("p_leisure"), css("--accent")], ["relatives", t("p_relatives"), "#3b5272"],
                 ["business", t("p_business"), css("--blue")], ["other", t("p_other"), "#8a9bb3"]];
  const bars = parts.map(([k, n, c]) => ({type: "bar", name: n, x: yrs, marker: {color: c},
    y: P.yearly.map(r => r[k] / r.total * 100), customdata: P.yearly.map(r => r[k] * 1000),
    hovertemplate: "%{x}: %{y:.1f}% (%{customdata:,.0f})<extra>" + n + "</extra>"}));
  const L1 = layout("%", false);
  L1.barmode = "stack"; L1.xaxis = {type: "category", gridcolor: css("--rule") + "55"};
  L1.yaxis = {range: [0, 100], ticksuffix: "%", gridcolor: css("--rule") + "55"}; L1.hovermode = "closest";
  L1.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L1.margin = {l: 44, r: 10, t: 10, b: 80};
  Plotly.react("purpose-years", bars, L1, cfg);
  const pal = ["#d4af37", "#f2d27a", "#6f9fd8", "#a9c4e8", "#b8862b", "#4f78b0", "#e8c66a", "#8a9bb3", "#3b5272"];
  const st = P.stack.map((s, i) => ({type: "bar", name: ckey(s.country), x: P.months.map(m => m + "-01"), y: s.y,
    marker: {color: pal[i % pal.length]}, hovertemplate: "%{y:,.0f}<extra>" + ckey(s.country) + "</extra>"}));
  const L2 = layout(t("people_month"), false);
  L2.barmode = "stack"; L2.xaxis = {type: "date", tickformat: "%Y-%m", gridcolor: css("--rule") + "55"};
  L2.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L2.margin = {l: 56, r: 10, t: 10, b: 100};
  Plotly.react("leisure-months", st, L2, cfg);
  const targets = (P.total.forecast || []).map(f => f.target);
  document.getElementById("leisure-title").textContent = t("leis_table_t", {y: P.ytd_year, m: P.ytd_months});
  const tbl = document.getElementById("leisure-table");
  tbl.innerHTML = `<thead><tr><th>${t("c_country")}</th><th>${t("c_leis_share")}</th><th>${t("c_arrivals")}</th><th>${t("c_of_leis")}</th>`
    + targets.map(x => "<th>" + lab(x) + "</th>").join("") + "</tr></thead>";
  const tb = document.createElement("tbody");
  const cell = (tr, txt, sub, bold) => { const td = document.createElement("td");
    const a = document.createElement("div"); a.textContent = txt; if (bold) a.style.fontWeight = "600"; td.appendChild(a);
    if (sub) { const b = document.createElement("div"); b.className = "rng"; b.textContent = sub; td.appendChild(b); } tr.appendChild(td); };
  [...P.rows, Object.assign({total: true, country: "TOTAL"}, P.total)].forEach(r => {
    const tr = document.createElement("tr");
    cell(tr, ckey(r.country), null, r.total);
    cell(tr, r.total ? (r.ytd_arrivals ? pct(r.ytd_leisure / r.ytd_arrivals) : "—") : pct(r.share),
         r.share_2023 != null ? "2023: " + pct(r.share_2023) : null, r.total);
    cell(tr, nf(r.ytd_arrivals), null, r.total);
    cell(tr, nf(r.ytd_leisure), null, r.total);
    targets.forEach(x => { const f = (r.forecast || []).find(q => q.target === x);
      cell(tr, f ? nf(f.v) : "—", f && f.lo != null ? nf(f.lo) + "–" + nf(f.hi) : null, r.total); });
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
  const v = P.validation.filter(x => !x.in_sample && x.year >= 2023)
    .map(x => x.year + ": " + (x.error_pct > 0 ? "+" : "") + dec(x.error_pct) + "%").join(", ");
  document.getElementById("leisure-note").textContent = t("leis_check", {v: v});
}
const GROUP_COL = {A: "#f2c94c", C: "#d9893a", B: "#6f9fd8", D: "#4a5d7c"};
function drawAttraction(){
  const A = D.attraction, box = document.getElementById("attr-box");
  if (!A || !A.rows.length || !D.map || !D.map.topo) { box.style.display = "none"; return; }
  const by = Object.fromEntries(A.rows.map(r => [r.num, r]));
  const g_ = k => t("grp_" + k);
  const msg = r => LANG === "uz" ? r.message_uz : r["message_" + LANG];
  const msgd = r => LANG === "uz" ? r.message_detail : r["message_detail_" + LANG];
  const why = r => LANG === "uz" ? r.why : r["why_" + LANG];
  const chan = r => LANG === "uz" ? r.channels : r["channels_" + LANG];
  const rn = r => cname(A2[r.num], r.name);
  document.getElementById("attr-legend").innerHTML = ["A", "C", "B", "D"].map(k =>
    `<span style="margin-right:14px"><span class="gdot" style="background:${GROUP_COL[k]}"></span>${k} — ${g_(k)}</span>`).join("");
  const svg = d3.select("#amap"), W = 960, H = 470;
  svg.attr("viewBox", `0 0 ${W} ${H}`).selectAll("*").remove();
  const proj = d3.geoNaturalEarth1().fitExtent([[6, 6], [W - 6, H - 6]], {type: "Sphere"}), path = d3.geoPath(proj);
  const g = svg.append("g");
  g.append("path").attr("class", "sphere").attr("d", path({type: "Sphere"}));
  g.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule10()));
  const feats = topojson.feature(D.map.topo, D.map.topo.objects.countries).features;
  const tip = document.getElementById("atip");
  g.append("g").selectAll("path").data(feats).join("path")
    .attr("class", d => "land" + (d.id === "860" ? " uzb" : "")).attr("d", path)
    .attr("style", d => by[d.id] ? `fill:${GROUP_COL[by[d.id].group]}` : null)
    .on("mousemove", (ev, d) => {
      const r = by[d.id]; if (!r) { tip.hidden = true; return; }
      const bx = document.querySelector("#attr-box .mapwrap").getBoundingClientRect();
      tip.innerHTML = `<b>${rn(r)}</b> · ${r.group} — ${g_(r.group)}<br><b>${msg(r)}:</b> ${msgd(r)}<br>`
        + `<span style="color:var(--muted)">${why(r)}</span><br>${t("leis_trips_y")}: ${nf(r.leisure)}`
        + (r.headroom ? `<br>${t("headroom")}: +${nf(r.headroom)} / ${t("u_year")}` : "") + `<br>${t("channel")}: ${chan(r)}`;
      tip.hidden = false; tip.style.left = Math.min(ev.clientX - bx.left + 12, bx.width - 270) + "px"; tip.style.top = (ev.clientY - bx.top + 12) + "px"; })
    .on("mouseleave", () => { tip.hidden = true; });
  svg.call(d3.zoom().scaleExtent([1, 8]).translateExtent([[0, 0], [W, H]]).on("zoom", e => g.attr("transform", e.transform)));
  const tbl = document.getElementById("attr-table");
  tbl.innerHTML = `<thead><tr><th>${t("c_market")}</th><th>${t("c_group")}</th><th>${t("leis_trips_y")}</th><th>${t("c_per1000")}</th><th>${t("c_headroom")}</th><th>${t("c_google")}</th><th>${t("c_message")}</th></tr></thead>`;
  const tb = document.createElement("tbody");
  A.rows.forEach(r => {
    const tr = document.createElement("tr");
    const td = (html, cls) => { const c = document.createElement("td"); c.innerHTML = html; if (cls) c.className = cls; tr.appendChild(c); };
    td(`<b>${rn(r)}</b>`);
    td(`<span class="gdot" style="background:${GROUP_COL[r.group]}"></span>${r.group}`, "num");
    td(nf(r.leisure) + (r.share_year ? `<div class="rng">${t("share_lbl")} ${Math.round(r.leisure_share * 100)}% (${r.share_year})</div>` : ""), "num");
    td(r.rate == null || r.near ? "—" : dec(r.rate, 2), "num");
    td(r.headroom ? "+" + nf(r.headroom) : "—", "num");
    td(r.search == null ? "—" : Math.round(r.search) + "%", "num");
    td(`<b>${msg(r)}</b> — ${msgd(r)}<div class="why">${why(r)}. ${t("channel")}: ${chan(r)}</div>`);
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
  document.getElementById("attr-note").textContent = t("attr_typical", {r: dec(A.typical, 2)});
}
function drawTrends(){
  const T = D.trends, box = document.getElementById("trends-box");
  if (!T || !T.markets || !T.markets.length) { box.style.display = "none"; return; }
  const ms = T.markets.slice().sort((a, b) => a.latest[0] - b.latest[0]);
  const pal = [css("--accent"), "#6f9fd8", "#4f6b8f", "#8a9bb3", "#2f4466"];
  const dn = T.destinations.map(ckey), mn = m => flag(m.geo) + " " + cname(m.geo);
  const bars = dn.map((d, i) => ({type: "bar", orientation: "h", name: d, y: ms.map(mn),
    x: ms.map(m => m.latest[i]), marker: {color: pal[i]}, hovertemplate: "%{y}: %{x}%<extra>" + d + "</extra>",
    text: i === 0 ? ms.map(m => m.latest[0] + "%") : null, textposition: "inside", insidetextanchor: "start"}));
  const L1 = layout("%", false);
  L1.barmode = "stack"; L1.xaxis = {range: [0, 100], gridcolor: css("--rule") + "55", ticksuffix: "%"};
  L1.yaxis = {automargin: true}; L1.hovermode = "closest";
  L1.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L1.margin = {l: 10, r: 10, t: 10, b: 70};
  document.getElementById("trends-latest-title").textContent = T.snapshot ? t("trends_latest_d", {d: T.snapshot}) : t("trends_latest");
  Plotly.react("trends-latest", bars, L1, cfg);
  const lines = T.markets.filter(m => m.geo !== "KZ").map(m => ({type: "scatter", mode: "lines+markers", name: mn(m),
    x: T.years, y: m.years, visible: ["DE", "KR", "IN", "US", "JP"].includes(m.geo) ? true : "legendonly",
    hovertemplate: "%{x}: %{y}%<extra>" + mn(m) + "</extra>"}));
  const L2 = layout("%", false);
  L2.xaxis = {type: "category", gridcolor: css("--rule") + "55"}; L2.yaxis.rangemode = "tozero"; L2.yaxis.ticksuffix = "%";
  L2.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L2.margin = {l: 40, r: 10, t: 28, b: 110};
  const wc = T.years.indexOf("2026");   // category axis: number-like strings are read as numbers in shapes -> index
  L2.shapes = wc < 0 ? [] : [{type: "line", xref: "x", yref: "paper", x0: wc, x1: wc, y0: 0, y1: 1, line: {color: css("--accent"), width: 1, dash: "dot"}}];
  L2.annotations = wc < 0 ? [] : [{x: wc, y: 1, yref: "paper", text: t("world_cup"), showarrow: false, font: {size: 11, color: css("--accent")}, xanchor: "right", yanchor: "bottom"}];
  Plotly.react("trends-years", lines, L2, cfg);
}
function drawShare(){
  const has = D.series.some(s => s.share && s.share.some(v => v !== null));
  if (!has) { document.getElementById("share-box").style.display = "none"; return; }
  const tr = D.series.filter(s => s.share).map(s => ({x:D.dates, y:s.share, name:seriesName(s), type:"scattergl",
    mode:"lines", line:{color:s.color, width:1.6, dash:s.dash}}));
  Plotly.react("share", tr, layout(t("per_million"), true), cfg);
}
function drawArrivals(){
  const tr = Object.entries(D.monthly).map(([k,v]) => ({x:v.x, y:v.y, name: k === "TOTAL" ? t("total") : flag(EN_A2[k]) + " " + ckey(k), type:"scatter",
    mode:"lines+markers", yaxis: k==="TOTAL" ? "y2" : "y", connectgaps:false,
    marker:{symbol:v.exact.map(e => e ? "circle" : "circle-open"), size:8},
    line:{width: k==="TOTAL" ? 3 : 1.6, dash: k==="TOTAL" ? "dash" : "solid"}}));
  const L = layout(t("arr_y1"), false);
  L.xaxis = {gridcolor:css("--rule")+"55", type:"date", tickformat:"%Y-%m", dtick:"M2"};
  L.yaxis.rangemode = "tozero";
  L.yaxis2 = {title:t("arr_y2"), overlaying:"y", side:"right", showgrid:false, rangemode:"tozero"};
  L.margin.r = 60;
  Plotly.react("arrivals", tr, L, cfg);
}
let og = "month";
function drawOverall(){
  const O = D.overall, box = document.getElementById("overall-box");
  if (!O || !O.points || !O.points.length) { box.style.display = "none"; return; }
  const dim = m => new Date(Date.UTC(+m.slice(0,4), +m.slice(5,7), 0)).getUTCDate();
  const per = (m, v) => og === "day" ? v / dim(m) : og === "week" ? v / dim(m) * 7 : v;
  const accent = css("--accent"), ink = css("--ink"), grey = css("--rule") || "#999";
  let tr = [];
  const L = layout(t("og_" + og), false);
  L.xaxis.rangeslider = {visible:false}; L.xaxis.rangeselector = undefined; L.xaxis.type = "date";
  L.yaxis.rangemode = "tozero"; L.hovermode = "x unified";
  if (og === "year") {
    const ys = Object.keys(O.years).sort();
    const act = ys.filter(y => O.years[y].kind === "actual"), fc = ys.filter(y => O.years[y].kind === "forecast");
    tr.push({x:act, y:act.map(y => O.years[y].v), type:"bar", name:t("o_official_y"), marker:{color:ink}, hovertemplate:"%{y:,.0f}<extra></extra>"});
    fc.forEach(y => { const r = O.years[y];
      tr.push({x:[y], y:[r.ytd], type:"bar", name:t("o_actual_m", {y: y, m: r.through}), marker:{color:ink, opacity:0.55}, hovertemplate:"%{y:,.0f}<extra></extra>"});
      tr.push({x:[y], y:[r.v - r.ytd], type:"bar", name:t("o_fc_rest", {y: y}), marker:{color:accent},
        error_y:{type:"data", symmetric:false, array:[r.hi - r.v], arrayminus:[r.v - r.lo], color:accent},
        hovertemplate:`≈ ${nf(r.v)} (${nf(r.lo)} – ${nf(r.hi)})<extra></extra>`}); });
    L.barmode = "stack"; L.xaxis.type = "category";
  } else {
    const P = O.points, yr = P.filter(p => p.kind === "year"), mo = P.filter(p => p.kind === "month" || p.kind === "span"),
          lg = P.filter(p => p.kind === "long");
    const x = p => p.m + "-01";
    tr.push({x:yr.map(x), y:yr.map(p => { const yd = (+p.m.slice(0,4) % 4 === 0) ? 366 : 365;
      return og === "day" ? p.v * 12 / yd : og === "week" ? p.v * 12 / yd * 7 : p.v; }), name:t("o_year12"), mode:"lines",
      line:{color:grey, width:2, dash:"dash", shape:"hv"}, hovertemplate:"%{y:,.0f}<extra></extra>"});
    if (lg.length) tr.push({x:lg.map(x), y:lg.map(p => per(p.m, p.v)), name:t("o_avg_months"), mode:"lines",
      line:{color:grey, width:2, dash:"dot", shape:"hv"}, hovertemplate:"%{y:,.0f}<extra></extra>"});
    tr.push({x:mo.map(x), y:mo.map(p => per(p.m, p.v)), name:t("o_official_m"), mode:"lines+markers",
      line:{color:ink, width:2.5}, marker:{size:7, color:ink, symbol:mo.map(p => p.exact ? "circle" : "circle-open")},
      text:mo.map(p => p.kind === "span" ? t("o_span") : p.exact ? t("o_exact") : t("o_rounded")),
      hovertemplate:"%{y:,.0f} — %{text}<extra></extra>"});
    if (O.forecast && O.forecast.length) {
      const lastP = mo[mo.length - 1], F = O.forecast;
      const fx = [x(lastP)].concat(F.map(x));
      const lo = [lastP.v].concat(F.map(f => f.lo)), hi = [lastP.v].concat(F.map(f => f.hi));
      const ms = [lastP.m].concat(F.map(f => f.m));
      tr.push({x:fx, y:hi.map((v,i) => per(ms[i], v)), mode:"lines", line:{width:0}, showlegend:false, hoverinfo:"skip"});
      tr.push({x:fx, y:lo.map((v,i) => per(ms[i], v)), mode:"lines", line:{width:0}, fill:"tonexty",
        fillcolor:accent + "33", name:t("o_range"), hoverinfo:"skip"});
      tr.push({x:fx.slice(1), y:F.map(f => per(f.m, f.v)), mode:"lines+markers", name:t("o_fc"),
        line:{color:accent, width:2.5, dash:"dot"}, marker:{size:7, color:accent},
        customdata:F.map(f => [per(f.m, f.lo), per(f.m, f.hi)]),
        hovertemplate:"≈ %{y:,.0f} (%{customdata[0]:,.0f} – %{customdata[1]:,.0f})<extra></extra>"});
      tr.push({x:[x(lastP), fx[1]], y:[per(lastP.m, lastP.v), per(F[0].m, F[0].v)], mode:"lines", showlegend:false,
        hoverinfo:"skip", line:{color:accent, width:2.5, dash:"dot"}});
    }
    L.xaxis.tickformat = "%Y"; L.xaxis.dtick = "M12";
  }
  L.legend = {orientation:"h", y:-0.12, yanchor:"top", font:{size:12}};
  L.margin.b = NARROW ? 170 : 90;
  Plotly.react("overall", tr, L, cfg);
  const M = O.method, Y = M && O.years[M.year];
  const bt = (O.backtest || []).map(b => t("o_bt_item", {y: b.year, f: nf(b.forecast), a: nf(b.actual),
      e: (b.error_pct > 0 ? "+" : "") + dec(b.error_pct), o: b.inside ? "" : t("o_outside")})).join("; ");
  document.getElementById("overall-method").innerHTML = M ? t("o_method", {y: M.year, v: nf(Y.v), lo: nf(Y.lo), hi: nf(Y.hi),
      m: M.through, ytd: nf(Y.ytd), g: dec(M.central, 3), raw: dec(M.raw_central || M.central, 3)}) + (bt ? "<br>" + t("o_bt", {m: M.through, list: bt}) : "") : "";
}
// ---------------------------------------------------------------- world map + events (redrawn on language change)
const MAPS = {};
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
  const pct = v => (v >= 0 ? "+" : "−") + Math.round(Math.abs(v) * 100) + "%";
  const nm = id => { const c = M.countries[id], f = feats.find(x => x.id === id);
    return cname(A2[id], (c && (LANG === "uz" ? c.n : c.e)) || (f ? f.properties.name : id)); };
  const MARKET_ISO_JS = {zh:"156", ko:"410", ja:"392", de:"276", tr:"792", it:"380", fr:"250", hi:"356", kk:"398", ky:"417", tg:"762", tk:"795", ps:"004", ru:"643"};
  const MK = l => flag(LANG_A2[l]);
  const warm = d3.interpolateRgbBasis(["#22344f", "#46506a", "#8a7236", "#d4af37", "#fbe7a8"]);
  const div = d3.interpolateRgbBasis(["#3d6fb0", "#7d9cc4", "#2a3a54", "#c9a13a", "#fbe0a0"]);
  function value(id){
    const c = M.countries[id];
    if (metric === "arrivals") return c && c.y[year] > 0 ? c.y[year] : null;
    if (metric === "growth") { if (!c || !(c.y[year] > 0) || !(c.y[year-1] > 0)) return null; return c.y[year] / c.y[year-1]; }
    const m = M.markets[id]; if (!m) return null;
    return metric === "share" ? m.share30 : (m.change == null ? null : 1 + m.change);
  }
  function scale(){
    const vals = feats.map(f => value(f.id)).filter(v => v != null && v > 0);
    if (metric === "arrivals") return d3.scaleSequentialLog([10, d3.max(vals) || 10], warm);
    if (metric === "share") return d3.scaleSequentialLog([Math.max(1, d3.min(vals) || 1), d3.max(vals) || 10], warm);
    return d3.scaleDivergingLog([0.25, 1, 4], div).clamp(true);
  }
  const lands = g.append("g").selectAll("path").data(feats).join("path")
    .attr("class", d => "land" + (d.id === "860" ? " uzb" : "")).attr("d", path)
    .on("mousemove", (ev, d) => tip(ev, d)).on("mouseleave", () => { document.getElementById("tip").hidden = true; })
    .on("click", (ev, d) => { selected = d.id; paint(); panel(); });
  svg.call(d3.zoom().scaleExtent([1, 8]).translateExtent([[0, 0], [W, H]]).on("zoom", e => g.attr("transform", e.transform)));
  function label(v){
    if (v == null) return t("no_data");
    if (metric === "arrivals") return nf(v) + " " + t("tourists_w");
    if (metric === "growth") return pct(v - 1) + " " + t("vs_prev_year");
    if (metric === "share") return dec(v) + " / " + t("per_million_short");
    return pct(v - 1) + " " + t("vs_last_year");
  }
  function tip(ev, d){
    const el = document.getElementById("tip"), box = document.querySelector("#map-box .mapwrap").getBoundingClientRect();
    el.innerHTML = `<b>${nm(d.id)}</b><br>${d.id === "860" ? "" : label(value(d.id))}`;
    el.hidden = false; el.style.left = Math.min(ev.clientX - box.left + 12, box.width - 200) + "px"; el.style.top = (ev.clientY - box.top + 12) + "px";
  }
  function paint(){
    const sc = scale();
    lands.attr("fill", d => { const v = value(d.id); return v == null ? null : sc(v); })
         .classed("nodata", d => value(d.id) == null).classed("sel", d => d.id === selected);
    lands.filter(d => d.id === selected).raise();
    document.getElementById("yearrow").style.display = (metric === "arrivals" || metric === "growth") ? "flex" : "none";
    document.getElementById("yearlbl").textContent = year + (metric === "growth" ? " " + t("vs_year", {y: year - 1}) : "");
    legend(sc);
  }
  function legend(sc){
    const el = document.getElementById("legend"), dom = sc.domain(), n = 6;
    const stops = d3.range(n).map(i => metric === "arrivals" || metric === "share"
      ? Math.exp(Math.log(dom[0]) + i/(n-1) * (Math.log(dom[dom.length-1]) - Math.log(dom[0])))
      : Math.exp(Math.log(0.25) + i/(n-1) * Math.log(16)));
    const grad = stops.map((v,i) => `${sc(v)} ${i/(n-1)*100}%`).join(",");
    const ticks = metric === "arrivals" ? [stops[0], stops[n-1]].map(v => d3.format(".2s")(v))
      : metric === "share" ? [stops[0], stops[n-1]].map(v => v.toFixed(0)) : ["−75%", "0", "+300%"];
    const title = {arrivals: t("lg_arrivals", {y: year}), growth: t("lg_growth", {y: year}), share: t("lg_share"), change: t("lg_change")}[metric];
    el.innerHTML = `<div>${title}</div><div class="bar" style="background:linear-gradient(90deg,${grad})"></div><div class="ticks">${ticks.map(x=>`<span>${x}</span>`).join("")}</div>` +
      (metric === "share" || metric === "change" ? `<div style='margin-top:3px'>${t("lg_only_tracked")}</div>` : "");
  }
  function pp(x){ return x && x.p != null ? "~" + Math.round(x.p*100) + "%" : t("not_enough"); }
  function panel(){
    const id = selected, c = M.countries[id], m = M.markets[id], el = document.getElementById("panel");
    if (id === "860") { el.innerHTML = `<h3>${cname("UZ")}</h3><p class="note">${t("total_foreign")}:</p><dl class="kv">${Object.entries(M.totals).map(([y,v])=>`<dt>${y}</dt><dd>${nf(v)}</dd>`).join("")}</dl>`; return; }
    let h = `<h3>${flag(A2[id])} ${nm(id)}</h3><dl class="kv">`;
    if (c) {
      const ly = years[years.length-1], v = c.y[ly], v0 = c.y[ly-1], share = M.totals[ly] ? v / M.totals[ly] : null;
      h += `<dt>${t("tourists_y", {y: ly})}</dt><dd>${v ? nf(v) : "—"}</dd>`;
      if (v0) h += `<dt>${t("vs_year", {y: ly - 1})}</dt><dd>${pct(v / v0 - 1)}</dd>`;
      if (share) h += `<dt>${t("share_total")}</dt><dd>${dec(share * 100, 2)}%</dd>`;
    } else h += `<dt>${t("tourists_w")}</dt><dd>${t("no_data")}</dd>`;
    const mm = M.monthly[id];
    if (mm && mm.length) h += `<dt>${t("in_months", {y: mm[0].m.slice(0,4), n: mm.length})}</dt><dd>${nf(d3.sum(mm, x => x.v))}</dd>`;
    if (m) {
      h += `<dt>${t("wiki_30")}</dt><dd>${nf(m.views30)}</dd>`;
      if (m.share30 != null) h += `<dt>${t("per_million_med")}</dt><dd>${dec(m.share30)}</dd>`;
      if (m.change != null) h += `<dt>${t("interest_yoy")}</dt><dd>${pct(m.change)}</dd>`;
    }
    h += `</dl><div id="mini1" class="mini"></div>`;
    if (m) h += `<div id="mini2" class="mini"></div>`;
    const effs = (M.effects[id] || []);
    const ups = (M.upcoming || []).filter(u => u.isos.includes(id));
    if (effs.length) h += `<b>${t("past_events")}</b><ul class="evlist">` + effs.map(e => `<li>${e.date}: ${e.title} — ${t("wiki_w")} ${e.wiki_ratio == null ? "—" : "×" + dec(e.wiki_ratio, 2)}, ${t("tourists_w")} ${e.excess == null ? t("pending") : "×" + dec(e.excess, 2)}${(e.arr_verdict||"").includes("(") ? " <i>(" + t("unreliable") + ")</i>" : ""}</li>`).join("") + `</ul>`;
    if (ups.length) h += `<b>${t("upcoming_w")}</b><ul class="evlist">` + ups.map(u => `<li>${u.date}: ${u.title} — ${pp(u.estimate.info)} ${t("interest_w")}, ${pp(u.estimate.arr)} ${t("tourists_w")}</li>`).join("") + `</ul>`;
    if (!m) h += `<p class="note">${t("not_tracked")}</p>`;
    el.innerHTML = h;
    if (typeof Plotly === "undefined") return;
    const mini = (title, xtype) => ({paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)", margin:{l:44,r:6,t:22,b:26},
      font:{family:"EB Garamond, Georgia, serif", size:12, color:css("--ink")}, showlegend:false, separators: LANG === "en" ? ".," : ", ",
      title:{text:title, font:{size:13}}, xaxis:{type:xtype, gridcolor:css("--rule")+"44"},
      yaxis:{gridcolor:css("--rule")+"44", rangemode:"tozero"}});
    if (c) { const L1 = mini(t("mini_arr"), "linear"); L1.xaxis.dtick = 2; L1.xaxis.tickformat = "d";
      Plotly.react("mini1", [{type:"bar", x:Object.keys(c.y).map(Number), y:Object.values(c.y), marker:{color:css("--accent")}}],
      L1, {displayModeBar:false, responsive:true}); }
    if (m) { const s = D.series.find(x => x.lang === m.lang), n = 730;
      Plotly.react("mini2", [{type:"scatter", mode:"lines", x:D.dates.slice(-n), y:s.avg7.slice(-n), line:{color:css("--blue"), width:1.4}}],
      mini(t("mini_wiki"), "date"), {displayModeBar:false, responsive:true}); }
  }
  document.querySelectorAll("[data-metric]").forEach(b => b.onclick = () => { metric = b.dataset.metric;
    document.querySelectorAll("[data-metric]").forEach(x => x.classList.toggle("on", x === b)); paint(); });
  slider.oninput = () => { year = +slider.value; paint(); };

  // upcoming / past events cards
  const box = document.getElementById("upcoming"), U = M.upcoming || [], R = M.recent || [];
  const sg = v => (v > 0 ? "+" : v < 0 ? "−" : "±") + nf(Math.abs(v));
  const mkt = l => MK(l) + " " + nm(MARKET_ISO_JS[l]);
  function expect(u){
    const x = u.estimate.expected || {};
    if (!x.markets || !Object.keys(x.markets).length) return `<p class="note">🔢 ${t("exp_none", {n: x.n || 0})}</p>`;
    const rows = Object.entries(x.markets).sort((a,b) => b[1].base_month - a[1].base_month).map(([l,m]) =>
      `<tr><td>${mkt(l)}</td><td>${nf(m.base_month)}</td><td><b>${sg(m.mid)}</b></td><td>${sg(m.low)} … ${sg(m.high)}</td><td class="note">${m.basis}</td></tr>`).join("");
    const concl = x.q25 > 1.05 ? t("exp_rose") : t("exp_flat");
    return `<p style="margin:8px 0 0"><b>🔢 ${t("exp_t")}</b> <span class="note">(${t("exp_n", {n: x.n})})</span></p>` +
      `<table class="exp"><tr><th>${t("c_market")}</th><th>${t("c_now_month")}</th><th>${t("c_expected")}</th><th>${t("c_range")}</th><th>${t("c_basis")}</th></tr>${rows}</table><p class="note" style="margin:4px 0 0">${concl}</p>`;
  }
  const row = (lbl, x) => x && x.p != null
    ? `<span>${lbl}</span><span><div class="meter"><i style="width:${Math.round(x.p*100)}%"></i></div> <b>~${Math.round(x.p*100)}%</b> — ${t("in_similar", {k: x.k, n: x.n, c: t("conf_" + x.conf)})}</span>`
    : `<span>${lbl}</span><span>${t("not_enough_n", {n: x ? x.n : 0})}</span>`;
  let dir = "next", win = 366;
  const card = u => `<div class="upcard"><b>${u.title}</b><div class="note">${u.date}${u.precision && u.precision !== "day" ? " (" + t("approx") + ": " + t("prec_" + u.precision) + ")" : ""} · ${t("in_days", {n: u.days})} · ${t("type_" + u.type)} · ` +
      `${u.markets === "all" ? t("all_distant") : u.markets === "neighbours" ? t("neighbours") : u.isos.map(nm).join(", ")}${u.source ? ` · <a href="${u.source}" target="_blank" rel="noopener">${t("source")}</a>` : ""}</div>` +
      `<div class="p">${row("📖 " + t("info_search"), u.estimate.info)}${row("🧳 " + t("arrivals_w"), u.estimate.arr)}</div>` + expect(u) + `</div>`;
  const pastCard = r => {
    const rows = r.rows.map(x => `<tr><td>${mkt(x.lang)}</td><td>${x.wiki_ratio == null ? "—" : "×" + dec(x.wiki_ratio, 2) + " (" + (x.wiki_overlap ? t("mixed") : t("wv_" + (x.wiki_verdict || "none"))) + ")"}</td>` +
      `<td>${x.arr_before == null ? t("pending") : nf(x.arr_before) + " → " + nf(x.arr_after)}</td><td>${x.excess == null ? "—" : "×" + dec(x.excess, 2)}</td></tr>`).join("");
    return `<div class="upcard"><b>${r.title}</b><div class="note">${r.date} · ${t("days_ago", {n: r.days_ago})} · ${t("type_" + r.type)}${r.source ? ` · <a href="${r.source}" target="_blank" rel="noopener">${t("source")}</a>` : ""}</div>` +
      `<table class="exp"><tr><th>${t("c_market")}</th><th>${t("c_wiki7")}</th><th>${t("c_before_after")}</th><th>${t("c_diff")}</th></tr>${rows}</table></div>`;
  };
  function renderList(){
    const wn = t("win_" + win);
    if (dir === "next") {
      const L = U.filter(u => u.days < win);
      box.innerHTML = L.length ? L.map(card).join("") : `<p class="note">${t("none_next", {w: wn, e: U.length ? U[0].date + " — " + U[0].title : "—"})}</p>`;
    } else {
      const L = R.filter(r => r.days_ago < win);
      box.innerHTML = L.length ? L.map(pastCard).join("") : `<p class="note">${t("none_past", {w: wn})}</p>`;
    }
  }
  document.querySelectorAll("[data-dir]").forEach(b => b.onclick = () => { dir = b.dataset.dir;
    document.querySelectorAll("[data-dir]").forEach(x => x.classList.toggle("on", x === b)); renderList(); });
  document.querySelectorAll("[data-win]").forEach(b => b.onclick = () => { win = +b.dataset.win;
    document.querySelectorAll("[data-win]").forEach(x => x.classList.toggle("on", x === b)); renderList(); });
  MAPS.refresh = () => { paint(); panel(); renderList(); };
})();
function renderEvents(){
  const box = document.getElementById("events-box");
  if (!D.effects || !D.effects.length) { box.style.display = "none"; return; }
  const av = v => (!v || v === "—") ? t("pending") : v.startsWith("rose") ? t("av_rose") : v.startsWith("fell") ? t("av_fell") : t("av_none");
  const esc = x => String(x ?? "").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
  const src = Object.fromEntries((D.events||[]).map(e => [e.id, e.source]));
  const mk = l => flag(LANG_A2[l]) + " " + (l === "en" ? t("series_en") : l === "ru" ? t("series_ru") : cname(LANG_A2[l]));
  let h = `<tr><th>${t("c_event")}</th><th>${t("c_date")}</th><th>${t("c_type")}</th><th>${t("c_market")}</th><th>${t("c_wiki7")}</th><th>${t("c_before_after")}</th><th>${t("c_diff")}</th><th>${t("c_result")}</th></tr>`;
  for (const r of D.effects) {
    const mixed = (r.arr_verdict||"").includes("(");
    const wiki = r.wiki_ratio == null ? "—" : `×${dec(r.wiki_ratio, 2)} (${r.wiki_overlap ? t("mixed") : t("wv_" + (r.wiki_verdict || "none"))})`;
    const arr = r.arr_before == null ? t("pending") : `${nf(r.arr_before)} → ${nf(r.arr_after)}` +
      (r.arr_method === "monthly" ? " /" + t("u_month") : ` (${esc((r.arr_window||"").split(" (")[0])})`);
    const ex = r.excess == null ? "—" : `<span class="pill ${r.excess>=1.2?"up":r.excess<=0.83?"down":""}">×${dec(r.excess, 2)}</span>`;
    const v = r.arr_verdict||"";
    const note = v.includes("mixed") ? " — " + t("n_mixed") : v.includes("COVID") ? " — " + t("n_covid")
               : v.includes("season") ? " — " + t("n_season") : (r.season_year ? ` (${t("n_season_y")}: ${r.season_year})` : "");
    h += `<tr class="${mixed?"mixed":""}"><td><a href="${esc(src[r.id])}" target="_blank" rel="noopener">${esc(r.title)}</a></td><td>${esc(r.date)}</td>` +
         `<td>${t("type_" + r.type)}</td><td>${mk(r.lang)}</td><td>${wiki}</td><td>${arr}</td><td>${ex}</td><td>${av(r.arr_verdict)}${note}</td></tr>`;
  }
  document.getElementById("ev-table").innerHTML = h;
  let s = `<table><tr><th>${t("c_type")}</th><th>${t("c_events")}</th><th>${t("c_wiki_react")}</th><th>${t("c_arr_rose")}</th><th>${t("c_med_diff")}</th></tr>`;
  for (const r of (D.ev_summary||[])) s += `<tr><td>${t("type_" + r.type)}</td><td>${r.events}</td>` +
    `<td>${r.wiki_reacted} / ${r.measured_wiki}</td><td>${r.arrivals_rose} / ${r.measured_arrivals}</td><td>${r.median_excess==null?"—":"×"+dec(r.median_excess, 2)}</td></tr>`;
  document.getElementById("ev-summary").innerHTML = s + "</table>";
}
// ---------------------------------------------------------------- wiring
document.querySelectorAll("[data-gran]").forEach(b => b.onclick = () => {
  gran = b.dataset.gran; document.querySelectorAll("[data-gran]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });
document.querySelectorAll("[data-scale]").forEach(b => b.onclick = () => {
  scale = b.dataset.scale; document.querySelectorAll("[data-scale]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });
document.querySelectorAll("[data-og]").forEach(b => b.onclick = () => {
  og = b.dataset.og; document.querySelectorAll("[data-og]").forEach(x => x.classList.toggle("on", x===b)); drawOverall(); });
function drawAll(){
  applyStatic(); drawKpis(); renderEvents();
  if (typeof Plotly === "undefined") {
    document.querySelectorAll(".chart").forEach(c => c.innerHTML = `<p style="padding:20px">${t("no_plotly")}</p>`);
  } else {
    drawOverall(); drawScore(); drawLeisure(); drawViews(); drawShare(); drawTrends(); drawArrivals();
  }
  if (typeof d3 !== "undefined") drawAttraction();
  if (MAPS.refresh) MAPS.refresh();
}
document.querySelectorAll("[data-lang]").forEach(b => b.onclick = () => {
  LANG = b.dataset.lang;
  try { localStorage.setItem("utm_lang", LANG); } catch (e) {}
  try { const u = new URL(location.href); u.searchParams.set("lang", LANG); history.replaceState(null, "", u); } catch (e) {}
  drawAll();
});
drawAll();
const off = document.getElementById("offline");
if (off) off.onclick = async e => {
  e.preventDefault(); off.textContent = t("dl_preparing");
  try {
    const END = "</scr" + "ipt>";
    const libs = ["plotly.min.js", "d3.min.js", "topojson-client.min.js"];
    let html = await fetch(location.href.split("?")[0]).then(r => r.text());
    for (const name of libs) {
      const code = await fetch(name).then(r => r.text());
      const inline = "<scr" + "ipt>" + code.split(END).join("<\\/scr" + "ipt>") + END;
      html = html.replace('<script src="' + name + '">' + END, () => inline);  // function: "$" stays literal
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([html], {type: "text/html"}));
    a.download = "uzbekistan_tourism_monitor_" + D.last + ".html"; a.click();
    off.textContent = t("dl_offline");
  } catch (err) { off.textContent = t("dl_error"); }
};
</script>
</body>
</html>
"""
