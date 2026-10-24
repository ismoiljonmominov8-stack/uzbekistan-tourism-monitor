"""Analyst agent: turns the collected data into daily, weekly and monthly Telegram posts."""
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config, pageviews, statuz  # noqa: E402
from .texts import market_name, month_name, t  # noqa: E402
from .util import admin_id, channel_id, esc, log, read_json, send_message, send_photo, write_json  # noqa: E402

STATE = config.DATA / "post_state.json"


def _fmt_change(c: float) -> str:
    arrow = "▲" if c >= 0.05 else "▼" if c <= -0.05 else "•"
    return f"{c:+.0%} {arrow}"


def single_article_spike(df: pd.DataFrame, lang: str, day) -> str | None:
    """If one article explains >80 % of a market's jump, the spike may be automated traffic
    or a single viral link rather than real travel interest. Returns that article or None."""
    d = df[df["lang"] == lang].copy()
    d["date"] = pd.to_datetime(d["date"])
    today = d[d["date"] == day].set_index("article")["views"]
    base = d[(d["date"] < day) & (d["date"] >= day - pd.Timedelta(days=config.BASELINE_DAYS))]
    avg = base.groupby("article")["views"].mean()
    diff = (today - avg).dropna()
    total = diff.sum()
    if total <= 0 or diff.empty:
        return None
    top = diff.idxmax()
    return top if diff[top] / total > 0.8 else None


def daily(force=False):
    state = read_json(STATE, {})
    df = pageviews.load()
    wide = pageviews.market_daily(df)
    if wide.empty:
        log.info("daily: no data yet")
        return
    day = wide.index.max()
    if day.date() < date.today() - timedelta(days=2):
        log.info("daily: newest data is %s, not posting stale numbers", day.date())
        return
    if state.get("daily") == str(day.date()) and not force:
        log.info("daily: already posted for %s", day.date())
        return

    ds = day.strftime("%d.%m.%Y")
    mv = pageviews.movers(wide, day)
    if not mv:
        log.info("daily: not enough history for a baseline yet")
        return
    if max(abs(m["change"]) for m in mv) < 0.10:
        send_message(channel_id(), t("quiet").format(date=ds))
    else:
        lines = [f"<b>{t('daily_title').format(date=ds)}</b>", "", t("movers")]
        for m in mv[: config.TOP_MOVERS]:
            flag = config.MARKETS[m["lang"]]["flag"]
            lines.append(f"{flag} {esc(market_name(m['lang']))}  <b>{_fmt_change(m['change'])}</b>  ({m['views']:,})")
        top = pageviews.most_viewed_article(df, day)
        if top:
            lines += ["", t("most_viewed").format(article=top)]
        up, n = pageviews.trend_7d(wide)
        if n:
            lines.append(t("trend").format(up=up, n=n))
        spikes = [m for m in mv if abs(m["change"]) >= config.SPIKE_THRESHOLD]
        if spikes:
            names = ", ".join(f"{market_name(m['lang'])} {m['change']:+.0%}" for m in spikes)
            lines += ["", t("spike").format(markets=esc(names))]
            for m in spikes:
                art = single_article_spike(df, m["lang"], day)
                if art:
                    lines.append(t("bot_warning").format(market=esc(market_name(m["lang"])), article=esc(art)))
        lines += ["", f"<i>{t('footnote')}</i>"]
        send_message(channel_id(), "\n".join(lines))
    state["daily"] = str(day.date())
    write_json(STATE, state)


def weekly():
    wide = pageviews.market_daily(pageviews.load())
    if len(wide) < 7 * 13:
        log.info("weekly: not enough data")
        return
    # complete weeks only (Mon-Sun)
    weeks = wide.resample("W-SUN").sum()
    last_full = weeks.index[-1] if wide.index.max().weekday() == 6 else weeks.index[-2]
    weeks = weeks.loc[:last_full].iloc[-12:]
    index = weeks / weeks.iloc[0] * 100

    config.CHARTS.mkdir(exist_ok=True)
    path = config.CHARTS / "weekly.png"
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    for lang in index.columns:
        style = "--" if config.MARKETS[lang]["flag"] == "🌐" else "-"
        ax.plot(index.index, index[lang], style, linewidth=2, label=config.MARKETS[lang]["en"])
    ax.axhline(100, color="#999", linewidth=0.8)
    ax.set_title(t("weekly_caption"), fontsize=11)
    ax.legend(ncol=3, fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)

    change = weeks.iloc[-1] / weeks.iloc[-2] - 1
    start = (last_full - pd.Timedelta(days=6)).strftime("%d.%m")
    lines = [f"<b>{t('weekly_title').format(start=start, end=last_full.strftime('%d.%m.%Y'))}</b>", ""]
    for lang in change.sort_values(ascending=False).index:
        lines.append(t("weekly_line").format(flag=config.MARKETS[lang]["flag"], name=esc(market_name(lang)),
                                             change=change[lang]))
    send_photo(channel_id(), path, "\n".join(lines))


def monthly(releases: list[dict]):
    """Post each newly published stat.uz release, compared with Wikipedia interest."""
    if not releases:
        return
    mon = statuz.monthly()
    wide = pageviews.market_daily(pageviews.load())
    for rel in releases:
        y, m = rel["year"], rel["month"]
        period = f"{month_name(1)}–{month_name(m)} {y}" if m > 1 else f"{month_name(1)} {y}"
        lines = [f"<b>{t('monthly_title').format(period=period)}</b>", "",
                 t("monthly_total").format(total=rel["total"])]
        this = mon[(mon["year"] == y) & (mon["month"] == m)]
        tot = this[this["country"] == "TOTAL"]
        if len(tot):
            lines.append(t("monthly_month").format(n=int(tot["arrivals"].iloc[0])))
        month_views = pd.Series(dtype=float)
        if not wide.empty:
            sel = wide[(wide.index.year == y) & (wide.index.month == m)]
            month_views = sel.sum()
        rows = []
        for lang, info in config.MARKETS.items():
            if not info["stat_names"] or lang == "ru":
                continue
            names = {statuz._norm_country(n) for n in info["stat_names"]}
            hit = this[this["country"].isin(names)]
            arrivals = f"{int(hit['arrivals'].iloc[0]):,}" if len(hit) else "—"
            v = month_views.get(lang, 0)
            views = f"{int(v):,}" if v and not pd.isna(v) else "—"
            rows.append(t("monthly_row").format(flag=info["flag"], name=esc(market_name(lang)),
                                                arrivals=arrivals, views=views))
        if rows:
            lines += ["", t("monthly_markets")] + rows
        for note in rel.get("notes", []):
            if "typo" in note:
                lines.append(t("monthly_note").format(note=esc(note)))
        lines += ["", f"<i>{t('monthly_src')}</i> — <a href=\"{esc(rel['url'])}\">stat.uz</a>"]
        if rel.get("problems"):
            # failed a sanity check: show it to the admin only, never the channel
            head = [t("check_failed")] + [f"• {esc(p)}" for p in rel["problems"]] + [""]
            send_message(admin_id() or None, "\n".join(head + lines))
        else:
            send_message(channel_id(), "\n".join(lines))
