/* Activity page: reads /api/activity (same origin, edge-cached) and fills in state, dates, counts. */
(function () {
  var root = document.getElementById('activity');
  if (!root) return;
  var status = document.getElementById('activity-status');
  function rel(iso) {
    if (!iso) return '';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 90) return 'just now';
    var m = Math.round(s / 60); if (m < 90) return m + ' minutes ago';
    var h = Math.round(s / 3600); if (h < 36) return h + ' hours ago';
    var d = Math.round(s / 86400); if (d < 45) return d + ' days ago';
    var mo = Math.round(d / 30); if (mo < 18) return mo + ' months ago';
    return Math.round(d / 365) + ' years ago';
  }
  function day(iso) { return iso ? iso.slice(0, 10) : ''; }
  function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }
  var SIMPLE = {
    issue: { open: 'A reported problem that is still open.', closed: 'A reported problem that has been closed.' },
    pull: { open: 'A proposed fix waiting for the library’s owner to review it.', merged: 'A fix that the library’s owner has accepted into the code.', closed: 'A proposed fix that was closed without being merged.', draft: 'A proposed fix still being worked on.' }
  };
  function badgeClass(state) { return state === 'open' ? 'open' : state === 'merged' ? 'merged' : 'closed'; }
  function render(data) {
    (data.items || []).forEach(function (it) {
      var el = root.querySelector('[data-activity-item="' + it.id + '"]');
      if (!el) return;
      var badge = el.querySelector('[data-state]'), meta = el.querySelector('[data-meta]'), simple = el.querySelector('[data-simple]'), link = el.querySelector('[data-link]');
      if (it.missing) { badge.textContent = 'not found'; badge.className = 'badge neutral'; return; }
      var state = it.draft && it.state === 'open' ? 'draft' : it.state;
      badge.textContent = state; badge.className = 'badge ' + badgeClass(it.state);
      if (link && it.url) link.href = it.url;
      var parts = ['Opened ' + day(it.created_at)];
      if (it.merged) parts.push('merged ' + day(it.merged_at));
      else if (it.closed_at) parts.push('closed ' + day(it.closed_at));
      parts.push('updated ' + rel(it.updated_at)); parts.push(plural(it.comments || 0, 'comment'));
      if (it.kind === 'pull' && it.commits != null) parts.push(plural(it.commits, 'commit') + (it.changed_files != null ? ', ' + plural(it.changed_files, 'file') : ''));
      meta.textContent = parts.join(' · ') + '.';
      if (simple) simple.textContent = (SIMPLE[it.kind] || {})[state] || '';
    });
    var c = data.repos && data.repos.corpus;
    if (c) {
      var relEl = root.querySelector('[data-repo="corpus-release"]'), relDate = root.querySelector('[data-repo="corpus-release-date"]');
      if (c.latest_release) { relEl.textContent = c.latest_release.tag; relDate.innerHTML = ''; var a = document.createElement('a'); a.href = c.latest_release.url; a.textContent = 'released ' + day(c.latest_release.published_at); relDate.appendChild(a); }
      if (c.pushed_at) root.querySelector('[data-repo="corpus-pushed"]').textContent = rel(c.pushed_at);
    }
    var s = data.repos && data.repos.site;
    if (s && s.pushed_at) { root.querySelector('[data-repo="site-pushed"]').textContent = rel(s.pushed_at); var sub = root.querySelector('[data-repo="site-sub"]'); sub.innerHTML = ''; var b = document.createElement('a'); b.href = s.url; b.textContent = 'repository'; sub.appendChild(b); }
    var note = 'Data from GitHub, refreshed at most hourly. Last updated ' + rel(data.generated_at) + ' (' + (data.generated_at || '').replace('T', ' ').replace(/\.\d+Z$/, ' UTC') + ').';
    if (data.stale) note += ' GitHub could not be reached just now, so this is the last good copy.';
    status.textContent = note;
  }
  fetch('/api/activity', { credentials: 'omit' }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); }).then(function (x) {
    if (!x.ok && !(x.d && x.d.items && x.d.items.length)) { status.textContent = 'Live state is unavailable right now (' + (x.d && x.d.error ? x.d.error : 'no data') + '); the links above still work.'; return; }
    render(x.d);
  }).catch(function () { status.textContent = 'Live state could not be loaded; the links above still work.'; });
})();
