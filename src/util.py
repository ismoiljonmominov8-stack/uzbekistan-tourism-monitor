"""Shared helpers: HTTP, files, Telegram."""
import html
import json
import logging
import os
import time
from pathlib import Path

import requests

from . import config

log = logging.getLogger("monitor")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("matplotlib").setLevel(logging.WARNING)

_session = requests.Session()
_session.headers["User-Agent"] = config.USER_AGENT


def http_get(url, *, params=None, timeout=30, retries=3, as_json=False):
    """GET with simple retry/backoff. Returns text/JSON, or None if it keeps failing."""
    for attempt in range(1, retries + 1):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json() if as_json else r.text
        except Exception as e:  # noqa: BLE001 - network code: never crash the whole run
            log.warning("GET %s failed (%s/%s): %s", url, attempt, retries, e)
            time.sleep(2 * attempt)
    return None


def http_post_json(url, payload, *, headers=None, timeout=60):
    r = _session.post(url, json=payload, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- files
def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- Telegram
def dry_run() -> bool:
    return os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes") or not os.getenv("TELEGRAM_BOT_TOKEN")


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def _tg(method, payload=None, files=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        r = _session.post(url, data=payload, files=files, timeout=60)
    else:
        r = _session.post(url, json=payload, timeout=60)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
    return data["result"]


def send_message(chat_id, text, *, buttons=None, keyboard=None):
    """Send an HTML message. buttons = [[(label, callback_data), ...], ...] (inline, under the message);
    keyboard = [[label, ...], ...] (menu buttons that stay above the typing field)."""
    if dry_run() or not chat_id:
        print(f"\n----- [DRY RUN] message to {chat_id or '(no chat)'} -----\n{text}\n")
        if buttons:
            print("buttons:", buttons)
        if keyboard:
            print("keyboard:", keyboard)
        return None
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in buttons]
        }
    elif keyboard:
        payload["reply_markup"] = {"keyboard": [[{"text": t} for t in row] for row in keyboard],
                                   "resize_keyboard": True, "is_persistent": True}
    return _tg("sendMessage", payload)


def send_photo(chat_id, photo_path: Path, caption=""):
    if dry_run() or not chat_id:
        print(f"\n----- [DRY RUN] photo {photo_path} to {chat_id or '(no chat)'} -----\n{caption}\n")
        return None
    with open(photo_path, "rb") as f:
        return _tg("sendPhoto", {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}, files={"photo": f})


def tg_call(method, payload):
    if dry_run():
        return None
    return _tg(method, payload)


def channel_id():
    return os.getenv("TELEGRAM_CHANNEL_ID", "")


def admin_id():
    return os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
