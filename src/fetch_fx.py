"""Monthly exchange rates (som per unit) from the Central Bank of Uzbekistan archive, mid-month, 2021 onward.
Used to test whether currency moves help the arrivals forecast (src/signals_test.py). Output: data/fx_monthly.csv"""
from datetime import date

import pandas as pd

from . import config
from .util import http_get, log

OUT = config.DATA / "fx_monthly.csv"
CCY = ["RUB", "KZT", "KGS", "TJS", "CNY", "TRY", "INR", "USD", "EUR", "KRW"]
URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/{c}/{d}/"


def run(start="2021-01"):
    have = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["month", "ccy", "som_per_unit"])
    done = set(zip(have["month"], have["ccy"]))
    rows = []
    today = date.today()
    for p in pd.period_range(start, f"{today.year}-{today.month:02d}", freq="M"):
        d = date(p.year, p.month, 15)
        if d > today:
            continue
        for c in CCY:
            if (str(p), c) in done:
                continue
            data = http_get(URL.format(c=c, d=d.isoformat()), as_json=True)
            if not data:
                log.warning("fx: no data %s %s", c, d)
                continue
            x = data[0] if isinstance(data, list) else data
            rate = float(str(x["Rate"]).replace(",", ".")) / float(x.get("Nominal", 1) or 1)
            rows.append({"month": str(p), "ccy": c, "som_per_unit": rate})
    out = pd.concat([have, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["month", "ccy"], keep="last")
    out.sort_values(["ccy", "month"]).to_csv(OUT, index=False)
    log.info("fx: %d new rows, %d total", len(rows), len(out))


if __name__ == "__main__":
    run()
