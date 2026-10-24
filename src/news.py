"""News agent: read RSS feeds, keep tourism-related items, let the AI judge their impact,
log every judgement as a prediction (data/predictions.csv), and post or send for approval."""
import hashlib
import os
import re
from datetime import datetime, timedelta, timezone

import feedparser
import pandas as pd

from . import ai, config
from .texts import t
from .util import (admin_id, channel_id, esc, http_get, log, read_json, send_message, tg_call,
                   write_json)

SEEN = config.DATA / "news_seen.json"
PENDING = config.DATA / "pending.json"
OFFSET = config.DATA / "tg_offset.json"
PREDICTIONS = config.DATA / "predictions.csv"
PRED_COLS = ["date", "id", "status", "provider", "impact", "markets", "horizon", "confidence",
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


def process_approvals():
    """Read button presses since the last run; post approved items to the channel."""
    if not approval_on():
        return
    offset = read_json(OFFSET, {"offset": 0})["offset"]
    updates = tg_call("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["callback_query"]}) or []
    pending = read_json(PENDING, {})
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        cq = u.get("callback_query")
        if not cq or str(cq["from"]["id"]) != str(admin_id()):
            continue
        action, _, nid = (cq.get("data") or "").partition(":")
        text = pending.pop(nid, None)
        msg = cq.get("message", {})
        if text is None:
            tg_call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "—"})
            continue
        if action == "ok":
            send_message(channel_id(), text)
            _set_status(nid, "posted")
            label = t("approved")
        else:
            _set_status(nid, "rejected")
            label = t("rejected")
        tg_call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": label})
        if msg:
            tg_call("editMessageReplyMarkup", {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                               "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": "x:x"}]]}})
        log.info("approval: %s %s", action, nid)
    write_json(OFFSET, {"offset": offset})
    write_json(PENDING, pending)
