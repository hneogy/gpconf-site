/* Cloudflare Pages Function: GET /api/activity
 *
 * Queries the GitHub REST API for a fixed list of public items (two python-sgp4 issues, two pull
 * requests, and the two public repositories of this project), keeps state, dates, counts and links
 * only, and caches the result at the edge for one hour so that GitHub sees at most about one
 * refresh per hour per edge location. A long-lived "last good" copy is kept as well: if GitHub
 * fails, that copy is served with its original timestamp and a stale flag.
 *
 * Authentication: env.GITHUB_TOKEN (a Cloudflare Pages secret; read-only, public repositories).
 * Without it the function still works, unauthenticated, within GitHub's 60 requests/hour limit.
 * No token is ever written into a response.
 */
const GITHUB = 'https://api.github.com';
const UPSTREAM = 'brandon-rhodes/python-sgp4';
export const ITEMS = [
  { id: 'python-sgp4#169', repo: UPSTREAM, kind: 'issue', number: 169 },
  { id: 'python-sgp4#170', repo: UPSTREAM, kind: 'pull', number: 170 },
  { id: 'python-sgp4#171', repo: UPSTREAM, kind: 'issue', number: 171 },
  { id: 'python-sgp4#172', repo: UPSTREAM, kind: 'pull', number: 172 },
];
export const REPOS = { corpus: 'hneogy/gp-omm-conformance', site: 'hneogy/gpconf-site' };
export const FRESH_SECONDS = 3600;
export const LAST_GOOD_SECONDS = 30 * 86400;
const USER_AGENT = 'gpconf-site/0.1 (+https://gpconf.neogy.dev; activity function, one refresh per hour)';

function headersFor(env) {
  const h = { accept: 'application/vnd.github+json', 'user-agent': USER_AGENT, 'x-github-api-version': '2022-11-28' };
  if (env && env.GITHUB_TOKEN) h.authorization = 'Bearer ' + env.GITHUB_TOKEN;
  return h;
}

async function gh(path, env, fetchImpl) {
  const r = await fetchImpl(GITHUB + path, { headers: headersFor(env) });
  const rate = {
    limit: Number(r.headers.get('x-ratelimit-limit')) || null,
    remaining: r.headers.get('x-ratelimit-remaining') === null ? null : Number(r.headers.get('x-ratelimit-remaining')),
  };
  if (r.status === 404) return { data: null, rate };
  if (!r.ok) throw new Error('GitHub responded ' + r.status + ' for ' + path);
  return { data: await r.json(), rate };
}

// Only state, dates, counts and links are kept. No titles, no bodies, no comment text.
function issueRecord(item, d) {
  return {
    ...item, url: d.html_url, state: d.state, state_reason: d.state_reason || null,
    created_at: d.created_at, updated_at: d.updated_at, closed_at: d.closed_at || null, comments: d.comments || 0,
  };
}
function pullRecord(item, d) {
  const merged = Boolean(d.merged || d.merged_at);
  return {
    ...item, url: d.html_url, state: merged ? 'merged' : d.state, merged, merged_at: d.merged_at || null,
    draft: Boolean(d.draft), created_at: d.created_at, updated_at: d.updated_at, closed_at: d.closed_at || null,
    comments: (d.comments || 0) + (d.review_comments || 0), commits: d.commits ?? null, changed_files: d.changed_files ?? null,
    head_sha: d.head && d.head.sha ? d.head.sha.slice(0, 7) : null, base: d.base ? d.base.ref : null,
  };
}
function repoRecord(d) {
  return d ? { full_name: d.full_name, url: d.html_url, pushed_at: d.pushed_at, updated_at: d.updated_at, default_branch: d.default_branch } : null;
}
function releaseRecord(d) {
  return d ? { tag: d.tag_name, url: d.html_url, published_at: d.published_at, prerelease: Boolean(d.prerelease) } : null;
}

export async function buildActivity(env, fetchImpl = fetch) {
  const calls = ITEMS.map((i) => gh('/repos/' + i.repo + '/' + (i.kind === 'pull' ? 'pulls' : 'issues') + '/' + i.number, env, fetchImpl));
  calls.push(gh('/repos/' + REPOS.corpus + '/releases/latest', env, fetchImpl));
  calls.push(gh('/repos/' + REPOS.corpus, env, fetchImpl));
  calls.push(gh('/repos/' + REPOS.site, env, fetchImpl));
  const results = await Promise.all(calls);
  const items = ITEMS.map((item, i) => {
    const d = results[i].data;
    if (!d) return { ...item, missing: true };
    return item.kind === 'pull' ? pullRecord(item, d) : issueRecord(item, d);
  });
  const n = ITEMS.length;
  return {
    generated_at: new Date().toISOString(),
    source: 'GitHub REST API',
    authenticated: Boolean(env && env.GITHUB_TOKEN),
    refresh_seconds: FRESH_SECONDS,
    requests_per_refresh: calls.length,
    rate_limit: results[results.length - 1].rate,
    items,
    repos: {
      corpus: { ...repoRecord(results[n + 1].data), latest_release: releaseRecord(results[n].data) },
      site: repoRecord(results[n + 2].data),
    },
    stale: false,
  };
}

function json(body, status, extra) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public, max-age=300', 'access-control-allow-origin': '*', ...extra },
  });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const cache = caches.default;
  const base = new URL(request.url);
  base.search = '';
  const freshKey = new Request(base.toString() + '?tier=fresh');
  const goodKey = new Request(base.toString() + '?tier=last-good');

  const hit = await cache.match(freshKey);
  if (hit) return json(await hit.json(), 200, { 'x-gpconf-cache': 'HIT' });

  try {
    const data = await buildActivity(env);
    const body = JSON.stringify(data);
    const store = (ttl) => new Response(body, { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=' + ttl } });
    await Promise.all([cache.put(freshKey, store(FRESH_SECONDS)), cache.put(goodKey, store(LAST_GOOD_SECONDS))]);
    return json(data, 200, { 'x-gpconf-cache': 'MISS' });
  } catch (err) {
    const stale = await cache.match(goodKey);
    if (stale) {
      const data = await stale.json();
      data.stale = true;
      data.stale_reason = String((err && err.message) || err);
      data.served_at = new Date().toISOString();
      return json(data, 200, { 'x-gpconf-cache': 'STALE', 'cache-control': 'public, max-age=60' });
    }
    return json({ error: 'GitHub is unreachable and no cached copy exists yet', detail: String((err && err.message) || err), generated_at: null, items: [], stale: true }, 503, { 'x-gpconf-cache': 'NONE', 'cache-control': 'no-store' });
  }
}
