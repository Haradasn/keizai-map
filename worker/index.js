// Keizai Atlas: 静的ファイルは assets から配信。/api/* だけこの Worker が受け持つ(読者の反応を D1 に保存)。
// 個人を特定できる情報(IPアドレス、User-Agent など)は保存しない。
const SCHEMA = [
  "CREATE TABLE IF NOT EXISTS likes (page TEXT NOT NULL, day TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (page, day))",
  "CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, page TEXT, body TEXT NOT NULL)",
];
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
const cleanPage = (p) => (typeof p === "string" && /^\/[\w\-./]{0,120}$/.test(p) ? p.replace(/\.html$/, "").replace(/\/index$/, "/") : null);
const today = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10); // 日本時間の日付

async function ensure(db) { await db.batch(SCHEMA.map((q) => db.prepare(q))); }

async function verifyTurnstile(env, token) {
  if (env.DEV_SKIP_TURNSTILE === "1") return true;           // ローカルの動作確認用(本番では設定しない)
  if (!env.TURNSTILE_SECRET || !token) return false;
  const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST", body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token }),
  });
  const j = await r.json().catch(() => ({}));
  return j.success === true;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(req);
    if (!env.DB) return json({ ok: false, error: "not configured" }, 503);
    // 同じサイトのページからの送信だけ受け付ける
    const origin = req.headers.get("origin");
    if (req.method === "POST" && origin && new URL(origin).host !== url.host) return json({ ok: false }, 403);
    try {
      await ensure(env.DB);
      if (url.pathname === "/api/like" && req.method === "POST") {
        const b = await req.json().catch(() => ({}));
        const page = cleanPage(b.page); if (!page) return json({ ok: false }, 400);
        await env.DB.prepare("INSERT INTO likes (page, day, n) VALUES (?1, ?2, 1) ON CONFLICT(page, day) DO UPDATE SET n = n + 1").bind(page, today()).run();
        return json({ ok: true });
      }
      if (url.pathname === "/api/request" && req.method === "POST") {
        const b = await req.json().catch(() => ({}));
        const body = typeof b.body === "string" ? b.body.trim().slice(0, 500) : "";
        if (body.length < 2) return json({ ok: false, error: "empty" }, 400);
        if (!(await verifyTurnstile(env, b.token))) return json({ ok: false, error: "turnstile" }, 403);
        await env.DB.prepare("INSERT INTO requests (ts, page, body) VALUES (?1, ?2, ?3)").bind(new Date().toISOString(), cleanPage(b.page), body).run();
        return json({ ok: true });
      }
      if (url.pathname === "/api/feedback/export" && req.method === "GET") {   // 週次レポート用(合言葉が必要)
        const key = (req.headers.get("authorization") || "").replace(/^Bearer\s+/, "");
        if (!env.FEEDBACK_KEY || key !== env.FEEDBACK_KEY) return json({ ok: false }, 401);
        const since = url.searchParams.get("since") || "1970-01-01";
        const likes = await env.DB.prepare("SELECT page, SUM(n) AS n FROM likes WHERE day >= ?1 GROUP BY page ORDER BY n DESC").bind(since).all();
        const reqs = await env.DB.prepare("SELECT ts, page, body FROM requests WHERE ts >= ?1 ORDER BY ts").bind(since).all();
        return json({ ok: true, likes: likes.results, requests: reqs.results });
      }
      return json({ ok: false }, 404);
    } catch (e) {
      return json({ ok: false, error: "server" }, 500);
    }
  },
};
