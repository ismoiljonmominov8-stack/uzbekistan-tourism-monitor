"""Entry point. Usage: python -m src.main <command>

  daily        collect pageviews + stat.uz + news, then post the daily index and news
  approvals    post news items you approved in the bot chat
  weekly       post the weekly chart
  test-models  compare Gemini and Groq on today's Uzbek news (prints only, posts nothing)
  collect      collect data only, post nothing
"""
import json
import os
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
    # stay online for a while so morning approvals are handled within seconds
    step("approvals", news.process_approvals, float(os.getenv("APPROVAL_WAIT_MINUTES", "30")))


def test_models():
    arts = news.fetch_candidates()[:5]
    if not arts:
        print("No tourism-related news in the last 48 hours; try again later.")
        return
    payload = [{k: a[k] for k in ("id", "title", "snippet", "source")} for a in arts]
    print("=== Articles ===")
    for a in arts:
        print(f"- [{a['source']}] {a['title']}\n  {a['url']}")
    # 1) comprehension: every article must be summarised, so we can judge how well
    #    each model understands Uzbek/Russian text even when nothing is relevant.
    comp_prompt = (
        "For EACH article below write, in Uzbek (Latin script), a one-sentence summary in your own "
        "words and a verdict: could it change the number of foreign tourists coming to Uzbekistan "
        "(yes/no) and why, in one short sentence. Return only JSON: "
        '{"items": [{"id": "...", "summary": "...", "affects_foreign_tourists": "yes|no", "why": "..."}]}\n\n'
        + json.dumps(payload, ensure_ascii=False, indent=1)
    )
    for provider in ("gemini", "groq"):
        data, used = ai.ask(comp_prompt, order=(provider,))
        print(f"\n=== {provider}: comprehension ({'ok' if used else 'FAILED / no key'}) ===")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    # 2) the real production prompt
    for provider in ("gemini", "groq"):
        items, used = ai.analyze_news(payload, order=(provider,))
        print(f"\n=== {provider}: production prompt ({'ok' if used else 'FAILED / no key'}) ===")
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
