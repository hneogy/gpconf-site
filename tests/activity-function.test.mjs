// Unit test for the Pages Function's data builder with a fake GitHub. `node tests/activity-function.test.mjs`
import assert from 'node:assert/strict';
// activity.js is an ES module under a .js name; Node resolves it as one because functions/package.json declares
// "type": "module" (guarded by tests/test_site.py, S-027), not because of module-syntax detection.
import { buildActivity, ITEMS, REPOS, FRESH_SECONDS } from '../functions/api/activity.js';

const calls = [];
const fakeFetch = async (url, opts) => {
  calls.push({ url, headers: opts.headers });
  const h = { 'content-type': 'application/json', 'x-ratelimit-limit': '5000', 'x-ratelimit-remaining': '4990' };
  const reply = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: h });
  if (url.endsWith('/issues/169')) return reply({ html_url: 'u169', state: 'open', created_at: '2026-08-20T15:32:00Z', updated_at: '2026-09-21T00:00:00Z', comments: 3, title: 'SECRET TITLE', body: 'SECRET BODY' });
  if (url.endsWith('/pulls/170')) return reply({ html_url: 'u170', state: 'open', merged: false, draft: false, created_at: '2026-09-01T18:31:09Z', updated_at: '2026-09-21T00:00:00Z', comments: 2, review_comments: 1, commits: 4, changed_files: 2, head: { sha: '5e4f308abcdef' }, base: { ref: 'master' }, title: 'SECRET TITLE' });
  if (url.endsWith('/issues/171')) return reply({ html_url: 'u171', state: 'closed', state_reason: 'completed', created_at: '2026-09-21T04:51:27Z', updated_at: '2026-09-22T00:00:00Z', closed_at: '2026-09-22T00:00:00Z', comments: 1 });
  if (url.endsWith('/pulls/172')) return reply({ html_url: 'u172', state: 'closed', merged: true, merged_at: '2026-09-22T00:00:00Z', created_at: '2026-09-21T20:17:10Z', updated_at: '2026-09-22T00:00:00Z', closed_at: '2026-09-22T00:00:00Z', comments: 0, review_comments: 0, commits: 1, changed_files: 2, head: { sha: 'd281247xyz' }, base: { ref: 'master' } });
  if (url.endsWith('/releases/latest')) return reply({ tag_name: 'v0.1.0', html_url: 'rel', published_at: '2026-09-21T04:36:16Z', prerelease: false, body: 'SECRET NOTES' });
  if (url.endsWith('/' + REPOS.corpus)) return reply({ full_name: REPOS.corpus, html_url: 'repo', pushed_at: '2026-09-21T05:00:00Z', updated_at: '2026-09-21T05:00:00Z', default_branch: 'main' });
  if (url.endsWith('/' + REPOS.site)) return reply({ message: 'Not Found' }, 404);
  throw new Error('unexpected url ' + url);
};

const data = await buildActivity({ GITHUB_TOKEN: 'not-a-real-token-for-test' }, fakeFetch);
assert.equal(calls.length, 7, 'seven REST calls per refresh');
assert.ok(calls.every((c) => c.headers.authorization === 'Bearer not-a-real-token-for-test'));
assert.ok(calls.every((c) => c.headers['user-agent'].includes('gpconf.neogy.dev')));
assert.equal(data.requests_per_refresh, 7);
assert.equal(data.refresh_seconds, FRESH_SECONDS);
assert.equal(data.items.length, ITEMS.length);
const by = Object.fromEntries(data.items.map((i) => [i.id, i]));
assert.equal(by['python-sgp4#169'].state, 'open');
assert.equal(by['python-sgp4#170'].comments, 3, 'PR comments = issue comments + review comments');
assert.equal(by['python-sgp4#170'].head_sha, '5e4f308');
assert.equal(by['python-sgp4#171'].state, 'closed');
assert.equal(by['python-sgp4#172'].state, 'merged');
assert.equal(by['python-sgp4#172'].merged, true);
assert.equal(data.repos.corpus.latest_release.tag, 'v0.1.0');
assert.equal(data.repos.site, null, 'a missing repository is null, not an error');
assert.equal(data.rate_limit.remaining, 4990);
const text = JSON.stringify(data);
assert.ok(!text.includes('SECRET'), 'no title, body or notes text reaches the output');
assert.ok(!text.includes('not-a-real-token'), 'the token never reaches the output');
assert.ok(!('title' in by['python-sgp4#169']));

// a failing GitHub call rejects, so the function can fall back to the last good copy
let threw = false;
try { await buildActivity({}, async () => new Response('nope', { status: 502, headers: {} })); } catch (e) { threw = /502/.test(String(e)); }
assert.ok(threw, 'non-404 errors reject');
console.log(JSON.stringify({ ok: true, calls: calls.length, states: Object.fromEntries(data.items.map((i) => [i.id, i.state])) }));
