"""Event tracker: did an announcement (visa, flight, event, sport...) change
(1) attention: Wikipedia views in the market's language over the next 7 days, and
(2) behaviour: tourist arrivals from that country, compared with arrivals overall?

Method (kept simple on purpose, so it can be explained in a dissertation):
- Wikipedia: mean views on days 0..6 after the announcement / median of days -35..-8 before.
- Arrivals, monthly: average monthly arrivals after the event month / before it, computed from
  stat.uz year-to-date figures, divided by the same ratio for ALL foreign arrivals. Dividing by
  the overall ratio removes seasons and general growth ("excess growth").
- Arrivals, yearly (fallback, and for old events): growth of the country's yearly arrivals in the
  first full year of the event / growth of total arrivals that year (SIAT open data).
Results are associations, not proof of cause: other things can change at the same time.
"""
import pandas as pd

from . import config, pageviews, statuz
from .util import log

EVENTS = config.DATA / "events.csv"
EFFECTS = config.DATA / "event_effects.csv"
EVENT_COLS = ["id", "date", "effective_date", "precision", "type", "markets", "title", "source", "origin"]
TYPES = ["visa", "flight", "event", "sport", "politics", "price", "infrastructure", "marketing", "other"]
COVID_YEARS = {2020, 2021, 2022, 2023}

# country name (as stat.uz / the AI writes it) -> Wikipedia language of that market
COUNTRY_LANG = {statuz._norm_country(n).lower(): lang
                for lang, info in config.MARKETS.items() for n in info["stat_names"] if lang != "ru"}
COUNTRY_LANG.update({"china": "zh", "korea": "ko", "south korea": "ko", "japan": "ja", "germany": "de",
                     "turkey": "tr", "türkiye": "tr", "italy": "it", "france": "fr", "india": "hi"})
DISTANT = [l for l, i in config.MARKETS.items() if i["stat_names"] and l != "ru"]


def lang_country(lang):
    names = config.MARKETS[lang]["stat_names"]
    return statuz._norm_country(names[0]) if names else None


def load_events() -> pd.DataFrame:
    if not EVENTS.exists():
        return pd.DataFrame(columns=EVENT_COLS)
    return pd.read_csv(EVENTS, dtype=str).fillna("")


def add_event(day: str, etype: str, markets: list[str], title: str, source: str, origin: str,
              effective: str | None = None) -> str | None:
    """Register an event. markets: country names or 'All'. Returns the id, or None if a duplicate."""
    df = load_events()
    if source and (df["source"] == source).any():
        return None
    langs = set()
    for m in markets or []:
        m = str(m).strip().lower()
        if m in ("all", "barcha", "*"):
            langs = {"all"}
            break
        if m in COUNTRY_LANG:
            langs.add(COUNTRY_LANG[m])
    if not langs:
        return None  # no market we can measure
    year = day[:4]
    n = int((df["id"].str.startswith(f"E{year}-")).sum()) + 1
    eid = f"E{year}-{n:02d}"
    row = {"id": eid, "date": day, "effective_date": effective or day, "precision": "day",
           "type": etype if etype in TYPES else "other", "markets": "|".join(sorted(langs)),
           "title": title, "source": source, "origin": origin}
    pd.concat([df, pd.DataFrame([row])], ignore_index=True)[EVENT_COLS].to_csv(EVENTS, index=False)
    log.info("event added: %s %s %s", eid, row["type"], title)
    return eid


# ---------------------------------------------------------------- measurements
def wiki_reaction(wide: pd.DataFrame, lang: str, day: pd.Timestamp) -> dict:
    if lang not in wide.columns:
        return {}
    s = wide[lang]
    base = s.loc[day - pd.Timedelta(days=35): day - pd.Timedelta(days=8)].dropna()
    win = s.loc[day: day + pd.Timedelta(days=6)].dropna()
    if len(base) < 14 or win.empty or base.median() <= 0:
        return {"wiki_status": "waiting" if win.empty else "no baseline"}
    return {"wiki_ratio": round(float(win.mean() / base.median()), 2),
            "wiki_peak": round(float(win.max() / base.median()), 2),
            "wiki_days": int(len(win)),
            "wiki_status": "ok" if len(win) == 7 else "partial"}


def _ytd_points(ytd: pd.DataFrame, country: str, year: int) -> dict:
    sub = ytd[(ytd["country"] == country) & (ytd["year"] == year)]
    pts = {0: (0, True)}
    for r in sub.itertuples():
        pts[int(r.month)] = (int(r.ytd), str(r.exact).lower() == "true")
    return pts


def _rate(pts: dict, lo: int, hi: int):
    """Average arrivals per month between year-to-date points lo and hi."""
    (a, ea), (b, eb) = pts[lo], pts[hi]
    return (b - a) / (hi - lo), ea and eb


def _window_ratio(ytd, country, year, lo_b, hi_b, lo_a, hi_a):
    """(after/before for country) / (after/before for TOTAL) for fixed month windows in one year."""
    pc, pt = _ytd_points(ytd, country, year), _ytd_points(ytd, "TOTAL", year)
    need = {lo_b, hi_b, lo_a, hi_a}
    if not need <= set(pc) or not need <= set(pt):
        return None
    cb, _ = _rate(pc, lo_b, hi_b); ca, _ = _rate(pc, lo_a, hi_a)
    tb, _ = _rate(pt, lo_b, hi_b); ta, _ = _rate(pt, lo_a, hi_a)
    if cb <= 0 or tb <= 0:
        return None
    return (ca / cb) / (ta / tb)


def monthly_effect(ytd: pd.DataFrame, country: str, eff: pd.Timestamp) -> dict:
    y, m0 = eff.year, eff.month
    if m0 <= 2:
        return {}
    pc, pt = _ytd_points(ytd, country, y), _ytd_points(ytd, "TOTAL", y)
    common = sorted(set(pc) & set(pt))
    before_hi = max([k for k in common if k <= m0 - 1], default=None)
    before_lo = max([k for k in common if before_hi is not None and k <= before_hi - 2], default=None)
    after_lo = min([k for k in common if k >= m0], default=None)
    after_hi = min([k for k in common if after_lo is not None and k >= after_lo + 2], default=None)
    if None in (before_hi, before_lo, after_lo, after_hi):
        return {"arr_status": "waiting"}
    cb, e1 = _rate(pc, before_lo, before_hi)
    ca, e2 = _rate(pc, after_lo, after_hi)
    tb, e3 = _rate(pt, before_lo, before_hi)
    ta, e4 = _rate(pt, after_lo, after_hi)
    if cb <= 0 or tb <= 0:
        return {"arr_status": "no data"}
    ratio, total_ratio = ca / cb, ta / tb
    raw_excess = ratio / total_ratio
    months = lambda a, b: f"{y}-{a + 1:02d}..{y}-{b:02d}"  # noqa: E731
    out = {"arr_method": "monthly", "arr_before": round(cb), "arr_after": round(ca),
           "arr_ratio": round(ratio, 2), "total_ratio": round(total_ratio, 2),
           "exact": e1 and e2 and e3 and e4,
           "arr_window": f"before {months(before_lo, before_hi)}, after {months(after_lo, after_hi)}",
           "arr_status": "ok"}
    # Seasons: the same months in another year (no event) show this country's normal seasonal
    # pattern relative to the overall flow. Divide it out; if no such year exists, say so.
    years = sorted(set(ytd["year"].astype(int)) - {y}, key=lambda yy: abs(yy - y))
    for yy in years:
        season = _window_ratio(ytd, country, yy, before_lo, before_hi, after_lo, after_hi)
        if season:
            out.update({"season_year": yy, "season_factor": round(season, 2),
                        "excess_raw": round(raw_excess, 2), "excess": round(raw_excess / season, 2)})
            out["arr_window"] += f"; season-adjusted with {yy}"
            break
    else:
        out.update({"excess_raw": round(raw_excess, 2), "excess": round(raw_excess, 2)})
        out["arr_window"] += " (season not controlled)"
    return out


def yearly_effect(yearly: pd.DataFrame, country: str, eff: pd.Timestamp) -> dict:
    y = effect_year(eff)  # first (mostly) full year with the event
    get = lambda c, yr: yearly[(yearly["country"] == c) & (yearly["year"] == yr)]["arrivals"]  # noqa: E731
    c1, c0, t1, t0 = get(country, y), get(country, y - 1), get("TOTAL", y), get("TOTAL", y - 1)
    if c1.empty or t1.empty:
        return {"arr_status": "waiting"}
    if c0.empty or int(c0.iloc[0]) == 0:
        return {"arr_status": "no data"}
    ratio = int(c1.iloc[0]) / int(c0.iloc[0])
    total_ratio = int(t1.iloc[0]) / int(t0.iloc[0])
    return {"arr_method": "yearly", "arr_before": int(c0.iloc[0]), "arr_after": int(c1.iloc[0]),
            "arr_ratio": round(ratio, 2), "total_ratio": round(total_ratio, 2),
            "excess": round(ratio / total_ratio, 2), "exact": True,
            "arr_window": f"{y - 1} vs {y}" + (" (COVID period: unreliable)" if y in COVID_YEARS else ""),
            "arr_status": "ok"}


def verdicts(r: dict) -> dict:
    w = r.get("wiki_ratio")
    r["wiki_verdict"] = ("—" if w is None else "strong" if (w >= 1.5 or r.get("wiki_peak", 0) >= 3)
                         else "some" if w >= 1.2 else "none")
    e = r.get("excess")
    r["arr_verdict"] = ("—" if e is None else "rose more than overall" if e >= 1.2
                        else "fell vs overall" if e <= 0.83 else "no clear change")
    if r.get("overlap") and e is not None:
        r["arr_verdict"] += " (mixed with other events)"
    if "COVID" in str(r.get("arr_window", "")) and e is not None:
        r["arr_verdict"] += " (COVID period)"
    if "season not controlled" in str(r.get("arr_window", "")) and e is not None:
        r["arr_verdict"] += " (season not controlled)"
    return r


def effect_year(ts: pd.Timestamp) -> int:
    return ts.year if ts.month <= 6 else ts.year + 1


def overlaps(events: pd.DataFrame, ev, lang: str, method) -> str:
    """Other events for the same market whose effect falls in the same measurement window, so the
    effects cannot be separated: within 95 days (monthly) or the same measured year (yearly)."""
    if not method:
        return ""
    eff = pd.Timestamp(ev.effective_date or ev.date)
    out = []
    for o in events.itertuples():
        if o.id == ev.id:
            continue
        o_langs = DISTANT if o.markets == "all" else o.markets.split("|")
        if lang not in o_langs:
            continue
        o_eff = pd.Timestamp(o.effective_date or o.date)
        same = abs(o_eff - eff) <= pd.Timedelta(days=95) if method == "monthly" else effect_year(o_eff) == effect_year(eff)
        if same:
            out.append(o.id)
    return " ".join(out)


def measure() -> pd.DataFrame:
    events = load_events()
    if events.empty:
        return pd.DataFrame()
    wide = pageviews.market_daily(pageviews.load())
    ytd, yearly = statuz.load(), statuz.load_yearly()
    old = pd.read_csv(EFFECTS) if EFFECTS.exists() else pd.DataFrame(columns=["id", "lang", "reported"])
    reported = {(r.id, r.lang): bool(r.reported) for r in old.itertuples()} if "reported" in old else {}
    rows = []
    for ev in events.itertuples():
        langs = DISTANT if ev.markets == "all" else [l for l in ev.markets.split("|") if l in config.MARKETS]
        day = pd.Timestamp(ev.date)
        eff = pd.Timestamp(ev.effective_date or ev.date)
        for lang in langs:
            r = {"id": ev.id, "date": ev.date, "type": ev.type, "lang": lang, "title": ev.title}
            r.update(wiki_reaction(wide, lang, day) if ev.precision == "day" else {"wiki_status": "date not exact"})
            country = lang_country(lang)
            arr = monthly_effect(ytd, country, eff) if country else {}
            if arr.get("arr_status") != "ok" and country:
                arr = yearly_effect(yearly, country, eff)
            r.update(arr)
            r["overlap"] = overlaps(events, ev, lang, r.get("arr_method"))
            r["reported"] = reported.get((ev.id, lang), False)
            rows.append(verdicts(r))
    out = pd.DataFrame(rows)
    out.to_csv(EFFECTS, index=False)
    return out


def summary_by_type(eff: pd.DataFrame) -> pd.DataFrame:
    """Per event type: how often Wikipedia reacted and how often arrivals rose more than overall."""
    if eff.empty:
        return pd.DataFrame()
    d = eff.copy()
    clean = ~d["arr_verdict"].astype(str).str.contains(r"\(", regex=True)
    d.loc[~clean, "excess"] = None   # mixed or COVID results are shown but not counted
    g = d.groupby("type")
    return pd.DataFrame({
        "events": g["id"].nunique(),
        "measured_wiki": g["wiki_ratio"].count() if "wiki_ratio" in d else 0,
        "wiki_reacted": g["wiki_verdict"].apply(lambda s: int(s.isin(["some", "strong"]).sum())),
        "measured_arrivals": g["excess"].count() if "excess" in d else 0,
        "arrivals_rose": g["arr_verdict"].apply(lambda s: int((s == "rose more than overall").sum())),
        "median_excess": g["excess"].median().round(2) if "excess" in d else None,
    }).reset_index()


def new_results(eff: pd.DataFrame) -> pd.DataFrame:
    """Rows whose arrivals result is now measurable and has not been posted yet."""
    if eff.empty or "excess" not in eff:
        return pd.DataFrame()
    return eff[eff["excess"].notna() & ~eff["reported"].astype(bool)]


def mark_reported(ids_langs):
    eff = pd.read_csv(EFFECTS)
    for eid, lang in ids_langs:
        eff.loc[(eff["id"] == eid) & (eff["lang"] == lang), "reported"] = True
    eff.to_csv(EFFECTS, index=False)



# ---------------------------------------------------------------- upcoming events: possibilities
TYPE_ALIASES = {"viza": "visa", "reys": "flight", "parvoz": "flight", "tadbir": "event", "festival": "event",
                "konferensiya": "event", "forum": "event", "ko'rgazma": "event", "sport": "sport",
                "siyosat": "politics", "narx": "price", "infratuzilma": "infrastructure", "marketing": "marketing",
                "reklama": "marketing", "boshqa": "other"}
PRIOR_STRENGTH = 2.0
MIN_CASES = 3   # fewer comparable past cases than this: say "not enough data" instead of a number


def _rate_with_prior(k: int, n: int, prior: float) -> float:
    """Share of past successes, pulled toward the overall rate when there are few cases."""
    return (k + PRIOR_STRENGTH * prior) / (n + PRIOR_STRENGTH)


def _confidence(n: int) -> str:
    return "low" if n < 5 else "medium" if n < 30 else "high"


def estimate(etype: str, langs: list[str], eff: pd.DataFrame | None = None) -> dict:
    """Possibility that (1) people look up Uzbekistan more (Wikipedia x1.2+ within 7 days) and
    (2) arrivals from the market rise more than overall (x1.2+), from PAST measured events.
    Unit = event x market. Mixed / COVID / season-uncontrolled arrival results are not used."""
    eff = (pd.read_csv(EFFECTS) if EFFECTS.exists() else pd.DataFrame()) if eff is None else eff
    out = {"type": etype}
    if eff.empty:
        return out | {"info_p": None, "arr_p": None}
    verdict = eff.get("arr_verdict", pd.Series(dtype=str)).astype(str)
    clean_arr = eff[eff["excess"].notna() & ~verdict.str.contains(r"\(", regex=True)] if "excess" in eff else eff.iloc[0:0]
    wiki = eff[eff["wiki_ratio"].notna()] if "wiki_ratio" in eff else eff.iloc[0:0]

    def part(rows, success, size_col):
        # overall rate across all types, itself pulled toward 50 % (Laplace), as the prior
        prior = (int(success(rows).sum()) + 1) / (len(rows) + 2)
        typed = rows[rows["type"] == etype]
        mk = typed[typed["lang"].isin(langs)] if langs else typed.iloc[0:0]
        k, n = int(success(typed).sum()), len(typed)
        return {"p": round(_rate_with_prior(k, n, prior), 2) if n >= MIN_CASES else None,
                "k": k, "n": n, "conf": _confidence(n),
                "prior": round(prior, 2), "size": (round(float(typed[size_col].median()), 2) if n else None),
                "market_k": int(success(mk).sum()), "market_n": len(mk)}

    info = part(wiki, lambda d: d["wiki_ratio"] >= 1.2, "wiki_ratio")
    arr = part(clean_arr, lambda d: d["excess"] >= 1.2, "excess")
    return out | {"info_p": info["p"], "info": info, "arr_p": arr["p"], "arr": arr,
                  "expected": expected_numbers(etype, langs, clean_arr, wiki)}


def expected_numbers(etype: str, langs: list[str], clean_arr: pd.DataFrame, wiki: pd.DataFrame) -> dict:
    """What similar past events did, turned into numbers for each market of an upcoming event:
    the middle half (25th-75th percentile) and median of the 'excess' of past events of this type,
    applied to the market's current monthly arrivals (latest full year / 12). Needs >= MIN_CASES."""
    typed = clean_arr[clean_arr["type"] == etype]
    wtyped = wiki[wiki["type"] == etype]
    res = {"n": len(typed), "wiki_median": round(float(wtyped["wiki_ratio"].median()), 2) if len(wtyped) else None,
           "markets": {}}
    if len(typed) < MIN_CASES:
        return res
    q25, q50, q75 = (float(typed["excess"].quantile(q)) for q in (0.25, 0.5, 0.75))
    res.update({"q25": round(q25, 2), "q50": round(q50, 2), "q75": round(q75, 2)})
    yearly, mon = statuz.load_yearly(), statuz.monthly()
    last = int(yearly["year"].max()) if not yearly.empty else None
    for lang in langs:
        country = lang_country(lang)
        base, basis = None, ""
        # prefer the latest 3 official months (current level); else last full year / 12
        m = mon[(mon["country"] == country)].sort_values(["year", "month"]) if not mon.empty else mon
        if len(m) >= 3:
            recent = m.tail(3)
            base = float(recent["arrivals"].mean())
            basis = f"{int(recent.iloc[0].year)}-{int(recent.iloc[0].month):02d}..{int(recent.iloc[-1].year)}-{int(recent.iloc[-1].month):02d}"
        elif last is not None:
            row = yearly[(yearly["country"] == country) & (yearly["year"] == last)]
            if not row.empty:
                base, basis = int(row["arrivals"].iloc[0]) / 12, f"{last} / 12"
        if not base:
            continue
        res["markets"][lang] = {"base_month": round(base), "basis": basis,
                                "low": round(base * (q25 - 1)), "mid": round(base * (q50 - 1)),
                                "high": round(base * (q75 - 1))}
    return res


def upcoming(today: pd.Timestamp | None = None) -> list[dict]:
    today = (today or pd.Timestamp.now(tz="UTC").tz_localize(None)).normalize()
    ev = load_events()
    if ev.empty:
        return []
    eff = pd.read_csv(EFFECTS) if EFFECTS.exists() else pd.DataFrame()
    out = []
    for e in ev.itertuples():
        d = pd.Timestamp(e.date)
        if d < today:
            continue
        langs = DISTANT if e.markets == "all" else e.markets.split("|")
        out.append({"id": e.id, "date": e.date, "days": int((d - today).days), "type": e.type,
                    "markets": e.markets, "title": e.title, "source": e.source,
                    "estimate": estimate(e.type, langs, eff)})
    return sorted(out, key=lambda x: x["date"])


def parse_event_command(text: str):
    """'/event 2026-11-20 | festival | China, Korea | Title | https://link' -> dict or error string."""
    body = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""
    parts = [p.strip() for p in body.split("|")]
    if len(parts) < 4:
        return "format"
    day, etype, markets, title = parts[:4]
    source = parts[4] if len(parts) > 4 else ""
    try:
        day = pd.Timestamp(day).date().isoformat()
    except Exception:  # noqa: BLE001
        return "date"
    etype = TYPE_ALIASES.get(etype.lower(), etype.lower())
    if etype not in TYPES:
        etype = "other"
    return {"date": day, "type": etype, "markets": [m.strip() for m in markets.split(",") if m.strip()],
            "title": title, "source": source}
