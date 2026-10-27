"""Builds docs/index.html: every day of collected data in interactive charts, plus CSV downloads.
Published by GitHub Pages and rebuilt after each daily run."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import config, events, forecast, pageviews, statuz
from .util import log

DOCS = config.ROOT / "docs"
import shutil  # noqa: E402

# Libraries kept in the repo (vendor/), served next to the page: no outside CDN needed.
VENDOR = config.ROOT / "vendor"
VENDOR_JS = VENDOR / "plotly.min.js"
PLOTLY = "plotly.min.js"
LIBS = ["plotly.min.js", "d3.min.js", "topojson-client.min.js"]
MARKET_ISO = {"zh": "156", "ko": "410", "ja": "392", "de": "276", "tr": "792", "it": "380", "fr": "250", "hi": "356",
              "kk": "398", "ky": "417", "tg": "762", "tk": "795", "ps": "004", "ru": "643"}
COLORS = {"zh": "#a23b2a", "ko": "#2f5d7c", "ja": "#c47f2c", "de": "#3d6b45", "tr": "#7a3b6b",
          "it": "#5b7f99", "fr": "#8a6d3b", "hi": "#c06a2b",
          "kk": "#4b8f8c", "ky": "#b5651d", "tg": "#6a8f3a", "tk": "#7d6aa8", "ps": "#9b4f3c", "en": "#6e6e6e", "ru": "#9a9a9a"}


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
    recent = []
    if events.EFFECTS.exists():
        effs = pd.read_csv(events.EFFECTS)
        evs = events.load_events().set_index("id")
        today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
        for eid, g in effs.groupby("id"):
            d = pd.Timestamp(evs.at[eid, "date"])
            if not (today - pd.Timedelta(days=366) <= d < today):
                continue
            rows = [{k: _clean(v) for k, v in r.items()} for r in g.to_dict("records")]
            recent.append({"id": eid, "date": evs.at[eid, "date"], "type": evs.at[eid, "type"],
                           "title": evs.at[eid, "title"], "source": evs.at[eid, "source"],
                           "days_ago": int((today - d).days), "rows": rows})
    ups = []
    for u in events.upcoming():
        langs = events.expand(u["markets"])
        ups.append(u | {"isos": [MARKET_ISO[l] for l in langs if l in MARKET_ISO],
                        "estimate": json.loads(json.dumps(u["estimate"], default=str))})
    return {"topo": topo, "countries": countries, "totals": totals, "markets": markets,
            "monthly": monthly, "effects": by_iso_effects, "upcoming": ups, "recent": sorted(recent, key=lambda r: r["date"], reverse=True),
            "years": sorted(totals) if totals else []}


TRENDS_GEO = {"US": "🇺🇸 AQSh", "GB": "🇬🇧 Buyuk Britaniya", "DE": "🇩🇪 Germaniya", "FR": "🇫🇷 Fransiya",
              "IT": "🇮🇹 Italiya", "JP": "🇯🇵 Yaponiya", "KR": "🇰🇷 Koreya", "IN": "🇮🇳 Hindiston",
              "CN": "🇨🇳 Xitoy", "TR": "🇹🇷 Turkiya", "RU": "🇷🇺 Rossiya", "KZ": "🇰🇿 Qozog'iston"}


def trends_data() -> dict | None:
    """Uzbekistan's share of searches among 5 destinations, by market: yearly history + latest 90 days."""
    from . import trends
    df = trends.load()
    if df.empty:
        return None
    df = df[df["geo"].isin(TRENDS_GEO)]
    df["period"] = df["period"].astype(str)
    years = sorted(p for p in df["period"].unique() if p.isdigit())
    snaps = sorted(p for p in df["period"].unique() if p.startswith("90d-"))
    out = {"years": years, "snapshot": snaps[-1][4:] if snaps else None, "markets": [],
           "destinations": [trends.NAMES_UZ[d] for d in trends.TOPICS]}
    for geo, name in TRENDS_GEO.items():
        g = df[df["geo"] == geo]
        uz = g[g["destination"] == "Uzbekistan"].set_index("period")["share"]
        latest = g[g["period"] == (snaps[-1] if snaps else years[-1])].set_index("destination")["share"]
        out["markets"].append({"geo": geo, "name": name,
                               "years": [None if y not in uz.index else int(uz[y]) for y in years],
                               "latest": [int(latest.get(d, 0)) for d in trends.TOPICS]})
    return out


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
            "dash": "dot" if info["flag"] == "🌐" else "solid", "group": info.get("group", ""),
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

    try:
        overall = forecast.build()
        overall["backtest"] = forecast.backtest()
    except Exception:  # noqa: BLE001  the page must still build if the forecast fails
        log.exception("overall forecast failed")
        overall = None
    data = {"dates": dates, "series": series, "monthly": monthly, "overall": overall, "trends": trends_data(), "map": map_data(wide, proj, mon),
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
#views{height:540px}
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
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px}
h3.sub{font-size:16px;margin:6px 0 2px;font-weight:600}
#trends-latest,#trends-years{min-height:420px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Uzbekistan Tourism Monitor<small>O'zbekistonga xalqaro qiziqish — har bir kun</small></h1>
  <div class="meta" id="meta"></div>
</header>

<section id="upcoming-box">
  <div class="controls" id="period-btns" style="float:right;margin:0">
    <button data-dir="next" class="on">Kelgusi</button><button data-dir="past">O'tgan</button>
  </div>
  <h2>Kutilayotgan voqealar va ularning kutilgan ta'siri</h2>
  <p class="note">Voqea qo'shish: Telegram botga oddiy so'zlar bilan yozing (masalan, «5-dekabr kuni Samarqandda festival, Xitoy va Koreyadan mehmonlar kutilmoqda») yoki yangilikni ✅ bilan tasdiqlang. Ehtimollar — o'tgan o'lchangan o'xshash voqealarga asoslangan ulush, bashorat emas. Voqea o'tgach, haqiqiy ta'sir o'zi o'lchanadi.</p>
  <div class="controls" id="win-btns">
    <button data-win="1">Kun</button><button data-win="7">Hafta</button><button data-win="31">Oy</button>
    <button data-win="366" class="on">Yil</button><button data-win="99999">Hammasi</button>
  </div>
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
<section id="overall-box">
  <h2>Jami xorijiy turistlar: 2018 – 2026 (prognoz bilan)</h2>
  <p class="note"><b>Muhim:</b> rasmiy statistika faqat <b>oylik</b> (2022-yil avgustidan, ba'zi oylar yo'q) va <b>yillik</b> chiqadi; kunlik yoki haftalik rasmiy raqam yo'q.
  Shuning uchun "Kun" va "Hafta" — o'rtacha qiymat (oy ÷ kunlar soni, ×7). Kulrang uzuq chiziq — oylik ma'lumot yo'q davr (yillik jami ÷ 12 yoki bir necha oy o'rtachasi, mavsum ko'rinmaydi).
  Ochiq nuqta — manbada yaxlitlangan yoki ikki oy birga e'lon qilingan (teng bo'lingan). Rangli soha — prognoz oralig'i.</p>
  <div class="controls">
    <button data-og="day">Kun</button><button data-og="week">Hafta</button>
    <button data-og="month" class="on">Oy</button><button data-og="year">Yil</button>
  </div>
  <div id="overall" class="chart"></div>
  <p class="note" id="overall-method"></p>
</section>
<section>
  <h2>Vikipediya ko'rishlari — kun, hafta, oy, yil</h2>
  <p class="note">O'zbekiston, Samarqand, Buxoro, Xiva, Toshkent sahifalari, har bir til = bir bozor. Hafta/oy/yil — shu davrdagi ko'rishlar yig'indisi (tugallanmagan oxirgi davr ko'rsatilmaydi). Qo'shni davlatlar yashirin — legendani bosib yoqing. ▼ — voqealar. Kamera belgisi grafikni PNG qilib yuklaydi.</p>
  <div class="controls">
    <button data-gran="day">Kun</button><button data-gran="week" class="on">Hafta</button>
    <button data-gran="month">Oy</button><button data-gran="year">Yil</button>
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

<section id="trends-box">
  <h2>Google qidiruvlari: O'zbekiston raqobatchilar orasida</h2>
  <p class="note">Har bir davlatda 5 ta yo'nalish (O'zbekiston, Qozog'iston, Qirg'iziston, Gruziya, Tojikiston) haqidagi Google qidiruvlari 100% deb olinsa, O'zbekistonga qanchasi to'g'ri keladi. Manba: Google Trends (mavzular, tildan qat'i nazar), har hafta yangilanadi.
  <b>Ehtiyot bo'ling:</b> bu barcha qidiruvlar — yangiliklar, sport, biznes, faqat sayohat emas. 2026 yilgi o'sish asosan FIFA Jahon chempionati bilan bog'liq bo'lishi mumkin. Xitoyda Google bloklangan — u yerdagi raqamlar kam sonli foydalanuvchiga asoslangan.</p>
  <div class="grid2">
    <div><h3 class="sub" id="trends-latest-title">So'nggi 90 kun</h3><div id="trends-latest" class="chart"></div></div>
    <div><h3 class="sub">O'zbekiston ulushi yillar bo'yicha, %</h3><div id="trends-years" class="chart"></div></div>
  </div>
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
    <a class="btn" href="reports/latest.docx" download>Haftalik hisobot (Word, .docx)</a>
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
let gran = "week", scale = "log";
// sum daily values into weeks (Monday start), months or years; incomplete last period is dropped
function aggregate(dates, vals, g){
  if (g === "day") return {x:dates, y:vals};
  const key = d => g === "year" ? d.slice(0,4) : g === "month" ? d.slice(0,7) + "-01" : (() => {
    const t = new Date(d + "T00:00:00Z"); const wd = (t.getUTCDay() + 6) % 7; t.setUTCDate(t.getUTCDate() - wd);
    return t.toISOString().slice(0,10); })();
  const m = new Map(), n = new Map();
  dates.forEach((d,i) => { const k = key(d); if (vals[i] != null) { m.set(k, (m.get(k)||0) + vals[i]); } n.set(k, (n.get(k)||0) + 1); });
  const full = g === "week" ? 7 : g === "month" ? 28 : 365;
  const keys = [...m.keys()].filter((k,i,a) => i < a.length - 1 || n.get(k) >= full);
  return {x: g === "year" ? keys.map(k => k + "-07-01") : keys, y: keys.map(k => m.get(k))};
}
function drawViews(){
  const tr = D.series.map(s => { const a = aggregate(D.dates, s.daily, gran);
    return {x:a.x, y:a.y, name:s.name, type: gran === "day" ? "scattergl" : "scatter", mode: gran === "year" ? "lines+markers" : "lines",
      visible: s.group === "neighbour" ? "legendonly" : true,
      line:{color:s.color, width: gran==="day" ? 1 : 1.8, dash:s.dash}}; });
  const unit = {day:"kun", week:"hafta", month:"oy", year:"yil"}[gran];
  const L = layout("ko'rishlar / " + unit, scale==="log");
  L.shapes = (D.events||[]).map(e => ({type:"line", xref:"x", yref:"paper", x0:e.date, x1:e.date, y0:0, y1:1,
    line:{color:css("--accent"), width:1, dash:"dot"}}));
  // event markers: dotted lines + one hoverable point per event at the top (no crowded labels)
  const ev = D.events || [];
  tr.push({x: ev.map(e => e.date), y: ev.map(() => 1), yaxis: "y2", type: "scatter", mode: "markers", name: "Voqealar",
    marker: {symbol: "triangle-down", size: 9, color: css("--accent")}, hovertext: ev.map(e => e.date + ": " + e.title),
    hoverinfo: "text", showlegend: true});
  L.yaxis2 = {overlaying: "y", range: [0, 1.02], visible: false, fixedrange: true};
  L.xaxis.rangeslider = {visible: false};
  L.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}};
  L.margin.b = NARROW ? 260 : 120;
  Plotly.react("views", tr, L, cfg);
}
function drawTrends(){
  const T = D.trends, box = document.getElementById("trends-box");
  if (!T || !T.markets || !T.markets.length) { box.style.display = "none"; return; }
  const ms = T.markets.slice().sort((a, b) => a.latest[0] - b.latest[0]);
  const pal = [css("--accent"), "#7a8b99", "#a89c7d", "#8aa38b", "#b9a2a2"];
  const bars = T.destinations.map((d, i) => ({type: "bar", orientation: "h", name: d, y: ms.map(m => m.name),
    x: ms.map(m => m.latest[i]), marker: {color: pal[i]}, hovertemplate: "%{y}: %{x}%<extra>" + d + "</extra>",
    text: i === 0 ? ms.map(m => m.latest[0] + "%") : null, textposition: "inside", insidetextanchor: "start"}));
  const L1 = layout("%", false);
  L1.barmode = "stack"; L1.xaxis = {range: [0, 100], gridcolor: css("--rule") + "55", ticksuffix: "%"};
  L1.yaxis = {automargin: true}; L1.hovermode = "closest";
  L1.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L1.margin = {l: 10, r: 10, t: 10, b: 70};
  if (T.snapshot) document.getElementById("trends-latest-title").textContent = "So'nggi 90 kun (" + T.snapshot + " gacha)";
  Plotly.react("trends-latest", bars, L1, cfg);
  const lines = T.markets.filter(m => m.geo !== "KZ").map(m => ({type: "scatter", mode: "lines+markers", name: m.name,
    x: T.years, y: m.years, visible: ["DE", "KR", "IN", "US", "JP"].includes(m.geo) ? true : "legendonly",
    hovertemplate: "%{x}: %{y}%<extra>" + m.name + "</extra>"}));
  const L2 = layout("%", false);
  L2.xaxis = {type: "category", gridcolor: css("--rule") + "55"}; L2.yaxis.rangemode = "tozero"; L2.yaxis.ticksuffix = "%";
  L2.legend = {orientation: "h", y: -0.12, yanchor: "top", font: {size: 12}}; L2.margin = {l: 40, r: 10, t: 28, b: 110};
  // category axis: number-like strings ("2026") are read as numbers in shapes, so use the index
  const wc = T.years.indexOf("2026");
  L2.shapes = wc < 0 ? [] : [{type: "line", xref: "x", yref: "paper", x0: wc, x1: wc, y0: 0, y1: 1, line: {color: css("--accent"), width: 1, dash: "dot"}}];
  L2.annotations = wc < 0 ? [] : [{x: wc, y: 1, yref: "paper", text: "Jahon chempionati", showarrow: false, font: {size: 11, color: css("--accent")}, xanchor: "right", yanchor: "bottom"}];
  Plotly.react("trends-years", lines, L2, cfg);
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
document.querySelectorAll("[data-gran]").forEach(b => b.onclick = () => {
  gran = b.dataset.gran; document.querySelectorAll("[data-gran]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });
document.querySelectorAll("[data-scale]").forEach(b => b.onclick = () => {
  scale = b.dataset.scale; document.querySelectorAll("[data-scale]").forEach(x => x.classList.toggle("on", x===b)); drawViews(); });

let og = "month";
function drawOverall(){
  const O = D.overall, box = document.getElementById("overall-box");
  if (!O || !O.points || !O.points.length) { box.style.display = "none"; return; }
  const dim = m => new Date(Date.UTC(+m.slice(0,4), +m.slice(5,7), 0)).getUTCDate();
  const per = (m, v) => og === "day" ? v / dim(m) : og === "week" ? v / dim(m) * 7 : v;
  const unit = {day:"turist / kun (o'rtacha)", week:"turist / hafta (o'rtacha)", month:"turist / oy", year:"turist / yil"}[og];
  const nf = v => Math.round(v).toLocaleString("ru-RU");
  const accent = css("--accent"), ink = css("--ink"), grey = css("--rule") || "#999";
  let tr = [];
  const L = layout(unit, false);
  L.xaxis.rangeslider = {visible:false}; L.xaxis.rangeselector = undefined; L.xaxis.type = "date";
  L.yaxis.rangemode = "tozero"; L.hovermode = "x unified";
  if (og === "year") {
    const ys = Object.keys(O.years).sort();
    const act = ys.filter(y => O.years[y].kind === "actual"), fc = ys.filter(y => O.years[y].kind === "forecast");
    tr.push({x:act, y:act.map(y => O.years[y].v), type:"bar", name:"Rasmiy (yillik)",
      marker:{color:ink}, hovertemplate:"%{y:,.0f}<extra>rasmiy</extra>"});
    fc.forEach(y => { const r = O.years[y];
      tr.push({x:[y], y:[r.ytd], type:"bar", name:`${y}: ${r.through} oylik haqiqiy`, marker:{color:ink, opacity:0.55},
        hovertemplate:"%{y:,.0f}<extra>haqiqiy</extra>"});
      tr.push({x:[y], y:[r.v - r.ytd], type:"bar", name:`${y}: prognoz (qolgan oylar)`, marker:{color:accent},
        error_y:{type:"data", symmetric:false, array:[r.hi - r.v], arrayminus:[r.v - r.lo], color:accent},
        hovertemplate:`jami ≈ ${nf(r.v)} (${nf(r.lo)} – ${nf(r.hi)})<extra>prognoz</extra>`}); });
    L.barmode = "stack"; L.xaxis.type = "category";
  } else {
    const P = O.points, yr = P.filter(p => p.kind === "year"), mo = P.filter(p => p.kind === "month" || p.kind === "span"),
          lg = P.filter(p => p.kind === "long");
    const x = p => p.m + "-01";
    const yrTr = {x:yr.map(x), y:yr.map(p => { const yd = (+p.m.slice(0,4) % 4 === 0) ? 366 : 365;  // flat: year / days, not month lengths
      return og === "day" ? p.v * 12 / yd : og === "week" ? p.v * 12 / yd * 7 : p.v; }), name:"Yillik jami ÷ 12 (oylik ma'lumot yo'q)", mode:"lines",
      line:{color:grey, width:2, dash:"dash", shape:"hv"}, hovertemplate:"%{y:,.0f}<extra>yillik o'rtacha</extra>"};
    tr.push(yrTr);
    if (lg.length) tr.push({x:lg.map(x), y:lg.map(p => per(p.m, p.v)), name:"Bir necha oy o'rtachasi (oylik reliz yo'q)", mode:"lines",
      line:{color:grey, width:2, dash:"dot", shape:"hv"}, hovertemplate:"%{y:,.0f}<extra>o'rtacha</extra>"});
    tr.push({x:mo.map(x), y:mo.map(p => per(p.m, p.v)), name:"Rasmiy (oylik)", mode:"lines+markers",
      line:{color:ink, width:2.5}, marker:{size:7, color:ink, symbol:mo.map(p => p.exact ? "circle" : "circle-open")},
      text:mo.map(p => p.kind === "span" ? "ikki oy birga e'lon qilingan, teng bo'lingan" : p.exact ? "aniq" : "yaxlitlangan (≈)"),
      hovertemplate:"%{y:,.0f} — %{text}<extra></extra>"});
    if (O.forecast && O.forecast.length) {
      const lastP = mo[mo.length - 1], F = O.forecast;
      const fx = [x(lastP)].concat(F.map(x)), fy = [lastP.v].concat(F.map(f => f.v));
      const lo = [lastP.v].concat(F.map(f => f.lo)), hi = [lastP.v].concat(F.map(f => f.hi));
      const ms = [lastP.m].concat(F.map(f => f.m));
      tr.push({x:fx, y:hi.map((v,i) => per(ms[i], v)), mode:"lines", line:{width:0}, showlegend:false, hoverinfo:"skip"});
      tr.push({x:fx, y:lo.map((v,i) => per(ms[i], v)), mode:"lines", line:{width:0}, fill:"tonexty",
        fillcolor:accent + "33", name:"Prognoz oralig'i", hoverinfo:"skip"});
      tr.push({x:fx.slice(1), y:F.map(f => per(f.m, f.v)), mode:"lines+markers", name:"Prognoz",
        line:{color:accent, width:2.5, dash:"dot"}, marker:{size:7, color:accent},
        customdata:F.map(f => [per(f.m, f.lo), per(f.m, f.hi)]),
        hovertemplate:"≈ %{y:,.0f} (%{customdata[0]:,.0f} – %{customdata[1]:,.0f})<extra>prognoz</extra>"});
      tr.push({x:[x(lastP), fx[1]], y:[per(lastP.m, lastP.v), per(F[0].m, F[0].v)], mode:"lines", showlegend:false,
        hoverinfo:"skip", line:{color:accent, width:2.5, dash:"dot"}});
    }
    L.xaxis.tickformat = "%Y"; L.xaxis.dtick = "M12";
  }
  L.legend = {orientation:"h", y:-0.12, yanchor:"top", font:{size:12}};
  L.margin.b = NARROW ? 170 : 90;
  Plotly.react("overall", tr, L, cfg);
  const M = O.method, Y = M && O.years[M.year];
  document.getElementById("overall-method").innerHTML = M ? 
    `<b>${M.year}-yil prognozi: ≈ ${nf(Y.v)} turist</b> (oraliq ${nf(Y.lo)} – ${nf(Y.hi)}); shundan ${M.through} oyda haqiqatda ${nf(Y.ytd)} kelgan.
     <b>Usul:</b> qolgan har bir oy = o'tgan yilning shu oyi × oxirgi 3 oy (${M.months.join(", ")}-oylar) o'sishi (×${M.central}).
     Oraliq — oxirgi 6 oydagi eng past va eng yuqori oylik o'sish (×${M.lo} – ×${M.hi}), o'tgan yil raqami yaxlitlangan bo'lsa ±5%.
     Bu "o'sish shunday davom etsa" degan taxmin; sabablar modeli emas. Oylik o'sish ${M.year}-yilda sekinlashmoqda:
     ${Object.entries(M.ratios).map(([k,v]) => k.slice(5) + "-oy ×" + v).join(", ")}.` +
    ((O.backtest || []).length ? `<br><b>Usul tekshiruvi</b> (o'tgan yillarda xuddi shu usul bilan, ${M.through} oylik ma'lumotdan):
     ${O.backtest.map(b => `${b.year}: prognoz ${nf(b.forecast)}, haqiqatda ${nf(b.actual)} (${b.error_pct > 0 ? "+" : ""}${b.error_pct}%${b.inside ? "" : ", oraliqdan tashqarida"})`).join("; ")}.
     Faqat ikki yil — xulosa uchun kam, lekin bu usulning haqiqiy aniqligi.` : "") : "";
}
document.querySelectorAll("[data-og]").forEach(b => b.onclick = () => {
  og = b.dataset.og; document.querySelectorAll("[data-og]").forEach(x => x.classList.toggle("on", x===b)); drawOverall(); });
if (typeof Plotly !== "undefined") { drawOverall(); drawViews(); drawShare(); drawTrends(); drawArrivals(); }
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
  const MARKET_ISO_JS = {zh:"156", ko:"410", ja:"392", de:"276", tr:"792", it:"380", fr:"250", hi:"356", kk:"398", ky:"417", tg:"762", tk:"795", ps:"004", ru:"643"};
  const MK = {zh:"🇨🇳", ko:"🇰🇷", ja:"🇯🇵", de:"🇩🇪", tr:"🇹🇷", it:"🇮🇹", fr:"🇫🇷", hi:"🇮🇳", kk:"🇰🇿", ky:"🇰🇬", tg:"🇹🇯", tk:"🇹🇲", ps:"🇦🇫", ru:"🇷🇺"};
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
      (metric === "share" || metric === "change" ? "<div style='margin-top:3px'>Faqat Vikipediyasi kuzatilayotgan bozorlar</div>" : "");
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
    if (!m) h += `<p class="note">Bu mamlakat uchun Vikipediya qiziqishi kuzatilmaydi (faqat kuzatilayotgan bozorlar).</p>`;
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
  const tn = {visa:"viza", border:"chegara ochilishi", crossing:"o'tish punkti", flight:"reys", event:"tadbir", sport:"sport", politics:"siyosat", price:"narx", infrastructure:"infratuzilma", marketing:"marketing", other:"boshqa"};
  const conf = {low:"past", medium:"o'rta", high:"yuqori"};
  const row = (label, x) => x && x.p != null
    ? `<span>${label}</span><span><div class="meter"><i style="width:${Math.round(x.p*100)}%"></i></div> <b>~${Math.round(x.p*100)}%</b> — ${x.k}/${x.n} o'xshash holatda (ishonch: ${conf[x.conf]})</span>`
    : `<span>${label}</span><span>ma'lumot yetarli emas (${x ? x.n : 0} ta o'xshash voqea)</span>`;
  const R = M.recent || [];
  let dir = "next", win = 366;
  const wv = {strong:"kuchli", some:"biroz", none:"yo'q"};
  const card = u => `<div class="upcard"><b>${u.title}</b><div class="note">${u.date}${u.precision && u.precision !== "day" ? " (taxminiy: " + ({month:"oy", quarter:"chorak"}[u.precision]||u.precision) + ")" : ""} · ${u.days} kundan keyin · ${tn[u.type]||u.type} · ` +
      `${u.markets === "all" ? "barcha uzoq bozorlar" : u.markets === "neighbours" ? "qo'shni davlatlar" : u.isos.map(nm).join(", ")}${u.source ? ` · <a href="${u.source}" target="_blank" rel="noopener">manba</a>` : ""}</div>` +
      `<div class="p">${row("📖 Ma'lumot qidirish", u.estimate.info)}${row("🧳 Turistlar kelishi", u.estimate.arr)}</div>` + expect(u) + `</div>`;
  const pastCard = r => {
    const rows = r.rows.map(x => `<tr><td>${MK[x.lang]||""} ${nm(MARKET_ISO_JS[x.lang])}</td><td>${x.wiki_ratio == null ? "—" : "×" + x.wiki_ratio + " (" + (wv[x.wiki_verdict]||"—") + ")"}</td>` +
      `<td>${x.arr_before == null ? "kutilmoqda" : fmt(Math.round(x.arr_before)) + " → " + fmt(Math.round(x.arr_after))}</td><td>${x.excess == null ? "—" : "×" + x.excess}</td></tr>`).join("");
    return `<div class="upcard"><b>${r.title}</b><div class="note">${r.date} · ${r.days_ago} kun oldin · ${tn[r.type]||r.type}${r.source ? ` · <a href="${r.source}" target="_blank" rel="noopener">manba</a>` : ""}</div>` +
      `<table class="exp"><tr><th>Bozor</th><th>Vikipediya, 7 kun</th><th>Turistlar/oy, oldin → keyin</th><th>Farq</th></tr>${rows}</table></div>`;
  };
  const winName = {1:"bugun", 7:"shu hafta", 31:"shu oy", 366:"shu yil", 99999:"hammasi"};
  function renderList(){
    if (dir === "next") {
      const L = U.filter(u => u.days < win);
      box.innerHTML = L.length ? L.map(card).join("") : `<p class="note">Kelgusi davrda (${winName[win]}) tasdiqlangan voqea yo'q. Eng yaqini: ${U.length ? U[0].date + " — " + U[0].title : "—"}.</p>`;
    } else {
      const L = R.filter(r => r.days_ago < win);
      box.innerHTML = L.length ? L.map(pastCard).join("") : `<p class="note">O'tgan davrda (${winName[win]}) voqea yo'q.</p>`;
    }
  }
  document.querySelectorAll("[data-dir]").forEach(b => b.onclick = () => { dir = b.dataset.dir;
    document.querySelectorAll("[data-dir]").forEach(x => x.classList.toggle("on", x === b)); renderList(); });
  document.querySelectorAll("[data-win]").forEach(b => b.onclick = () => { win = +b.dataset.win;
    document.querySelectorAll("[data-win]").forEach(x => x.classList.toggle("on", x === b)); renderList(); });
  renderList();
})();
(function renderEvents(){
  const box = document.getElementById("events-box");
  if (!D.effects || !D.effects.length) { box.style.display = "none"; return; }
  const tn = {visa:"viza", border:"chegara ochilishi", crossing:"o'tish punkti", flight:"reys", event:"tadbir", sport:"sport", politics:"siyosat", price:"narx",
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
