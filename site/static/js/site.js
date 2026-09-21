/* Reading-level and theme toggles. No network, no tracking. */
(function () {
  var d = document.documentElement;
  var announcer = document.getElementById('level-announcer');
  function setLevel(level, announce) {
    d.setAttribute('data-level', level);
    try { localStorage.setItem('gpconf-level', level); } catch (e) { /* ignore */ }
    document.querySelectorAll('[data-set-level]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-set-level') === level ? 'true' : 'false');
    });
    if (announce && announcer) announcer.textContent = 'Showing the ' + level + ' version.';
    document.dispatchEvent(new CustomEvent('gpconf:level', { detail: level }));
  }
  document.querySelectorAll('[data-set-level]').forEach(function (b) {
    b.addEventListener('click', function () { setLevel(b.getAttribute('data-set-level'), true); });
  });
  document.querySelectorAll('a[data-level-link]').forEach(function (a) {
    a.addEventListener('click', function () { setLevel(a.getAttribute('data-level-link'), false); });
  });
  setLevel(d.getAttribute('data-level') || 'simple', false);

  var themeBtn = document.getElementById('theme-toggle');
  var order = ['auto', 'light', 'dark'];
  var icons = { auto: '◐', light: '☀', dark: '☾' };
  function current() { return d.getAttribute('data-theme') || 'auto'; }
  function applyTheme(t) {
    if (t === 'auto') d.removeAttribute('data-theme'); else d.setAttribute('data-theme', t);
    try { if (t === 'auto') localStorage.removeItem('gpconf-theme'); else localStorage.setItem('gpconf-theme', t); } catch (e) { /* ignore */ }
    if (themeBtn) {
      themeBtn.querySelector('.theme-icon').textContent = icons[t];
      themeBtn.setAttribute('aria-label', 'Colour theme: ' + (t === 'auto' ? 'automatic' : t) + '. Activate to switch.');
    }
  }
  if (themeBtn) {
    applyTheme(current());
    themeBtn.addEventListener('click', function () { applyTheme(order[(order.indexOf(current()) + 1) % order.length]); });
  }
})();
