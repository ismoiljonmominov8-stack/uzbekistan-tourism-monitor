# Uzbekistan Tourism Monitor

A free, automated pipeline that tracks **online interest in Uzbekistan** from key tourist markets,
collects **official inbound-tourism statistics**, reads **tourism-related news**, and posts the
analysis to a Telegram channel. It is built as a data source for the master's dissertation
*"O'zbekistonda raqamli texnologiyalar va sun'iy intellekt yordamida turistlarni jalb etish hamda tartibga solish"*
(Tashkent State Agrarian University).

Everything runs on GitHub Actions and costs nothing.

## What it does

| When (Tashkent time) | What | Data file |
|---|---|---|
| Every day 09:47 | Downloads yesterday's Wikipedia pageviews of *Uzbekistan, Samarkand, Bukhara, Khiva, Tashkent* in 9 languages | `data/pageviews_daily.csv` |
| Every day 09:47 | Checks stat.uz for new monthly tourist-arrival press releases and parses them | `data/arrivals_ytd.csv` |
| Every day ~09:50 | Posts the **interest index**: each market vs its 30-day average | — |
| Every day ~09:50 | Reads news feeds, AI picks up to 3 relevant items and rates their impact | `data/predictions.csv` |
| Every hour | Posts the news items you approved | — |
| Mondays 10:23 | Posts a 12-week trend chart | — |
| When stat.uz publishes | Posts official arrivals for distant markets next to their Wikipedia interest | — |

### Why distant markets

About two-thirds of foreign arrivals are visits to relatives from neighbouring Central Asian
countries. Online interest says little about those trips, so the analysis focuses on China,
Korea, Japan, Germany, Türkiye, Italy and France, where each Wikipedia language maps cleanly to
one country. English (global) and Russian (CIS) are tracked for context only.

### The prediction log

Every news judgement (impact ▲/▼/◆/?, market, horizon, confidence) is saved with its date in
`data/predictions.csv`. Months later it can be compared with the official arrivals to see which
kinds of news actually moved tourism. The AI is told **not** to give probabilities: a percentage
read from one article would be false precision.

## Event tracker

Does an announcement change (1) attention and (2) actual arrivals? Every event in
`data/events.csv` is measured automatically, results in `data/event_effects.csv`, the chart page
("Voqealar ta'siri") and a Telegram post when a result first becomes measurable.

- **Wikipedia reaction:** mean views on days 0–6 after the announcement ÷ median of days −35…−8.
  "strong" ≥ ×1.5 (or a peak day ≥ ×3), "some" ≥ ×1.2.
- **Arrivals ("farq" / excess):** arrivals from the country after vs before, divided by the same
  ratio for all foreign arrivals (removes general growth). Monthly results are also divided by the
  same months of another year (removes the country's own seasons); without such a year the result
  is marked *season not controlled* and is not counted. Old events use yearly data (SIAT dataset
  1031): growth in the first full year ÷ growth of total arrivals. ≥ ×1.2 = rose more than overall.
- Events for the same market within 3 months (monthly) or 12 months (yearly) are marked *mixed*;
  results from 2020–2023 are marked *COVID period*. Neither is counted in the summary by type.
- These are associations, not proof of cause.

**Adding events:** news you approve in the bot are added automatically. To add one by hand, edit
`data/events.csv` on GitHub (Add a row: `id,date,effective_date,precision,type,markets,title,source,origin`;
markets are language codes `zh|ko|ja|de|tr|it|fr` or `all`; precision `day` or `month`; origin `manual`).

## Setup (about 15 minutes)

### 1. Telegram
1. In Telegram, open **@BotFather** → `/newbot` → copy the **bot token**.
2. Create a **new channel** for this project and add the bot as **administrator** (allow posting).
3. Channel ID: for a public channel use `@channelname`. For a private channel, forward a channel
   post to **@userinfobot**, which shows an ID like `-100…`.
4. Your own chat ID (for approving news): send any message to **@userinfobot** and copy your ID.
   Then open your new bot and press **Start**, otherwise it cannot message you.

### 2. AI keys
- **Gemini:** https://aistudio.google.com/apikey → *Create API key*
- **Groq:** https://console.groq.com/keys → *Create API Key*

### 3. Add the secrets to GitHub
Repository → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | bot token from BotFather |
| `TELEGRAM_CHANNEL_ID` | `@channelname` or `-100…` |
| `TELEGRAM_ADMIN_CHAT_ID` | your own chat ID (news comes to you for approval first) |
| `GEMINI_API_KEY` | Gemini key |
| `GROQ_API_KEY` | Groq key |

Optional, under the **Variables** tab:

| Name | Values | Default |
|---|---|---|
| `POST_LANG` | `uz` or `en` | `uz` |
| `NEWS_APPROVAL` | `on` or `off` (off = news goes straight to the channel) | `on` |

Never paste these keys into code, issues or chats.

### 4. First run
1. **Actions** tab → *Test AI models (Gemini vs Groq)* → **Run workflow**. Open the log and compare
   how each model understood today's news. If one is clearly better, keep it first (see below).
2. **Actions** → *Daily collect & post* → **Run workflow**. The first run downloads all history
   since 2016 and may take a few minutes.

## Changing things
- Markets, articles, feeds, keywords, thresholds: `src/config.py`
- Post wording (Uzbek / English): `src/texts.py`
- Model order: `analyze_news(..., order=("gemini", "groq"))` in `src/news.py`; model names via the
  `GEMINI_MODEL` / `GROQ_MODEL` environment variables

## Known limitations
- stat.uz publishes monthly figures only as press-release text. If they change the wording, the
  parser may miss a release; check the Actions log for `stat.uz: could not parse`.
- Releases sometimes contain typos (e.g. "43,572,000" for 43,572). A country value larger than the
  total is divided by 1000 and flagged in the `note` column.
- Monthly figures for a country are derived from two consecutive top-10 lists; when a country drops
  out of the top 10 that month shows "—".
- Free AI tiers change limits without notice. If both models fail, the bot posts plain headlines.
- GitHub pauses scheduled workflows in public repos after 60 days without commits. The daily data
  commit keeps the repository active.

## Data sources and licences
- Wikimedia Pageviews API (CC0) — https://wikimedia.org/api/rest_v1/
- National Statistics Committee of the Republic of Uzbekistan — https://stat.uz
- News: RSS feeds of kun.uz, gazeta.uz, UzDaily and Google News (headlines and links only)
