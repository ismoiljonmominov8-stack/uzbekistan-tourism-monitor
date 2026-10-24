"""Central settings. Edit this file to change markets, articles, feeds or thresholds."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

USER_AGENT = (
    "uzbekistan-tourism-monitor/1.0 "
    "(https://github.com/ismoiljonmominov8-stack/uzbekistan-tourism-monitor; research project)"
)

# ---------------------------------------------------------------- Wikipedia
# English article titles; titles in other languages are looked up automatically.
ARTICLES_EN = ["Uzbekistan", "Samarkand", "Bukhara", "Khiva", "Tashkent"]

# Wikipedia language -> market it stands for. Distant markets first: they are the
# ones online interest can actually say something about (see README).
MARKETS = {
    "zh": {"flag": "🇨🇳", "en": "China", "uz": "Xitoy", "stat_names": ["China"]},
    "ko": {"flag": "🇰🇷", "en": "Korea", "uz": "Koreya", "stat_names": ["Republic of Korea", "Korea", "South Korea"]},
    "ja": {"flag": "🇯🇵", "en": "Japan", "uz": "Yaponiya", "stat_names": ["Japan"]},
    "de": {"flag": "🇩🇪", "en": "Germany", "uz": "Germaniya", "stat_names": ["Germany"]},
    "tr": {"flag": "🇹🇷", "en": "Türkiye", "uz": "Turkiya", "stat_names": ["Turkey", "Türkiye", "Turkiye"]},
    "it": {"flag": "🇮🇹", "en": "Italy", "uz": "Italiya", "stat_names": ["Italy"]},
    "fr": {"flag": "🇫🇷", "en": "France", "uz": "Fransiya", "stat_names": ["France"]},
    "hi": {"flag": "🇮🇳", "en": "India", "uz": "Hindiston", "stat_names": ["India"]},
    "en": {"flag": "🌐", "en": "English (global)", "uz": "Ingliz tili (global)", "stat_names": []},
    "ru": {"flag": "🌐", "en": "Russian (CIS)", "uz": "Rus tili (MDH)", "stat_names": ["Russia"]},
}

PAGEVIEWS_START = "2016-01-01"  # backfill start on first run
BASELINE_DAYS = 30               # compare yesterday with the previous 30-day average
SPIKE_THRESHOLD = 0.30           # (unused) spikes are now flagged statistically, see pageviews.movers
TOP_MOVERS = 5                   # markets shown in the daily post
CHART_URL = os.getenv("CHART_URL", "https://ismoiljonmominov8-stack.github.io/uzbekistan-tourism-monitor/")

# ---------------------------------------------------------------- stat.uz
STATUZ_LIST_URL = "https://stat.uz/en/press-center/news-of-committee"
STATUZ_PAGE_SIZE = 18            # items per listing page (?start=18, 36, ...)
STATUZ_LIST_PAGES = 3            # pages scanned on a normal day (~1 week of news)
STATUZ_BACKFILL_PAGES = 150      # pages scanned on the first run (~1 year of news)

# ---------------------------------------------------------------- News
NEWS_FEEDS = [
    "https://kun.uz/news/rss",
    "https://kun.uz/en/news/rss",
    "https://www.gazeta.uz/ru/rss/",
    "https://www.gazeta.uz/oz/rss/",
    "https://www.uzdaily.uz/en/rss",
    "https://news.google.com/rss/search?q=Uzbekistan+tourism&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Uzbekistan+flights+OR+visa&hl=en-US&gl=US&ceid=US:en",
]
NEWS_KEYWORDS = [
    # en
    "touris", "travel", "flight", "airline", "airport", "visa", "hotel", "unesco", "samarkand",
    "bukhara", "khiva", "railway", "high-speed",
    # uz (latin)
    "turizm", "turist", "sayyoh", "parvoz", "aviakompaniya", "aeroport", "viza", "mehmonxona",
    "samarqand", "buxoro", "xiva",
    # ru
    "туриз", "турист", "рейс", "авиакомпан", "аэропорт", "виз", "гостиниц", "отел", "самарканд", "бухар", "хив",
]
NEWS_PER_DAY = 3                 # max news items analysed and posted per day
NEWS_MAX_CANDIDATES = 12         # max articles sent to the AI per run

# ---------------------------------------------------------------- AI
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")  # llama-3.3-70b was retired Aug 2026

# ---------------------------------------------------------------- Telegram
POST_LANG = os.getenv("POST_LANG", "uz")  # "uz" or "en"
TIMEZONE = "Asia/Tashkent"
