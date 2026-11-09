"""Builds docs/index.html: every day of collected data in interactive charts, plus CSV downloads.
Published by GitHub Pages and rebuilt after each daily run."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import attraction, config, events, forecast, pageviews, purpose, scorecard, statuz
from .page_i18n import as_json_dict
from .page_template import TEMPLATE
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
# bright tones that read on the dark-blue page; gold is kept for China (largest distant market) and accents
COLORS = {"zh": "#d4af37", "ko": "#6fa8dc", "ja": "#f0c987", "de": "#7fc4a4", "tr": "#c792ea",
          "it": "#9bbbe0", "fr": "#e39a5f", "hi": "#e8d17a",
          "kk": "#5fb3b3", "ky": "#d98e73", "tg": "#a5c46b", "tk": "#a99be0", "ps": "#c9876f", "en": "#b8b8b8", "ru": "#8f9bb0"}


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


def score_data() -> dict | None:
    """Forecast accuracy (rolling back-test + live) and the current 3-month forecasts by country."""
    if not scorecard.SCORES.exists():
        return None
    df = pd.read_csv(scorecard.SCORES)
    summ = scorecard.summary(df)
    acc = []
    for level in ["TOTAL"] + scorecard.COUNTRIES:
        row = {"level": level, "name": scorecard.NAME_UZ.get(level, level)}
        for kind in ("backtest", "live"):
            sub = summ[(summ["kind"] == kind) & (summ["level"] == level)]
            row[kind] = {int(r.h): {"n": int(r.n), "mae": float(r.mae), "bias": float(r.bias)} for r in sub.itertuples()}
        acc.append(row)
    cur = scorecard.current()
    fc = []
    for level in ["TOTAL"] + scorecard.COUNTRIES:
        c = cur.get(level)
        fc.append({"level": level, "name": scorecard.NAME_UZ.get(level, level),
                   "last": c["last"] if c else None, "last_value": c["last_value"] if c else None,
                   "rows": c["rows"] if c else []})
    live_n = int(((df["kind"] == "live") & df["actual"].notna()).sum())
    return {"accuracy": acc, "forecasts": fc, "live_scored": live_n,
            "live_logged": int((df["kind"] == "live").sum()), "damp": forecast.DAMP}


def leisure_data() -> dict | None:
    """Purpose of visit by year (official) + estimated leisure tourists by country (monthly, next 3 months)."""
    try:
        b = purpose.build()
    except Exception:  # noqa: BLE001
        log.exception("leisure estimates failed")
        return None
    py = b["yearly"]
    yearly = []
    for r in py.itertuples():
        other = r.total_k - r.relatives_k - r.leisure_k - r.business_k
        yearly.append({"year": str(int(r.year)), "total": r.total_k, "relatives": r.relatives_k, "leisure": r.leisure_k,
                       "business": r.business_k, "other": round(other, 1)})
    sh, mon, fc = b["shares"], b["monthly"], b["forecast"]
    name = lambda c: purpose.NAME_UZ.get(c, c)  # noqa: E731
    last_year = mon["month"].str[:4].max() if not mon.empty else None
    ytd = mon[mon["month"].str.startswith(last_year or "x")] if last_year else mon
    countries = purpose.MONTHLY + ["OTHER"]
    rows = []
    for c in countries:
        sub = ytd[ytd["country"] == c]
        f = [x for x in fc if x["country"] == c]
        s_row = sh[sh["country"] == c]
        rows.append({"country": c, "name": name(c),
                     "share": float(s_row["share"].iloc[0]) if len(s_row) else None,
                     "share_2023": None if not len(s_row) or pd.isna(s_row["share_2023"].iloc[0]) else float(s_row["share_2023"].iloc[0]),
                     "ytd_leisure": int(sub["leisure"].sum()) if len(sub) else None,
                     "ytd_arrivals": int(sub["arrivals"].sum()) if len(sub) else None,
                     "forecast": [{"target": x["target"], "v": x["leisure"], "lo": x["lo"], "hi": x["hi"]} for x in f]})
    rows.sort(key=lambda r: -(r["ytd_leisure"] or 0))
    tot = ytd[ytd["country"] == "TOTAL"]
    total = {"name": "Jami", "ytd_leisure": int(tot["leisure"].sum()), "ytd_arrivals": int(tot["arrivals"].sum()),
             "forecast": [{"target": x["target"], "v": x["leisure"], "lo": x["lo"], "hi": x["hi"]} for x in fc if x["country"] == "TOTAL"]}
    chart = mon[(mon["country"] != "TOTAL") & (mon["month"] >= "2024-01")]
    months = sorted(chart["month"].unique())
    stack = [{"country": c, "name": name(c), "y": [int(chart[(chart["country"] == c) & (chart["month"] == m)]["leisure"].sum()) for m in months]}
             for c in countries]
    return {"yearly": yearly, "rows": rows, "total": total, "ytd_year": last_year,
            "ytd_months": int(tot["month"].nunique()), "validation": b["validation"],
            "months": months, "stack": stack}


def attraction_data() -> dict | None:
    """Per-market priority group, message type and channels (src/attraction.py)."""
    try:
        df = attraction.build()
    except Exception:  # noqa: BLE001
        log.exception("attraction map failed")
        return None
    rows = [{k: _clean(v) for k, v in r.items()} for r in df.to_dict("records")]
    return {"rows": rows, "typical": float(df["typical_rate"].iloc[0]), "min_headroom": attraction.MIN_HEADROOM}


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
           "destinations": list(trends.TOPICS)}   # English keys; the page shows them in the chosen language
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
        # monthly ranges calibrated on the method's own past errors (scorecard), when available
        cal = scorecard.current().get("TOTAL", {}).get("rows", [])
        cal_by = {r["target"]: r for r in cal if r.get("range") == "calibrated"}
        for f in overall.get("forecast", []):
            if f["m"] in cal_by:
                f["lo"], f["hi"] = cal_by[f["m"]]["lo"], cal_by[f["m"]]["hi"]
    except Exception:  # noqa: BLE001  the page must still build if the forecast fails
        log.exception("overall forecast failed")
        overall = None
    data = {"dates": dates, "series": series, "monthly": monthly, "overall": overall, "trends": trends_data(),
            "score": score_data(), "leisure": leisure_data(), "attraction": attraction_data(), "map": map_data(wide, proj, mon),
            "events": ev_list, "effects": ev_rows, "ev_summary": ev_summary,
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "first": dates[0], "last": dates[-1]}
    a2 = json.loads((VENDOR / "iso_numeric_alpha2.json").read_text(encoding="utf-8"))
    html = TEMPLATE.replace("__I18N__", json.dumps(as_json_dict(), ensure_ascii=False, separators=(",", ":"))) \
                   .replace("__A2__", json.dumps(a2, separators=(",", ":"))) \
                   .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
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
