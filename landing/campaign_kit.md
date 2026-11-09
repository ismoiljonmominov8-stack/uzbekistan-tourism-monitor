# Campaign test kit — U.S. travellers, version A vs version B

**Question being tested:** the attraction map says the U.S. is an *awareness* problem (people barely know
Uzbekistan), so **inspiration** content (A) should get more "Plan your trip" clicks than **practical**
content (B). If B wins, the barrier is practical (flights, cost, planning) and the map's rule is wrong for the U.S.

**Pages**
- A — inspiration: `https://ismoiljonmominov8-stack.github.io/uzbekistan-tourism-monitor/visit/a.html`
- B — practical: `https://ismoiljonmominov8-stack.github.io/uzbekistan-tourism-monitor/visit/b.html`
- Random 50/50 (for organic sharing): `…/visit/index.html`

Always add the source to the link, e.g. `a.html?utm_source=meta`, `b.html?utm_source=reddit`.
Known sources: meta, instagram, facebook, reddit, youtube, google, telegram, email, pinterest, tiktok, linkedin, x, qr,
partner, and partner labels `p-<name>` (e.g. `p-aua`). Ready-made links, partner messages, Pinterest pins and QR cards:
see `landing/outreach.md`.

---

## 1. Turn on counting (one time, about 5 minutes, in Cloudflare)

1. Cloudflare dashboard → **Storage & Databases → D1** → **Create database** → name `tourism_stats`.
2. **Workers & Pages → tourism-bot-clock → Settings → Bindings → Add → D1 database**
   → variable name **`DB`** → database `tourism_stats` → Save.
3. **Edit code** → replace everything with the new `cloudflare/worker.js` from GitHub → **Deploy**.
4. Open the worker's address in a browser. You should see **"✅ Campaign counting works"**.
5. Send the worker's address (it looks like `https://tourism-bot-clock.NAME.workers.dev`) in the chat.
   It is not secret. Claude puts it into `docs/visit/track.js` and runs the live check.

Only counts are stored: day, version, event, visitor country, traffic source. No IP addresses, no cookies.

---

## 2. Run the test fairly

- **Same budget, same audience, same dates** for A and B; only the content differs.
- **Paid (most reliable):** Meta Ads (Instagram + Facebook), two ads in one campaign
  - Location: United States · Age 25–65 · Interests: travel, history, cultural tourism, backpacking
  - Budget: about **$5 per ad per day for 14 days** (≈ $140 in total)
  - Ad 1 → `a.html?utm_source=meta`, Ad 2 → `b.html?utm_source=meta`
  - Paying with an Uzbek card may not work on Meta — check before planning around it.
- **Free:** Reddit (r/travel, r/solotravel, r/uzbekistan) and travel Facebook groups. Post as a useful guide,
  follow each community's self-promotion rules, and say it is a university research project.
- **Enough data:** each version needs at least **100 U.S. views** before the weekly report gives a verdict;
  300+ per version gives a much clearer answer.
- **Do not edit the pages during the test** — any change resets the comparison.

---

## 3. Posts — version A (inspiration) → link to `a.html`

The pages now carry free-licensed photos (credited at the bottom of each page). For posts, use your own photos or the
ready-made Pinterest pin images in `docs/visit/pins/` (a1–a5 for A, b1–b5 for B).

**A1 — Registan at dusk**
> Most Americans have never heard of Samarkand. It traded with China and Persia for 2,000 years — and the Registan
> looks like this every evening. Now visa-free for U.S. citizens. 👉 [link]

**A2 — Khiva's walls**
> A whole walled city of mud-brick and minarets, still lived in. Khiva, Uzbekistan — best from the city wall at
> sunset. 👉 [link]

**A3 — Plov**
> Cooked in cauldrons big enough to feed a wedding. If you travel for food, Uzbekistan's plov alone is worth the
> flight. 👉 [link]

**A4 — Shah-i-Zinda**
> A street of blue-tiled tombs in Samarkand, each one a different shade of turquoise. A UNESCO site most travel
> lists still miss. 👉 [link]

**A5 — Safety**
> "Is it safe?" The U.S. State Department rates Uzbekistan Level 1 — exercise normal precautions, its lowest
> level. The Silk Road is open. 👉 [link]

---

## 4. Posts — version B (practical) → link to `b.html`

**B1 — The whole trip in one line**
> Uzbekistan in 7 days: nonstop from New York, no visa for U.S. citizens, fast trains between Samarkand and
> Bukhara — about $1,650 all in. 👉 [link]

**B2 — Entry**
> Since January 2026, U.S. citizens can visit Uzbekistan visa-free for up to 30 days. Your hotel registers your
> stay. Here's the rest of what you need. 👉 [link]

**B3 — Flights**
> There is a nonstop flight from JFK to Tashkent (Uzbekistan Airways, Boeing 787) — or one stop via Istanbul or
> Dubai. The full 7-day plan: 👉 [link]

**B4 — Trains**
> Tashkent → Samarkand: 2 hours by fast train. Samarkand → Bukhara: 1.5 hours. Tickets open 30–45 days ahead on
> the national railway site. 7-day route here: 👉 [link]

**B5 — Budget**
> What does a week in Uzbekistan cost? Our estimate: ~$1,100 return flight from the East Coast + ~$80 a day on
> the ground. Route, trains and entry rules: 👉 [link]

All figures are the same ones shown and sourced on the pages (checked November 2026).

---

## 5. Reading the result

The Monday Word report gets a section **"Jalb etish sinovi"** with views, engaged readers and clicks for A and B,
for U.S. visitors and for everyone, plus the verdict:
- "Hali erta" (too early) until each version has 100 U.S. views;
- A wins / B wins only if the difference is statistically reliable (p < 0.05);
- otherwise "no reliable difference".

What it can and cannot show: the test measures **interest and intention** (clicks), not trips. A small campaign
will not change the official arrival numbers.
