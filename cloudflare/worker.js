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
  if (!(await botHasMail(env))) return "no messages";
  if (await isBusy(env, "approvals.yml")) return "bot already running";
  await startWorkflow(env, "approvals.yml");
  return "bot started";
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(tick(event.cron, env).then(r => console.log(event.cron, "→", r)));
  },
  // Opening the worker's address in a browser shows whether the secrets work.
  async fetch(request, env) {
    const checks = [];
    try { await botHasMail(env); checks.push("✅ Telegram token works"); }
    catch (e) { checks.push("❌ Telegram: " + e.message); }
    try { await isBusy(env, "approvals.yml"); checks.push("✅ GitHub token works"); }
    catch (e) { checks.push("❌ GitHub: " + e.message); }
    return new Response("Uzbekistan Tourism Monitor worker\n\n" + checks.join("\n") + "\n",
      { headers: { "content-type": "text/plain; charset=utf-8" } });
  },
};
