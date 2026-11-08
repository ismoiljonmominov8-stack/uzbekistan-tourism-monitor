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

from . import ai, history, news, pageviews, posts, scorecard, statuz
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
    step("wikipedia totals", pageviews.collect_projects)
    step("yearly arrivals by country", statuz.collect_yearly)
    return step("stat.uz", statuz.collect) or []


def tashkent_now():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone.utc) + timedelta(hours=5)


def catch_up_daily() -> bool:
    """Wikimedia sometimes publishes yesterday's page views hours late. Then the 09:47 run finds nothing new and
    skips the index post. Later runs (backup schedules, approvals) call this: if yesterday's index was not posted,
    fetch again (at most every 50 minutes) and post when the data is there. Returns True if it posted."""
    from datetime import datetime, timedelta, timezone
    from .util import read_json, write_json
    now = datetime.now(timezone.utc)
    expected = (now.date() - timedelta(days=1)).isoformat()      # Wikipedia days are UTC days
    state = read_json(posts.STATE, {})
    if state.get("daily", "") >= expected:
        return False
    last = state.get("catchup_at")
    if last and now - datetime.fromisoformat(last) < timedelta(minutes=50):
        return False
    state["catchup_at"] = now.isoformat(timespec="seconds")
    write_json(posts.STATE, state)
    step("pageviews", pageviews.collect)
    step("wikipedia totals", pageviews.collect_projects)
    newest = str(pageviews.load()["date"].max())[:10]
    if newest < expected:
        log.info("catch-up: Wikipedia data for %s still not published (newest %s)", expected, newest)
        return False
    log.info("catch-up: data for %s arrived late -> posting the daily index now", expected)
    step("history chart", history.build)
    step("daily post", posts.daily)
    return True


def daily():
    """Runs at most once per Tashkent day (several schedules + catch-up may call it)."""
    from .util import read_json, write_json
    state = read_json(posts.STATE, {})
    today = tashkent_now().date().isoformat()
    if state.get("run_date") == today:
        log.info("daily: already ran today (%s); only handling approvals", today)
        step("daily post catch-up", catch_up_daily)
        step("approvals", news.process_approvals, 2)
        return
    state["run_date"] = today
    write_json(posts.STATE, state)
    releases = collect()
    step("event tracker", posts.event_results)
    step("forecast scorecard", scorecard.run)   # logs this month's forecasts, scores past ones
    step("history chart", history.build)
    step("daily post", posts.daily)
    step("monthly post", posts.monthly, releases)
    step("news", news.run)
    # stay online for a while so morning approvals are handled within seconds
    step("approvals", news.process_approvals, float(os.getenv("APPROVAL_WAIT_MINUTES", "30")))


def events_measure():
    from . import events
    return events.measure()


def approvals():
    """Handle button presses and messages; if an event was added, refresh effects and the page.
    Also a safety net: if the morning run was skipped by GitHub, do it now."""
    from . import events
    from .util import read_json
    now = tashkent_now()
    if now.hour * 60 + now.minute >= 9 * 60 + 40 and read_json(posts.STATE, {}).get("run_date") != now.date().isoformat():
        log.info("approvals: morning run missing today -> running it now")
        os.environ["APPROVAL_WAIT_MINUTES"] = "3"
        daily()
        return
    before = events.EVENTS.stat().st_mtime if events.EVENTS.exists() else 0
    if now.hour * 60 + now.minute >= 10 * 60:           # after the morning run had its chance
        step("daily post catch-up", catch_up_daily)
    step("approvals", news.process_approvals)
    if events.EVENTS.exists() and events.EVENTS.stat().st_mtime != before:
        step("event tracker", posts.event_results)
        step("history chart", history.build)


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
    "approvals": lambda: approvals(),
    "weekly": lambda: step("weekly", posts.weekly),
    "test-models": test_models,
    "approval-test": lambda: news.approval_test(10),
    "history": lambda: step("history chart", history.build),
    "scorecard": lambda: step("forecast scorecard", scorecard.run),
    "events": lambda: (step("event tracker", posts.event_results), step("history chart", history.build)),
    "post-daily-now": lambda: (collect(), step("history chart", history.build),
                               step("daily post", posts.daily, True)),
    "collect": collect,
    # stat.uz is skipped on purpose: a release found here would be marked seen but never posted
    "refresh": lambda: (step("pageviews", pageviews.collect), step("wikipedia totals", pageviews.collect_projects),
                        step("yearly arrivals by country", statuz.collect_yearly),
                        step("event effects", events_measure), step("history chart", history.build)),
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[cmd]()
