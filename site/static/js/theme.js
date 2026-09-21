/* Runs before paint: applies the stored reading level and colour theme, honours ?level=, marks JS on. */
(function () {
  var d = document.documentElement;
  d.classList.remove('no-js');
  var level = null;
  try {
    var q = new URLSearchParams(location.search).get('level');
    if (q === 'simple' || q === 'technical') { level = q; localStorage.setItem('gpconf-level', q); }
    if (!level) level = localStorage.getItem('gpconf-level');
  } catch (e) { /* storage unavailable: defaults apply */ }
  if (level !== 'simple' && level !== 'technical') level = 'simple';
  d.setAttribute('data-level', level);
  var theme = null;
  try {
    var qt = new URLSearchParams(location.search).get('theme');
    if (qt === 'light' || qt === 'dark') { theme = qt; localStorage.setItem('gpconf-theme', qt); }
    if (!theme) theme = localStorage.getItem('gpconf-theme');
  } catch (e) { /* ignore */ }
  if (theme === 'light' || theme === 'dark') d.setAttribute('data-theme', theme);
})();
