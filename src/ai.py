"""AI layer: Gemini first, Groq as fallback. Both free tiers; either may fail, so callers must cope with None."""
import json
import os
import re

from . import config
from .util import http_post_json, log

LANG_NAME = {"uz": "Uzbek (Latin script)", "en": "English"}

PROMPT = """You are an analyst of inbound tourism to Uzbekistan.

Below are recent news articles (JSON). For each one decide whether it could change the number
of FOREIGN tourists coming to Uzbekistan (flights, visas, prices, exchange rates, events, safety,
infrastructure, UNESCO, marketing campaigns, regional conflicts...). Ignore domestic politics,
crime, sport results and anything without a plausible effect on foreign arrivals.

Pick at most {limit} relevant articles, most important first. For each return:
- "id": the article id
- "headline": a short headline in {lang}, written in your own words
- "summary": 1-2 sentences in {lang}, in your own words. Never copy sentences from the article.
- "impact": one of "positive", "negative", "mixed", "unclear" (effect on foreign arrivals)
- "markets": list of affected source countries in English (e.g. ["China"]) or ["All"]
- "horizon": one of "0-3 months", "3-6 months", "6-12 months", "12+ months"
- "confidence": "low" if only announced/planned or rumoured, "medium" if confirmed but not yet
  in effect, "high" if already in effect
- "reason": one sentence in {lang} explaining the expected mechanism

Do NOT give probabilities or percentages. Do not invent facts that are not in the article.
Return only JSON: {{"items": [ ... ]}}. If nothing is relevant return {{"items": []}}.

Articles:
{articles}
"""


def _extract_json(text: str):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


def _gemini(prompt: str) -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    data = http_post_json(
        url,
        {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}},
        headers={"x-goog-api-key": key},
    )
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt: str) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    data = http_post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"model": config.GROQ_MODEL, "temperature": 0.2,
         "response_format": {"type": "json_object"},
         "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {key}"},
    )
    return data["choices"][0]["message"]["content"]


PROVIDERS = {"gemini": _gemini, "groq": _groq}


def ask(prompt: str, order=("gemini", "groq")):
    """Try providers in order. Returns (parsed_json, provider_name) or (None, None)."""
    for name in order:
        try:
            raw = PROVIDERS[name](prompt)
            if raw is None:
                log.info("AI %s: no API key, skipped", name)
                continue
            return _extract_json(raw), name
        except Exception as e:  # noqa: BLE001
            log.warning("AI %s failed: %s", name, e)
    return None, None


def analyze_news(articles: list[dict], order=("gemini", "groq")):
    """articles: [{id, title, snippet, source}] -> (items, provider)"""
    prompt = PROMPT.format(
        limit=config.NEWS_PER_DAY,
        lang=LANG_NAME.get(config.POST_LANG, "English"),
        articles=json.dumps(articles, ensure_ascii=False, indent=1),
    )
    data, provider = ask(prompt, order)
    if not data:
        return [], None
    valid_ids = {a["id"] for a in articles}
    items = [i for i in data.get("items", []) if isinstance(i, dict) and i.get("id") in valid_ids]
    for i in items:
        if i.get("impact") not in ("positive", "negative", "mixed", "unclear"):
            i["impact"] = "unclear"
        if i.get("confidence") not in ("low", "medium", "high"):
            i["confidence"] = "low"
    return items[: config.NEWS_PER_DAY], provider
