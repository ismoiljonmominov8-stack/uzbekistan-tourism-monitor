/**
 * Uzbekistan Tourism Monitor — clock and doorbell (Cloudflare Worker, free plan)
 *
 * Cron triggers to add in Cloudflare (Settings → Triggers → Cron Triggers):
 *   "47 4 * * *"   → 09:47 Tashkent: start the daily run (data, channel post, news)
 *   "23 5 * * MON" → Monday 10:23 Tashkent: start the weekly chart
 *                    (write MON: in Cloudflare 1 means Sunday)
 *   "* * * * *"    → every minute: if someone wrote to the bot or pressed a button,
 *                    start the bot on GitHub right away (reply in ~1–2 minutes)
 *
 * Secrets to add (Settings → Variables and Secrets, type "Secret"):
 *   TELEGRAM_BOT_TOKEN   the bot token from @BotFather
 *   GITHUB_TOKEN         fine-grained token with Actions: Read and write on the repository
 *
 * Campaign test (landing page versions A and B), optional:
 *   Storage & Databases → D1 → Create database "tourism_stats"; then in this worker
 *   Settings → Bindings → Add → D1 database → variable name DB → tourism_stats.
 *   POST /hit   — the landing page reports a view / engaged reader / button click. Only COUNTS are stored:
 *                 day, version, event, visitor country (from Cloudflare), traffic source. No IP, no cookies.
 *                 Protection: only the campaign pages (ORIGINS) may report; at most DAILY_CAP hits a day; at most
 *                 PER_VISITOR_HOUR hits per visitor per hour (the address is kept in memory only, never stored).
 *   GET  /stats — all counts as JSON (read by the daily GitHub run).
 */
const REPO = "ismoiljonmominov8-stack/uzbekistan-tourism-monitor";

async function gh(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "uzbekistan-tourism-monitor-worker",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
    },
  });
}

async function startWorkflow(env, file) {
  const r = await gh(env, `/actions/workflows/${file}/dispatches`, {
    method: "POST", body: JSON.stringify({ ref: "main" }),
  });
  if (r.status !== 204) throw new Error(`GitHub refused to start ${file}: ${r.status} ${await r.text()}`);
  return true;
}

async function isBusy(env, file) {
  for (const status of ["queued", "in_progress"]) {
    const r = await gh(env, `/actions/workflows/${file}/runs?status=${status}&per_page=1`);
    if (!r.ok) throw new Error(`GitHub runs check failed: ${r.status}`);
    if ((await r.json()).total_count > 0) return true;
  }
  return false;
}

// Looks at waiting Telegram messages WITHOUT taking them (no offset), so the bot on GitHub
// still receives and answers every one of them.
async function botHasMail(env) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getUpdates?limit=1&timeout=0`);
  const j = await r.json();
  if (!j.ok) throw new Error(`Telegram: ${j.description}`);
  return j.result.length > 0;
}

export async function tick(cron, env) {
  // matched by time, so the weekday spelling (MON / 2 / 1) does not matter
  if (cron.startsWith("47 4 ")) return (await startWorkflow(env, "daily.yml")) && "daily started";
  if (cron.startsWith("23 5 ")) return (await startWorkflow(env, "weekly.yml")) && "weekly started";
  // the bot already running is reading Telegram itself; peeking now would collide with it
  if (await isBusy(env, "approvals.yml")) return "bot already running";
  if (!(await botHasMail(env))) return "no messages";
  await startWorkflow(env, "approvals.yml");
  return "bot started";
}

// ---------------------------------------------------------------- campaign counting
const EVENTS = new Set(["view", "engaged", "cta_plan", "cta_rules", "cta_route"]);
const VERSIONS = new Set(["a", "b"]);
const SOURCES = new Set(["meta", "instagram", "facebook", "reddit", "youtube", "google", "telegram", "email", "direct",
                         "pinterest", "tiktok", "linkedin", "x", "qr", "partner", "other"]);
const PARTNER = /^p-[a-z0-9]{2,16}$/;   // one label per partner, e.g. ?utm_source=p-aua
const BOT = /bot|crawl|spider|slurp|preview|facebookexternalhit|headless|lighthouse|monitor/i;
// Protection: only the campaign pages may report visits; a hard daily ceiling; a short-lived per-visitor limit.
const ORIGINS = new Set(["https://ismoiljonmominov8-stack.github.io"]);
const DAILY_CAP = 5000;          // more hits than this in one day = an attack, not a campaign; stop counting until tomorrow
const PER_VISITOR_HOUR = 20;     // a real visitor sends at most 5 events per page
const recent = new Map();        // kept in memory for at most an hour, never written anywhere
let recentHour = -1, capDay = "", capped = false;
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
               "Access-Control-Allow-Headers": "Content-Type" };
let tableReady = false;

async function ensureTable(db) {
  if (tableReady) return;
  await db.prepare("CREATE TABLE IF NOT EXISTS hits (day TEXT, v TEXT, e TEXT, country TEXT, src TEXT, n INTEGER, " +
                   "PRIMARY KEY (day, v, e, country, src))").run();
  tableReady = true;
}

export async function hit(request, env) {
  if (!env.DB) return new Response("tracking not configured", { status: 503, headers: CORS });
  const origin = request.headers.get("origin") || "";
  if (!ORIGINS.has(origin) && origin !== (env.EXTRA_ORIGIN || "-")) return new Response("forbidden", { status: 403, headers: CORS });
  if (BOT.test(request.headers.get("user-agent") || "")) return new Response("ignored", { status: 202, headers: CORS });
  // per-visitor limit, in memory only (the address is never stored)
  const hour = Math.floor(Date.now() / 3600000);
  if (hour !== recentHour) { recent.clear(); recentHour = hour; }
  const who = request.headers.get("cf-connecting-ip") || "?";
  const seen = (recent.get(who) || 0) + 1;
  recent.set(who, seen);
  if (seen > PER_VISITOR_HOUR) return new Response("too many", { status: 429, headers: CORS });
  const raw = await request.text();
  if (raw.length > 300) return new Response("too long", { status: 413, headers: CORS });
  let b;
  try { b = JSON.parse(raw); } catch (e) { return new Response("bad json", { status: 400, headers: CORS }); }
  const s = String(b.s || "").toLowerCase();
  const v = String(b.v || "").toLowerCase(), e = String(b.e || ""), src = SOURCES.has(s) || PARTNER.test(s) ? s : "other";
  if (!VERSIONS.has(v) || !EVENTS.has(e)) return new Response("bad event", { status: 400, headers: CORS });
  const country = /^[A-Z]{2}$/.test(request.cf?.country || "") ? request.cf.country : "XX";
  const day = new Date().toISOString().slice(0, 10);
  await ensureTable(env.DB);
  // daily ceiling: checked from the database, remembered for the rest of the day once reached
  if (capDay !== day) { capDay = day; capped = false; }
  if (capped) return new Response("daily limit", { status: 429, headers: CORS });
  const total = await env.DB.prepare("SELECT COALESCE(SUM(n), 0) AS t FROM hits WHERE day = ?1").bind(day).first("t");
  if (total >= DAILY_CAP) { capped = true; return new Response("daily limit", { status: 429, headers: CORS }); }
  await env.DB.prepare("INSERT INTO hits (day, v, e, country, src, n) VALUES (?1, ?2, ?3, ?4, ?5, 1) " +
                       "ON CONFLICT (day, v, e, country, src) DO UPDATE SET n = n + 1").bind(day, v, e, country, src).run();
  return new Response("ok", { status: 200, headers: CORS });
}

export async function stats(env) {
  if (!env.DB) return Response.json({ error: "tracking not configured" }, { status: 503, headers: CORS });
  await ensureTable(env.DB);
  const { results } = await env.DB.prepare("SELECT day, v, e, country, src, n FROM hits ORDER BY day, v, e").all();
  return Response.json({ rows: results }, { headers: { ...CORS, "Cache-Control": "no-store" } });
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(tick(event.cron, env).then(r => console.log(event.cron, "→", r)));
  },
  // Opening the worker's address in a browser shows whether the secrets work.
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (path === "/hit" && request.method === "POST") return hit(request, env);
    if (path === "/stats") return stats(env);
    const checks = [];
    try { await botHasMail(env); checks.push("✅ Telegram token works"); }
    catch (e) {
      // "Conflict" = the bot on GitHub is reading messages at this moment: the token works
      checks.push(/Conflict/.test(e.message) ? "✅ Telegram token works (the bot is answering right now)"
                                             : "❌ Telegram: " + e.message);
    }
    try { await isBusy(env, "approvals.yml"); checks.push("✅ GitHub token works"); }
    catch (e) { checks.push("❌ GitHub: " + e.message); }
    if (env.DB) {
      try { await ensureTable(env.DB); checks.push("✅ Campaign counting works (database DB connected)"); }
      catch (e) { checks.push("❌ Campaign counting: " + e.message); }
    } else checks.push("ℹ️ Campaign counting off: add a D1 database binding named DB");
    return new Response("Uzbekistan Tourism Monitor worker\n\n" + checks.join("\n") + "\n",
      { headers: { "content-type": "text/plain; charset=utf-8" } });
  },
};
