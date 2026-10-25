"""How many adults in each source country can afford a 5-day trip to Uzbekistan?

Model (deliberately simple, every assumption visible):
  trip cost  = round-trip fare (or land transport) + 5 days in Uzbekistan + visa
               standard: average fare + $80/day (mid-range guesthouse, meals, trains, sights)
               budget:   cheap fare   + $45/day (hostel/private room, local food)
  "affordable" = trip cost <= one month of that person's spending (1/12 of annual consumption);
               sensitivity: half a month (strict) and two months (loose)
  spending   = household final consumption per person (World Bank, current US$), spread across
               people as a lognormal distribution with the country's Gini index
  result     = adults (15+) x share of people whose yearly spending >= 12 x trip cost

Known biases: consumption per person includes children and imputed rent (mean too high for cash);
a lognormal tail is thinner than real top incomes (undercounts the rich in poor countries). The
result is an order of magnitude, and it measures ABILITY, not wish to travel.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import pandas as pd

from . import config

N = NormalDist()
DAYS = 5
DAY_STANDARD, DAY_BUDGET, DAY_LOCAL = 80, 45, 25   # local: neighbours staying with relatives / cheap guesthouse
NEIGHBOURS = {"KAZ", "KGZ", "TJK", "TKM", "AFG"}
SHARE = {"strict": 1 / 24, "central": 1 / 12, "loose": 1 / 6}

# iso3: (name_uz, fare_avg, fare_cheap, visa, transport note, siat_name)
MARKETS = {
    "KAZ": ("Qozog'iston", 60, 30, 0, "quruqlik (avtobus/taksi)", "Kazakhstan"),
    "KGZ": ("Qirg'iziston", 60, 30, 0, "quruqlik", "Kyrgyzstan"),
    "TJK": ("Tojikiston", 60, 30, 0, "quruqlik", "Tajikistan"),
    "TKM": ("Turkmaniston", 60, 30, 0, "quruqlik", "Turkmenistan"),
    "AFG": ("Afg'oniston", 60, 30, 60, "quruqlik (Termiz), viza", "Afghanistan"),
    "RUS": ("Rossiya", 330, 250, 0, "aviareys Moskva", "Russia"),
    "CHN": ("Xitoy", 448, 391, 0, "aviareys Pekin", "China"),
    "TUR": ("Turkiya", 403, 323, 0, "aviareys Istanbul", "Türkiye"),
    "KOR": ("Janubiy Koreya", 561, 470, 0, "aviareys Seul", "Republic of Korea"),
    "IND": ("Hindiston", 367, 283, 0, "aviareys Dehli", "India"),
    "DEU": ("Germaniya", 665, 462, 0, "aviareys Frankfurt", "Germany"),
    "JPN": ("Yaponiya", 880, 624, 0, "aviareys Tokio", "Japan"),
    "ITA": ("Italiya", 888, 532, 0, "aviareys Rim", "Italy"),
    "FRA": ("Fransiya", 778, 627, 0, "aviareys Parij", "France"),
    "GBR": ("Buyuk Britaniya", 842, 692, 0, "aviareys London", "United Kingdom"),
    "USA": ("AQSh", 1100, 795, 0, "aviareys Nyu-York/Vashington", "United States"),
}
# gaps in World Bank data, filled with labelled guesses
FALLBACK_GINI = {"AFG": 30.0, "TKM": 40.0}
FALLBACK_CONS_PC = {"TKM": 0.35 * 6540}   # GDP per person x assumed consumption share (official FX overstates GDP)


def share_above(threshold: float, mean: float, gini: float) -> float:
    sigma = math.sqrt(2) * N.inv_cdf((gini / 100 + 1) / 2)
    mu = math.log(mean) - sigma ** 2 / 2
    return 1 - N.cdf((math.log(threshold) - mu) / sigma)


WID_CODE = {"KAZ": "KZ", "KGZ": "KG", "TJK": "TJ", "TKM": "TM", "AFG": "AF", "RUS": "RU", "CHN": "CN", "TUR": "TR",
            "KOR": "KR", "IND": "IN", "DEU": "DE", "JPN": "JP", "ITA": "IT", "FRA": "FR", "GBR": "GB", "USA": "US"}


def wid_shape() -> dict[str, list[tuple[float, float]]]:
    """{iso3: [(percentile, income threshold / mean income), ...]} from WID (pre-tax income, adults)."""
    path = config.DATA / "wid.csv"
    if not path.exists():
        return {}
    w = pd.read_csv(path)
    out = {}
    for iso, cc in WID_CODE.items():
        g = w[w.country == cc]
        mean = g[(g.variable == "aptincj992") & (g.percentile == "p0p100")]["value"]
        thr = g[g.variable == "tptincj992"]
        if mean.empty or thr.empty:
            continue
        pts = {}
        for pc, v in zip(thr.percentile, thr.value):
            lo = float(pc[1:].split("p")[0])
            pts[lo] = v / float(mean.iloc[0])
        out[iso] = sorted(pts.items())
    return out


def share_above_shape(threshold: float, level: float, shape: list[tuple[float, float]]) -> float:
    """Share of adults whose income (shape x level) is at or above the threshold (linear interpolation)."""
    rel = threshold / level
    prev = None
    for pc, r in shape:
        if r >= rel:
            if prev is None:
                return 1.0
            (p0, r0) = prev
            frac = (rel - r0) / (r - r0) if r > r0 else 0
            return max(0.0, 1 - (p0 + frac * (pc - p0)) / 100)
        prev = (pc, r)
    return 0.0


def load_wb() -> pd.DataFrame:
    d = pd.read_csv(config.DATA / "worldbank.csv")
    latest = d.sort_values("year").groupby(["country", "indicator"]).tail(1)
    p = latest.pivot(index="country", columns="indicator", values="value")
    yrs = latest.pivot(index="country", columns="indicator", values="year")
    dep19 = d[(d.indicator == "ST.INT.DPRT") & (d.year == 2019)].set_index("country")["value"]
    return p, yrs, dep19


ISO_NUM = {"KAZ": 398, "KGZ": 417, "TJK": 762, "TKM": 795, "AFG": 4, "RUS": 643, "CHN": 156, "TUR": 792, "KOR": 410,
           "IND": 356, "DEU": 276, "JPN": 392, "ITA": 380, "FRA": 250, "GBR": 826, "USA": 840}


def arrivals_2025() -> dict[str, int]:
    y = pd.read_csv(config.DATA / "arrivals_yearly_by_country.csv", dtype={"code": str})
    y = y[(y.year == y.year.max()) & y.code.notna()]
    by_num = {int(float(c)): int(a) for c, a in zip(y.code, y.arrivals)}
    return {iso: by_num.get(n) for iso, n in ISO_NUM.items()}, int(y.year.max())


def run() -> pd.DataFrame:
    p, yrs, dep19 = load_wb()
    arr, arr_year = arrivals_2025()
    shapes = wid_shape()
    rows = []
    for iso, (name, fare_avg, fare_cheap, visa, note, siat) in MARKETS.items():
        pop = p.at[iso, "SP.POP.TOTL"]
        adults = pop - p.at[iso, "SP.POP.0014.TO"]
        guessed = []
        if iso in FALLBACK_CONS_PC:
            cons, guessed = FALLBACK_CONS_PC[iso], guessed + ["iste'mol"]
        else:
            cons = p.at[iso, "NE.CON.PRVT.CD"] / p.at[iso, "SP.POP.TOTL"]
        gini = p.at[iso, "SI.POV.GINI"] if not pd.isna(p.at[iso, "SI.POV.GINI"]) else None
        if gini is None:
            gini, guessed = FALLBACK_GINI[iso], guessed + ["Gini"]
        cost_std = fare_avg + DAY_STANDARD * DAYS + visa
        cost_bud = fare_cheap + DAY_BUDGET * DAYS + visa
        r = {"iso": iso, "name": name, "transport": note, "adults": adults, "cons_pc": cons, "gini": gini,
             "cost_standard": cost_std, "cost_budget": cost_bud, "guessed": ", ".join(guessed),
             "cost_months_of_avg": cost_std / (cons / 12),
             "arrivals": arr.get(iso), "arrivals_year": arr_year,
             "departures_2019": dep19.get(iso)}
        if iso in shapes:   # WID income shape (keeps the rich tail), level = consumption per adult
            level = cons * pop / adults
            f = lambda t: share_above_shape(t, level, shapes[iso])  # noqa: E731
            r["method"] = "WID"
        else:               # fallback: lognormal from the Gini index
            f = lambda t: share_above(t, cons, gini)  # noqa: E731
            r["method"] = "lognormal"
        for k, s in SHARE.items():
            r[f"afford_std_{k}"] = adults * f(cost_std / s)
        r["afford_bud_central"] = adults * f(cost_bud / SHARE["central"])
        r["lognormal_central"] = adults * share_above(cost_std / SHARE["central"], cons, gini)
        if iso in NEIGHBOURS:
            r["cost_local"] = fare_cheap + DAY_LOCAL * DAYS + visa
            r["afford_local_central"] = adults * f(r["cost_local"] / SHARE["central"])
        r["share_std_central"] = r["afford_std_central"] / adults
        r["visits_per_1000_affordable"] = (r["arrivals"] / r["afford_std_central"] * 1000
                                           if r["arrivals"] and r["afford_std_central"] > 0 else None)
        rows.append(r)
    return pd.DataFrame(rows).sort_values("afford_std_central", ascending=False)


if __name__ == "__main__":
    df = run()
    pd.set_option("display.width", 250)
    show = df[["name", "method", "cons_pc", "gini", "cost_standard", "cost_months_of_avg", "share_std_central", "lognormal_central",
               "afford_std_strict", "afford_std_central", "afford_std_loose", "afford_bud_central",
               "arrivals", "visits_per_1000_affordable", "departures_2019", "guessed"]].copy()
    for c in ["afford_std_strict", "afford_std_central", "afford_std_loose", "afford_bud_central", "departures_2019", "lognormal_central"]:
        show[c] = (show[c] / 1e6).round(2)
    print(show.round(3).to_string(index=False))
    out = config.DATA / "affordability.csv"
    df.to_csv(out, index=False)
