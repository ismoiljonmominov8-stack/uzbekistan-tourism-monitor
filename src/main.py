"""Entry point. Usage: python -m src.main <command>

  daily        collect pageviews + stat.uz + news, then post the daily index and news
  approvals    post news items you approved in the bot chat
  weekly       post the weekly chart
  test-models  compare Gemini and Groq on today's Uzbek news (prints only, posts nothing)
  collect      collect data only, post nothing
"""
import json
import sys

from . import ai, news, pageviews, posts, statuz
from .util import log


def step(name, fn, *a):
    """Run one step; a failure in one source must not stop the others."""
    try:
        return fn(*a)
    except Exception:  # noqa: BLE001
        log.exception("step %s failed", name)
        return None


def collect():
    step("pageviews", pageviews.collect)
    return step("stat.uz", statuz.collect) or []


def daily():
    releases = collect()
    step("daily post", posts.daily)
    step("monthly post", posts.monthly, releases)
    step("news", news.run)


def test_models():
    arts = news.fetch_candidates()[:5]
    if not arts:
        print("No tourism-related news in the last 48 hours; try again later.")
        return
    payload = [{k: a[k] for k in ("id", "title", "snippet", "source")} for a in arts]
    print("=== Articles ===")
    for a in arts:
        print(f"- [{a['source']}] {a['title']}\n  {a['url']}")
    for provider in ("gemini", "groq"):
        items, used = ai.analyze_news(payload, order=(provider,))
        print(f"\n=== {provider} ({'ok' if used else 'FAILED / no key'}) ===")
        print(json.dumps(items, ensure_ascii=False, indent=2))


COMMANDS = {
    "daily": daily,
    "approvals": lambda: step("approvals", news.process_approvals),
    "weekly": lambda: step("weekly", posts.weekly),
    "test-models": test_models,
    "collect": collect,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[cmd]()
