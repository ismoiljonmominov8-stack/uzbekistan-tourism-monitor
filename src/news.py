"""News agent: read RSS feeds, keep tourism-related items, let the AI judge their impact,
log every judgement as a prediction (data/predictions.csv), and post or send for approval."""
import hashlib
import os
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import pandas as pd

from . import ai, config
from .texts import market_name, t
from .util import (admin_id, channel_id, esc, http_get, log, read_json, send_message, tg_call,
                   write_json)

SEEN = config.DATA / "news_seen.json"
PENDING = config.DATA / "pending.json"
OFFSET = config.DATA / "tg_offset.json"
PREDICTIONS = config.DATA / "predictions.csv"
PRED_COLS = ["date", "id", "status", "provider", "type", "event_date", "impact", "markets", "horizon", "confidence",
             "headline", "reason", "source", "url"]


def _clean(html_text: str, limit=500) -> str:
    text = re.sub(r"<[^>]+>", " ", html_text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def fetch_candidates() -> list[dict]:
    seen = set(read_json(SEEN, []))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    out = []
    for feed_url in config.NEWS_FEEDS:
        raw = http_get(feed_url, retries=2)
        if not raw:
            continue
        feed = feedparser.parse(raw)
        source = feed.feed.get("title", feed_url)
        for e in feed.entries:
            link = e.get("link", "")
            if not link:
                continue
            nid = hashlib.sha1(link.encode()).hexdigest()[:12]
            if nid in seen:
                continue
            published = e.get("published_parsed") or e.get("updated_parsed")
            if published and datetime(*published[:6], tzinfo=timezone.utc) < cutoff:
                continue
            title, snippet = _clean(e.get("title", ""), 200), _clean(e.get("summary", ""))
            hay = f"{title} {snippet}".lower()
            if not any(k in hay for k in config.NEWS_KEYWORDS):
                continue
            out.append({"id": nid, "title": title, "snippet": snippet, "source": source, "url": link})
    # de-duplicate near-identical headlines from different feeds
    uniq = {}
    for a in out:
        uniq.setdefault(re.sub(r"\W+", "", a["title"].lower())[:60], a)
    return list(uniq.values())[: config.NEWS_MAX_CANDIDATES]


def _valid_date(v) -> str:
    try:
        d = pd.Timestamp(str(v)).date()
        return d.isoformat() if 2000 <= d.year <= 2100 else ""
    except Exception:  # noqa: BLE001
        return ""


def format_item(item: dict, art: dict, provider: str | None) -> str:
    if not provider:
        return f"📰 <b>{esc(art['title'])}</b>\n{t('news_no_ai')}\n\n🔗 <a href=\"{esc(art['url'])}\">{esc(art['source'])}</a>"
    markets = ", ".join(item.get("markets") or []) or "—"
    return (
        f"📰 <b>{esc(item.get('headline') or art['title'])}</b>\n"
        f"{esc(item.get('summary', ''))}\n\n"
        f"{t('news_impact')}: {t('impact')[item['impact']]}\n"
        f"{t('news_market')}: {esc(markets)}\n"
        f"{t('news_when')}: {esc(item.get('horizon', '—'))}\n"
        f"{t('news_conf')}: {t('conf')[item['confidence']]}\n"
        f"{t('news_why')}: {esc(item.get('reason', ''))}\n\n"
        f"🔗 <a href=\"{esc(art['url'])}\">{esc(art['source'])}</a>"
    )


def _log_prediction(item, art, provider, status):
    row = {
        "date": datetime.now(timezone.utc).date().isoformat(), "id": art["id"], "status": status,
        "provider": provider or "none", "impact": item.get("impact", ""),
        "markets": "|".join(item.get("markets") or []), "horizon": item.get("horizon", ""),
        "confidence": item.get("confidence", ""), "headline": item.get("headline") or art["title"],
        "type": item.get("type", ""), "event_date": _valid_date(item.get("event_date")),
        "reason": item.get("reason", ""), "source": art["source"], "url": art["url"],
    }
    df = pd.read_csv(PREDICTIONS) if PREDICTIONS.exists() else pd.DataFrame(columns=PRED_COLS)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(PREDICTIONS, index=False)


def _set_status(nid, status):
    if not PREDICTIONS.exists():
        return
    df = pd.read_csv(PREDICTIONS)
    df.loc[df["id"] == nid, "status"] = status
    df.to_csv(PREDICTIONS, index=False)


def approval_on() -> bool:
    return bool(admin_id()) and os.getenv("NEWS_APPROVAL", "on").lower() != "off"


def run():
    """Fetch, analyse, log, and post (or send to the admin for approval)."""
    arts = fetch_candidates()
    seen = read_json(SEEN, [])
    seen += [a["id"] for a in arts]
    write_json(SEEN, seen[-3000:])
    if not arts:
        log.info("news: no new candidate articles")
        return 0

    items, provider = ai.analyze_news([{k: a[k] for k in ("id", "title", "snippet", "source")} for a in arts])
    by_id = {a["id"]: a for a in arts}
    if not provider:  # AI unavailable: fall back to plain headlines
        items = [{"id": a["id"]} for a in arts[: config.NEWS_PER_DAY]]
    log.info("news: %d candidates, %d selected (AI: %s)", len(arts), len(items), provider)

    pending = read_json(PENDING, {})
    for item in items:
        art = by_id[item["id"]]
        text = format_item(item, art, provider)
        if approval_on():
            send_message(admin_id(), f"{t('review')}\n\n{text}",
                         buttons=[[(t("approve"), f"ok:{art['id']}"), (t("reject"), f"no:{art['id']}")]])
            pending[art["id"]] = text
            _log_prediction(item, art, provider, "pending")
        else:
            send_message(channel_id(), text)
            _log_prediction(item, art, provider, "posted")
    write_json(PENDING, pending)
    return len(items)


def _register_event(nid):
    """An approved news item becomes an event whose effect the tracker will measure."""
    try:
        from . import events
        df = pd.read_csv(PREDICTIONS)
        row = df[df["id"] == nid].iloc[0]
        if str(row.get("impact", "")) == "unclear" and str(row.get("type", "other")) in ("other", "nan", ""):
            return
        # a future start date in the article makes this an UPCOMING event measured on that date
        when = str(row.get("event_date", "") or "")
        when = when if when and when != "nan" and when > str(row["date"]) else str(row["date"])
        eid = events.add_event(when, str(row.get("type", "other")),
                               str(row.get("markets", "")).split("|"), str(row["headline"]), str(row["url"]), "news")
        if eid and when > str(row["date"]):
            u = next((x for x in events.upcoming() if x["id"] == eid), None)
            if u:
                from . import botui
                send_message(admin_id(), botui.explain_upcoming(u, header="🗓 <b>Yangilikdan kutilayotgan voqea qo'shildi:</b>"))
        _alog(f"event registered: {eid} from news {nid}")
    except Exception as e:  # noqa: BLE001
        log.warning("could not register event for %s: %s", nid, e)


def _status(nid) -> str | None:
    if not PREDICTIONS.exists():
        return None
    df = pd.read_csv(PREDICTIONS)
    hit = df[df["id"] == nid]
    return None if hit.empty else str(hit["status"].iloc[0])


def _safe(method, payload):
    """Telegram calls that may fail harmlessly (e.g. answering a button press that is
    'too old'). They must never stop the approval loop."""
    try:
        tg_call(method, payload)
    except Exception as e:  # noqa: BLE001
        log.info("telegram %s ignored: %s", method, e)


def _handle(cq, pending):
    if str(cq["from"]["id"]) != str(admin_id()):
        _alog(f"press ignored: from a different user id (ends ...{str(cq['from']['id'])[-3:]}), "
              f"admin id ends ...{str(admin_id())[-3:]}")
        return
    action, _, nid = (cq.get("data") or "").partition(":")
    if action in ("ev", "evx"):
        from . import botui
        botui.handle_callback(cq, action, nid, _alog, _safe)
        return
    if nid.startswith("test"):
        label = "✅ Test OK" if action == "ok" else "❌ Test OK"
        _alog(f"TEST press received: {action}")
        _safe("answerCallbackQuery", {"callback_query_id": cq["id"], "text": label})
        msg = cq.get("message")
        if msg:
            _safe("editMessageReplyMarkup", {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                             "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": "x:x"}]]}})
        send_message(admin_id(), f"Test OK: button press received ({action}). Approvals work.")
        pending.pop(nid, None)
        write_json(PENDING, pending)
        return
    if action not in ("ok", "no"):
        _safe("answerCallbackQuery", {"callback_query_id": cq["id"]})
        return
    text = pending.pop(nid, None)
    status = _status(nid)
    if text is None or status in ("posted", "rejected"):
        _alog(f"press skipped: {action} {nid} (status={status}, in pending={text is not None})")
        # already handled (e.g. pressed twice): never post the same item again
        _safe("answerCallbackQuery", {"callback_query_id": cq["id"], "text": t("approved") if status == "posted" else "—"})
        return
    if action == "ok":
        send_message(channel_id(), text)
        _set_status(nid, "posted")
        _register_event(nid)
        label = t("approved")
    else:
        _set_status(nid, "rejected")
        label = t("rejected")
    write_json(PENDING, pending)  # save at once, so a later error cannot cause a repost
    _safe("answerCallbackQuery", {"callback_query_id": cq["id"], "text": label})
    msg = cq.get("message")
    if msg:
        _safe("editMessageReplyMarkup", {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                         "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": "x:x"}]]}})
    log.info("approval: %s %s", action, nid)
    _alog(f"press handled: {action} {nid}")


APPROVAL_LOG = config.DATA / "approvals_log.txt"


def _alog(msg: str):
    """Short diagnostic log kept in the repo (last 200 lines); never contains tokens."""
    lines = APPROVAL_LOG.read_text(encoding="utf-8").splitlines() if APPROVAL_LOG.exists() else []
    lines.append(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} {msg}")
    APPROVAL_LOG.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")


def format_upcoming(u: dict, added=False) -> str:
    est = u["estimate"]
    cw = t("conf_words")
    names = (t("all_markets") if u["markets"] == "all" else t("neighbours") if u["markets"] == "neighbours"
             else ", ".join(market_name(l) for l in u["markets"].split("|") if l in config.MARKETS))
    lines = [(t("up_added") if added else t("up_title")).format(title=esc(u["title"])),
             t("up_meta").format(date=u["date"], days=u["days"], type=t("types").get(u["type"], u["type"]), markets=esc(names))]
    i, a = est.get("info") or {}, est.get("arr") or {}
    lines.append(t("up_info").format(p=i["p"], k=i["k"], n=i["n"], conf=cw[i["conf"]]) if i.get("p") is not None
                 else t("up_nodata_info").format(n=i.get("n", 0)))
    lines.append(t("up_arr").format(p=a["p"], k=a["k"], n=a["n"], conf=cw[a["conf"]]) if a.get("p") is not None
                 else t("up_nodata_arr").format(n=a.get("n", 0)))
    x = est.get("expected") or {}
    if x.get("markets"):
        sign = lambda v: "±0" if v == 0 else f"{v:+,}".replace(",", "\u00a0").replace("-", "−")  # noqa: E731
        lines.append(t("up_expect_title").format(n=x["n"]))
        top = sorted(x["markets"].items(), key=lambda kv: -kv[1]["base_month"])[:5]
        for lang, m in top:
            lines.append(t("up_expect_row").format(flag=config.MARKETS[lang]["flag"], name=esc(market_name(lang)),
                                                   base=f"{m['base_month']:,}".replace(",", "\u00a0"),
                                                   mid=sign(m["mid"]), low=sign(m["low"]), high=sign(m["high"])))
        lines.append(t("up_expect_up") if x.get("q25", 0) > 1.05 else t("up_expect_flat") if x.get("q50", 1) < 1.1 else "")
    else:
        lines.append(t("up_expect_nodata").format(n=x.get("n", 0)))
    if u.get("source"):
        lines.append(f'🔗 <a href="{esc(u["source"])}">manba</a>')
    return "\n".join(l for l in lines if l)


def _handle_command(msg):
    """Messages from the admin in the bot chat (plain language, menu buttons, old commands)."""
    from . import botui
    botui.handle_message(msg, _alog)


def process_approvals(wait_minutes: float = 0):
    """Handle button presses. With wait_minutes > 0 it keeps listening (long polling) so
    presses are handled within seconds, e.g. right after the morning drafts are sent."""
    if not approval_on():
        return
    deadline = time.time() + wait_minutes * 60
    try:
        info = tg_call("getWebhookInfo", {}) or {}
        if info.get("url"):
            _alog("webhook is set on this bot -> deleting it so button presses can be read")
            tg_call("deleteWebhook", {"drop_pending_updates": False})
    except Exception as e:  # noqa: BLE001
        _alog(f"getWebhookInfo failed: {str(e)[:200]}")
    while True:
        offset = read_json(OFFSET, {"offset": 0})["offset"]
        pending = read_json(PENDING, {})
        poll = 0 if not wait_minutes else int(max(0, min(50, deadline - time.time())))
        try:
            updates = tg_call("getUpdates", {"offset": offset, "timeout": poll,
                                             "allowed_updates": ["callback_query", "message"]}) or []
            kinds = [k for u in updates for k in u if k != "update_id"]
            _alog(f"getUpdates offset={offset} pending={len(pending)} got={len(updates)} kinds={kinds}")
        except Exception as e:  # noqa: BLE001
            log.warning("getUpdates failed: %s", e)
            _alog(f"getUpdates FAILED: {str(e)[:200]}")
            updates = []
        for u in updates:
            try:
                if u.get("callback_query"):
                    _handle(u["callback_query"], pending)
                elif u.get("message"):
                    _handle_command(u["message"])
            except Exception:  # noqa: BLE001
                log.exception("approval update %s failed", u.get("update_id"))
            # confirm each update right away, so it is never processed twice
            write_json(OFFSET, {"offset": u["update_id"] + 1})
        if time.time() >= deadline and not updates:
            break  # the last call (with the new offset) also confirmed everything to Telegram
        if time.time() >= deadline + 120:
            break  # safety: never loop for long after the window


def approval_test(minutes: float = 10):
    """Send a test message with buttons to the admin and listen for presses."""
    try:
        me = tg_call("getMe", {}) or {}
        _alog(f"TEST start: bot @{me.get('username')} admin id ends ...{str(admin_id())[-3:]}")
    except Exception as e:  # noqa: BLE001
        _alog(f"TEST getMe failed: {str(e)[:200]}")
    pending = read_json(PENDING, {})
    pending["test1"] = "test"
    write_json(PENDING, pending)
    send_message(admin_id(), "🔧 Approval test: press ✅ or ❌ below within 10 minutes.",
                 buttons=[[("✅ Test", "ok:test1"), ("❌ Test", "no:test1")]])
    deadline = time.time() + minutes * 60
    while time.time() < deadline and "test1" in read_json(PENDING, {}):
        process_approvals(wait_minutes=min(1, (deadline - time.time()) / 60))
    if "test1" in read_json(PENDING, {}):
        _alog("TEST finished: NO press received in time")
        p = read_json(PENDING, {})
        p.pop("test1", None)
        write_json(PENDING, p)
