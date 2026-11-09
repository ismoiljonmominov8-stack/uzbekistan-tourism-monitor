"""Campaign test pages for U.S. travellers: docs/visit/a.html (inspiration) and docs/visit/b.html (practical),
plus docs/visit/index.html which splits organic visitors 50/50.

Both versions use exactly the same facts and blocks; only the headline and the ORDER differ:
  A "Inspiration": discover first (cities, food, safety), practical details after.
  B "Practical":   how to get there, cost and entry rules first, cities after.
That is the hypothesis from the attraction map: the U.S. is an awareness problem, so A should win.

Counting: the page tells the Cloudflare worker (POST /hit) about a view, an engaged reader (half the page or
30 s) and clicks on the three buttons. Only counts are kept (day, version, event, country, source).
The worker address is in docs/visit/track.js (window.TRACK_URL); empty = counting off, the page still works.
Facts checked 9 Nov 2026 (sources listed on the page and in FACT_SOURCES).
"""
from __future__ import annotations

import json

from . import config

OUT = config.ROOT / "docs" / "visit"
MAP = config.ROOT / "landing" / "uzmap.json"
TRACK_JS = OUT / "track.js"

FACT_SOURCES = [
    ("Visa-free entry for U.S. citizens, 30 days, from 1 January 2026 (Kun.uz)",
     "https://kun.uz/en/news/2025/12/24/uzbekistan-introduces-30-day-visa-free-entry-for-us-citizens-from-january-1"),
    ("U.S. State Department travel advisory: Level 1, exercise normal precautions (26 January 2026)",
     "https://travel.state.gov/en/international-travel/travel-advisories/uzbekistan.html"),
    ("Uzbekistan Airways nonstop New York JFK – Tashkent, Boeing 787 (AeroRoutes)", "https://www.aeroroutes.com/eng/260428-hymay26jfk"),
    ("Train times and booking (Journal of Nomads guide)", "https://www.journalofnomads.com/trains-in-uzbekistan-railways/"),
]
LINKS = {
    "plan": "https://uzbekistan.travel/en/",
    "rules": "https://travel.state.gov/content/travel/en/international-travel/International-Travel-Country-Information-Pages/Uzbekistan.html",
    "route": "https://e-ticket.railway.uz/",
}

# Photos: free-licensed, from Wikimedia Commons (src/fetch_photos.py). The same photos sit in the same places on A and B.
# key -> (candidate file, alt text, width, height, vertical focus 0..1)
PHOTOS = {
    "hero": ("registan_1.jpg", "The Registan in Samarkand lit up at night", 1600, 720, 0.55),
    "samarkand": ("shahizinda_5.jpg", "Blue-tiled mausoleums of Shah-i-Zinda, Samarkand", 800, 600, 0.5),
    "bukhara": ("bukhara_1.jpg", "The Kalyan minaret above a street in Bukhara", 800, 600, 0.3),
    "khiva": ("khiva_0.jpg", "Mud-brick walls and turquoise towers of Itchan Kala, Khiva", 800, 600, 0.5),
    "tashkent": ("chorsu_5.jpg", "Hand-painted ceramic plates at Chorsu bazaar, Tashkent", 800, 600, 0.5),
    "food": ("plov_3.jpg", "Plov being served at a restaurant", 800, 600, 0.5),
    "safety": ("registan_3.jpg", "A woman walking past a tiled wall of the Registan", 800, 600, 0.6),
    "hospitality": ("plov_2.jpg", "Guests gathered around a plov cauldron at a celebration", 800, 600, 0.5),
    "train": ("train_2.jpg", "Afrosiyob fast train at Tashkent station", 1200, 600, 0.55),
}
PHOTO_DIR = config.ROOT / "landing" / "photos"
IMG_OUT = OUT / "img"


def prepare_photos() -> None:
    """Crop and compress the chosen candidates into docs/visit/img and write landing/photos/credits.json.
    Needs landing/photos/raw (fetched on GitHub); the results are committed, so later builds do not."""
    from PIL import Image
    meta = json.loads((PHOTO_DIR / "raw" / "meta.json").read_text(encoding="utf-8"))
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    for key, (src, alt, w, h, fy) in PHOTOS.items():
        im = Image.open(PHOTO_DIR / "raw" / src).convert("RGB")
        scale = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        x0 = (im.width - w) // 2
        y0 = min(max(round(im.height * fy - h / 2), 0), im.height - h)
        im.crop((x0, y0, x0 + w, y0 + h)).save(IMG_OUT / f"{key}.jpg", quality=78, optimize=True, progressive=True)
        m = meta[src]
        credits[key] = {"alt": alt, "w": w, "h": h, "title": m["title"].removeprefix("File:"), "page": m["page"],
                        "author": m["author"], "license": m["license"], "license_url": m["license_url"]}
    (PHOTO_DIR / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")


def _img(key: str, cls: str = "", lazy: bool = True) -> str:
    c = json.loads((PHOTO_DIR / "credits.json").read_text(encoding="utf-8"))[key]
    return (f'<img src="img/{key}.jpg" alt="{c["alt"]}" width="{c["w"]}" height="{c["h"]}"'
            f'{" class=" + chr(34) + cls + chr(34) if cls else ""}{" loading=" + chr(34) + "lazy" + chr(34) if lazy else ""}>')


def _photo_credits() -> str:
    c = json.loads((PHOTO_DIR / "credits.json").read_text(encoding="utf-8"))
    lic = lambda x: (f'<a href="{x["license_url"]}" target="_blank" rel="noopener">{x["license"]}</a>'  # noqa: E731
                     if x["license_url"] else x["license"])
    return "".join(f'<li><a href="{x["page"]}" target="_blank" rel="noopener">{x["alt"]}</a> — {x["author"]}, {lic(x)}</li>'
                   for x in c.values())


BLOCKS = {
    "cities": """
<section class="block" id="cities">
  <h2>Four cities, one Silk Road</h2>
  <div class="cards">
    <article>__IMG_samarkand__<h3>Samarkand</h3><p>The Registan square and the blue-tiled street of tombs at Shah-i-Zinda. A UNESCO World Heritage city that traded with China and Persia for two thousand years.</p></article>
    <article>__IMG_bukhara__<h3>Bukhara</h3><p>A walkable old town of domed bazaars, madrasas and the 12th-century Kalyan minaret. Its historic centre is a UNESCO World Heritage site.</p></article>
    <article>__IMG_khiva__<h3>Khiva</h3><p>Itchan Kala, a complete walled inner city of mud-brick walls and minarets — best at sunset from the city wall.</p></article>
    <article>__IMG_tashkent__<h3>Tashkent</h3><p>The modern capital: wide avenues, the Chorsu bazaar and metro stations decorated like palaces. Your arrival point.</p></article>
  </div>
</section>""",
    "why": """
<section class="block" id="why">
  <h2>Why travellers come back</h2>
  <div class="cards three">
    <article>__IMG_food__<h3>Food</h3><p>Plov cooked in huge cauldrons, fresh bread from clay ovens, melons in summer. Eating out is part of the trip, not a cost line.</p></article>
    <article>__IMG_safety__<h3>Safety</h3><p>The U.S. State Department rates Uzbekistan <b>Level 1 — exercise normal precautions</b>, the lowest of its four levels (January 2026).</p></article>
    <article>__IMG_hospitality__<h3>Hospitality</h3><p>Small family guesthouses in the old towns, tea offered by strangers, and very few crowds outside the main squares.</p></article>
  </div>
</section>""",
    "practical": """
<section class="block" id="practical">
  <h2>What you need to know</h2>
  <div class="facts">
    <div><b>Entry</b><span>U.S. citizens can visit <b>visa-free for up to 30 days</b> (since 1 January 2026). Your hotel registers your stay. Always check the latest rules before you fly.</span></div>
    <div><b>Getting there</b><span><b>Nonstop from New York (JFK)</b> to Tashkent with Uzbekistan Airways (Boeing 787), or one stop via Istanbul or Dubai.</span></div>
    <div><b>Getting around</b><span>Fast trains: Tashkent → Samarkand about <b>2 hours</b>, Samarkand → Bukhara about <b>1.5 hours</b>, Bukhara → Khiva about 6 hours. Tickets on the national railway website open 30–45 days ahead.</span></div>
    <div><b>Budget (our estimate)</b><span>Round-trip flight from the U.S. East Coast around <b>$1,100</b> plus about <b>$80 a day</b> on the ground (mid-range) — roughly <b>$1,650 for 7 days</b>. Prices vary by season; check current fares.</span></div>
  </div>
  <p class="cta-row">
    <a class="btn" data-track="cta_rules" href="__RULES__" target="_blank" rel="noopener">Entry rules (U.S. State Department)</a>
    <a class="btn ghost" data-track="cta_route" href="__ROUTE__" target="_blank" rel="noopener">Train tickets (national railway)</a>
  </p>
</section>""",
    "route": """
<section class="block" id="route">
  <h2>A 7-day route</h2>
  <div class="route">
    <svg viewBox="0 0 __W__ __H__" role="img" aria-label="Map of Uzbekistan with the route Tashkent – Samarkand – Bukhara – Khiva">
      __NEAR__
      <path class="uz" d="__UZ__"/>
      <polyline class="line" points="__LINE__"/>
      __DOTS__
    </svg>
    <ol>
      <li><b>Days 1–2 · Tashkent</b> — arrive, bazaar, metro, old town.</li>
      <li><b>Days 3–4 · Samarkand</b> — fast train; Registan, Shah-i-Zinda, Gur-e-Amir.</li>
      <li><b>Days 5–6 · Bukhara</b> — old town on foot, bazaars, evening by the Lyab-i-Hauz pond.</li>
      <li><b>Day 7 · Khiva</b> — the walled city at sunset; fly back via Urgench or Tashkent.</li>
    </ol>
  </div>
  <figure class="wide">__IMG_train__<figcaption>The Afrosiyob fast train: Tashkent – Samarkand in about two hours.</figcaption></figure>
</section>""",
}

HEROES = {
    "a": ("A Silk Road city most Americans have never heard of",
          "Turquoise domes, two-thousand-year-old trading towns and food you will remember. "
          "Uzbekistan — now visa-free for U.S. citizens and safe by the State Department's own rating.",
          ["cities", "why", "route", "practical"]),
    "b": ("Uzbekistan in 7 days: how to get there, what it costs, what you need",
          "Nonstop from New York, visa-free for U.S. citizens since January 2026, fast trains between the Silk Road cities — "
          "and a full week for about $1,650.",
          ["practical", "route", "cities", "why"]),
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — Uzbekistan</title>
<meta name="description" content="__SUB__">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__SUB__">
<meta property="og:image" content="https://ismoiljonmominov8-stack.github.io/uzbekistan-tourism-monitor/visit/img/hero.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--paper:#f3ead7;--paper2:#ebdfc4;--card:#f8f1e1;--ink:#2b2117;--muted:#6b5a45;--rule:#b9a27c;--rust:#8c3b22;--blue:#2f5d7c;--green:#3d6b45}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.6 "EB Garamond",Georgia,serif;
  background-image:radial-gradient(circle at 15% 0%,rgba(140,59,34,.07),transparent 45%),radial-gradient(circle at 90% 100%,rgba(47,93,124,.06),transparent 45%)}
.wrap{max-width:980px;margin:0 auto;padding:0 16px 48px}
header.hero{padding:56px 0 34px;border-bottom:3px double var(--rule);margin-bottom:28px}
.kicker{font-size:14px;letter-spacing:.18em;text-transform:uppercase;color:var(--rust);margin:0 0 10px}
h1{font:700 clamp(34px,6vw,58px)/1.05 "Cormorant Garamond",serif;margin:0 0 16px;max-width:820px}
.sub{font-size:21px;max-width:760px;margin:0 0 24px;color:#3d3022}
h2{font:700 34px/1.15 "Cormorant Garamond",serif;margin:0 0 14px}
h3{font:600 24px/1.2 "Cormorant Garamond",serif;margin:0 0 6px;color:var(--rust)}
.block{margin:0 0 34px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));gap:14px}
.cards.three{grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}
.cards article,.facts>div{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:14px 16px}
.cards p{margin:0;font-size:17px}
.facts{display:grid;gap:10px}
.facts>div{display:grid;grid-template-columns:170px 1fr;gap:12px;align-items:start}
.facts b:first-child{font:600 21px "Cormorant Garamond",serif;color:var(--rust)}
.btn{display:inline-block;background:var(--rust);color:#fff8ec;text-decoration:none;border-radius:4px;padding:12px 20px;font:600 18px "EB Garamond",serif;border:1px solid var(--rust)}
.btn:hover{background:#6e2d19}
.btn.ghost{background:transparent;color:var(--rust)}
.btn.ghost:hover{background:var(--card)}
.cta-row{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 0}
.route{display:grid;grid-template-columns:minmax(0,3fr) minmax(240px,2fr);gap:18px;align-items:center}
.route svg{width:100%;height:auto;background:#e7dcc3;border:1px solid var(--rule);border-radius:4px}
.route .near{fill:#efe6d2;stroke:#b9a27c;stroke-width:.8}
.route .uz{fill:#d9c49a;stroke:var(--ink);stroke-width:1.4}
.route .line{fill:none;stroke:var(--rust);stroke-width:3;stroke-dasharray:7 5}
.route circle{fill:var(--rust);stroke:#fff8ec;stroke-width:2}
.route text{font:600 17px "EB Garamond",serif;fill:var(--ink);paint-order:stroke;stroke:#e7dcc3;stroke-width:4px}
.route ol{margin:0;padding-left:20px}.route li{margin-bottom:8px}
figure{margin:0}
.heroimg{margin:26px 0 0}.heroimg img,figure.wide img{display:block;width:100%;height:auto;border:1px solid var(--rule);border-radius:4px}
figcaption{font-size:15px;color:var(--muted);margin-top:6px}
figure.wide{margin:18px 0 0}
.cards article{overflow:hidden}
.cards article img{display:block;width:calc(100% + 32px);max-width:none;height:auto;aspect-ratio:4/3;object-fit:cover;margin:-14px -16px 12px;border-bottom:1px solid var(--rule)}
.credits{font-size:13px}
.final{background:var(--card);border:1px solid var(--rule);border-radius:4px;padding:22px;text-align:center;margin:10px 0 34px}
.final h2{margin-bottom:8px}
footer{border-top:1px solid var(--rule);padding-top:14px;color:var(--muted);font-size:15px}
footer a{color:var(--muted)}
footer ul{padding-left:18px;margin:6px 0}
@media (max-width:700px){.facts>div{grid-template-columns:1fr;gap:4px}.route{grid-template-columns:1fr}header.hero{padding:34px 0 24px}}
</style>
</head>
<body data-v="__V__">
<div class="wrap">
<header class="hero">
  <p class="kicker">Uzbekistan · Central Asia</p>
  <h1>__TITLE__</h1>
  <p class="sub">__SUB__</p>
  <a class="btn" data-track="cta_plan" href="__PLAN__" target="_blank" rel="noopener">Plan your trip</a>
  <figure class="heroimg">__IMG_hero__<figcaption>The Registan, Samarkand, at night</figcaption></figure>
</header>
__BLOCKS__
<section class="final">
  <h2>Ready to look closer?</h2>
  <p>Routes, sights and practical tips on Uzbekistan's national tourism website.</p>
  <a class="btn" data-track="cta_plan" href="__PLAN__" target="_blank" rel="noopener">Plan your trip</a>
</section>
<footer>
  <p><b>About this page.</b> It is part of a master's research project at Tashkent State Agrarian University on how digital
  information affects interest in travel to Uzbekistan. It sells nothing. We count visits anonymously — page version,
  country and button clicks only; no cookies and no personal data.</p>
  <p>Facts checked November 2026:</p>
  <ul>__SOURCES__</ul>
  <p>Photos from Wikimedia Commons, cropped and resized:</p>
  <ul class="credits">__CREDITS__</ul>
</footer>
</div>
<script src="track.js"></script>
<script>
(function () {
  var V = document.body.getAttribute("data-v");
  var URL_ = (window.TRACK_URL || "").replace(/\\/$/, "");
  var known = ["meta", "instagram", "facebook", "reddit", "youtube", "google", "telegram", "email",
               "pinterest", "tiktok", "linkedin", "x", "qr", "partner"];
  function source() {
    var p = new URLSearchParams(location.search), s = (p.get("utm_source") || p.get("s") || "").toLowerCase();
    if (s) return known.indexOf(s) >= 0 || /^p-[a-z0-9]{2,16}$/.test(s) ? s : "other";
    var r = document.referrer || "";
    if (/pinterest|pin\\.it/.test(r)) return "pinterest"; if (/tiktok/.test(r)) return "tiktok";
    if (/linkedin|lnkd\\.in/.test(r)) return "linkedin";
    if (/instagram/.test(r)) return "instagram"; if (/facebook|fb\\.com/.test(r)) return "facebook";
    if (/reddit/.test(r)) return "reddit"; if (/youtube/.test(r)) return "youtube";
    if (/google\\./.test(r)) return "google"; if (/t\\.me|telegram/.test(r)) return "telegram";
    return r ? "other" : "direct";
  }
  var SRC = source();
  window.__sent = [];
  function send(e) {
    var key = "uzc_" + V + "_" + e;
    try { if (sessionStorage.getItem(key)) return; sessionStorage.setItem(key, "1"); } catch (x) {}
    window.__sent.push(e);
    if (!URL_) return;
    var body = JSON.stringify({ v: V, e: e, s: SRC });
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(URL_ + "/hit", new Blob([body], { type: "text/plain" }))) return;
    } catch (x) {}
    try { fetch(URL_ + "/hit", { method: "POST", body: body, keepalive: true, mode: "cors" }); } catch (x) {}
  }
  send("view");
  var engaged = false;
  function engage() { if (!engaged) { engaged = true; send("engaged"); } }
  setTimeout(function () { if (document.visibilityState === "visible") engage(); }, 30000);
  window.addEventListener("scroll", function () {
    var h = document.documentElement; if ((h.scrollTop + innerHeight) / h.scrollHeight >= 0.5) engage();
  }, { passive: true });
  document.querySelectorAll("[data-track]").forEach(function (a) {
    a.addEventListener("click", function () { send(a.getAttribute("data-track")); });
  });
})();
</script>
</body>
</html>
"""

SPLIT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uzbekistan</title>
<script>
(function () {
  var v; try { v = localStorage.getItem("uzc_v"); } catch (e) {}
  if (v !== "a" && v !== "b") { v = Math.random() < 0.5 ? "a" : "b"; try { localStorage.setItem("uzc_v", v); } catch (e) {} }
  location.replace(v + ".html" + location.search);
})();
</script></head>
<body><p><a href="a.html">Continue</a></p></body></html>
"""


def _route_svg(m: dict) -> dict:
    near = "".join(f'<path class="near" d="{d}"/>' for d in m["near"])
    order = ["Tashkent", "Samarkand", "Bukhara", "Khiva"]
    pts = " ".join(f"{m['cities'][c][0]},{m['cities'][c][1]}" for c in order)
    anchor = {"Tashkent": ("start", 10, -8), "Samarkand": ("middle", 0, 26), "Bukhara": ("middle", 0, 26), "Khiva": ("middle", 0, -14)}
    dots = ""
    for c in order:
        x, y = m["cities"][c]
        a, dx, dy = anchor[c]
        dots += f'<circle cx="{x}" cy="{y}" r="7"/><text x="{x + dx}" y="{y + dy}" text-anchor="{a}">{c}</text>'
    return {"__W__": str(m["W"]), "__H__": str(m["H"]), "__NEAR__": near, "__UZ__": m["uz"], "__LINE__": pts, "__DOTS__": dots}


def build() -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    m = json.loads(MAP.read_text(encoding="utf-8"))
    rs = _route_svg(m)
    sources = "".join(f'<li><a href="{u}" target="_blank" rel="noopener">{t}</a></li>' for t, u in FACT_SOURCES)
    written = []
    for v, (title, sub, order) in HEROES.items():
        blocks = "\n".join(BLOCKS[k] for k in order)
        html = PAGE.replace("__BLOCKS__", blocks)
        for k, val in rs.items():
            html = html.replace(k, val)
        for key in PHOTOS:
            html = html.replace(f"__IMG_{key}__", _img(key, lazy=key != "hero"))
        html = html.replace("__CREDITS__", _photo_credits())
        html = (html.replace("__TITLE__", title).replace("__SUB__", sub).replace("__V__", v)
                    .replace("__PLAN__", LINKS["plan"]).replace("__RULES__", LINKS["rules"]).replace("__ROUTE__", LINKS["route"])
                    .replace("__SOURCES__", sources))
        assert "__" not in html.replace("window.__sent", ""), "unfilled placeholder"
        path = OUT / f"{v}.html"
        path.write_text(html, encoding="utf-8")
        written.append(path)
    (OUT / "index.html").write_text(SPLIT, encoding="utf-8")
    if not TRACK_JS.exists():
        TRACK_JS.write_text('// Cloudflare worker address for campaign counting, e.g. "https://tourism-bot-clock.NAME.workers.dev"\n'
                            'window.TRACK_URL = "";\n', encoding="utf-8")
    return written


if __name__ == "__main__":
    for p in build():
        print("wrote", p)
