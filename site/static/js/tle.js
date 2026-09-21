/* Anatomy of a TLE: highlights every field of the example lines and parses a pasted line in the browser.
   No network calls anywhere in this file; nothing typed here leaves the page. */
(function () {
  var mount = document.getElementById('tle-anatomy');
  if (!mount) return;
  var A = window.Alpha5;
  var F1 = [
    { c: [1, 1], name: 'Line number', desc: 'Always 1.' },
    { c: [3, 7], name: 'Catalog number', kind: 'catnr', desc: 'Five characters. Plain digits up to 99999. From 100000 on, Space-Track replaces the first digit with a letter (Alpha-5: A=10 … Z=33, no I or O). CelesTrak instead leaves those objects out of TLE output altogether.' },
    { c: [8, 8], name: 'Classification', desc: 'U unclassified, C classified (CelesTrak supplemental records use C), S secret.' },
    { c: [10, 11], name: 'Launch year', desc: 'Two digits of the international designator; no rule in any format document says how to pick the century.' },
    { c: [12, 14], name: 'Launch number of the year' },
    { c: [15, 17], name: 'Piece of the launch' },
    { c: [19, 20], name: 'Epoch year', kind: 'yy', desc: 'Two digits: 57–99 mean 1957–1999, 00–56 mean 2000–2056.' },
    { c: [21, 32], name: 'Epoch day of year with fraction', kind: 'doy', desc: 'Day 1 is January 1st; the fraction has 8 decimals, so the resolution is 864 microseconds.' },
    { c: [34, 43], name: 'First derivative of mean motion, halved', desc: 'Revolutions per day squared, as printed. The OMM keyword MEAN_MOTION_DOT carries this printed value, not the true derivative.' },
    { c: [45, 52], name: 'Second derivative of mean motion, divided by six', kind: 'exp', desc: 'Implied leading decimal point and a one-digit exponent. Zero is written  00000+0 by CelesTrak and  00000-0 by Space-Track.' },
    { c: [54, 61], name: 'BSTAR drag term', kind: 'exp', desc: 'Implied leading decimal point:  10000-3 means 0.10000 × 10⁻³.' },
    { c: [63, 63], name: 'Ephemeris type' },
    { c: [65, 68], name: 'Element set number' },
    { c: [69, 69], name: 'Checksum', kind: 'ck', desc: 'Add every digit, count each minus sign as 1, ignore letters, blanks, periods and plus signs; keep the last digit.' }
  ];
  var F2 = [
    { c: [1, 1], name: 'Line number', desc: 'Always 2.' },
    { c: [3, 7], name: 'Catalog number', kind: 'catnr', desc: 'Must equal the field on line 1.' },
    { c: [9, 16], name: 'Inclination', unit: 'degrees' },
    { c: [18, 25], name: 'Right ascension of the ascending node', unit: 'degrees' },
    { c: [27, 33], name: 'Eccentricity', kind: 'ecc', desc: 'Seven digits with an implied leading decimal point. CelesTrak truncates the OMM value to seven digits; Space-Track rounds it, so the last digit can differ between the two providers for the same record.' },
    { c: [35, 42], name: 'Argument of perigee', unit: 'degrees' },
    { c: [44, 51], name: 'Mean anomaly', unit: 'degrees' },
    { c: [53, 63], name: 'Mean motion', unit: 'revolutions per day' },
    { c: [64, 68], name: 'Revolution number at epoch' },
    { c: [69, 69], name: 'Checksum', kind: 'ck' }
  ];
  function checksum(line) { var s = 0; for (var i = 0; i < 68 && i < line.length; i++) { var ch = line.charAt(i); if (ch >= '0' && ch <= '9') s += ch.charCodeAt(0) - 48; else if (ch === '-') s += 1; } return s % 10; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function expField(t) { // ' 10000-3' -> value
    var m = /^([ +-])(\d{5})([+-]\d)$/.exec(t); if (!m) return null;
    var sign = m[1] === '-' ? -1 : 1; return sign * parseFloat('0.' + m[2]) * Math.pow(10, parseInt(m[3], 10));
  }
  function doyToDate(year, doy) { var d = new Date(Date.UTC(year, 0, 1)); d.setTime(d.getTime() + (doy - 1) * 86400000); return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC'); }
  function decodeField(f, raw, lines) {
    var v = raw, notes = [];
    try {
      if (f.kind === 'catnr') { var n = A.decode(raw); v = n.toLocaleString('en-US') + (/^[A-Z]/.test(raw) ? ' (Alpha-5, letter ' + raw.charAt(0) + ' = ' + Math.floor(n / 10000) + ')' : ''); }
      else if (f.kind === 'yy') { var yy = parseInt(raw, 10); v = String(yy < 57 ? 2000 + yy : 1900 + yy); }
      else if (f.kind === 'doy') { var yy2 = parseInt(lines[0].substr(18, 2), 10); v = doyToDate(yy2 < 57 ? 2000 + yy2 : 1900 + yy2, parseFloat(raw)); }
      else if (f.kind === 'exp') { var x = expField(raw); v = x == null ? 'not in the ±NNNNN±N form' : x.toExponential(4); }
      else if (f.kind === 'ecc') { v = '0.' + raw.trim(); }
      else if (f.kind === 'ck') { var line = f.c[0] === 69 && lines ? null : null; v = raw; }
      else if (f.unit) { v = parseFloat(raw) + ' ' + f.unit; }
    } catch (e) { notes.push(e.message); v = 'invalid: ' + e.message; }
    return { value: v, notes: notes };
  }
  function ruler() { var tens = '', ones = ''; for (var i = 1; i <= 69; i++) { tens += (i % 10 === 0) ? String(i / 10) : ' '; ones += String(i % 10); } return tens + '\n' + ones; }
  function buildLine(line, fields, lineIdx, lines, panel) {
    var frag = document.createDocumentFragment(), pos = 0;
    fields.forEach(function (f) {
      var start = f.c[0] - 1, end = f.c[1];
      if (start > pos) frag.appendChild(document.createTextNode(line.substring(pos, start)));
      var b = document.createElement('button'); b.type = 'button'; b.className = 'fld'; b.textContent = line.substring(start, end).padEnd(end - start, ' ');
      b.setAttribute('aria-label', f.name + ', columns ' + f.c[0] + (f.c[1] !== f.c[0] ? ' to ' + f.c[1] : '') + ', value ' + line.substring(start, end).trim());
      b.setAttribute('aria-pressed', 'false');
      var showIt = function () {
        mount.querySelectorAll('.fld[aria-pressed="true"]').forEach(function (o) { o.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        var raw = line.substring(start, end), dec = decodeField(f, raw, lines);
        var extra = '';
        if (f.kind === 'ck') { var want = checksum(line); extra = '<dt>computed</dt><dd>' + want + (String(want) === raw ? ' (matches)' : ' (line says ' + esc(raw) + ': mismatch)') + '</dd>'; }
        panel.innerHTML = '<h3>' + esc(f.name) + '</h3><dl class="kv"><dt>line</dt><dd>' + (lineIdx + 1) + '</dd><dt>columns</dt><dd>' + f.c[0] + (f.c[1] !== f.c[0] ? '–' + f.c[1] : '') + '</dd><dt>as printed</dt><dd><code>' + esc(raw) + '</code></dd><dt>meaning</dt><dd>' + esc(dec.value) + '</dd>' + extra + '</dl>' + (f.desc ? '<p class="small">' + esc(f.desc) + '</p>' : '');
      };
      b.addEventListener('click', showIt); b.addEventListener('focus', showIt); b.addEventListener('mouseenter', showIt);
      frag.appendChild(b); pos = end;
    });
    if (pos < line.length) frag.appendChild(document.createTextNode(line.substring(pos)));
    return frag;
  }
  function renderSet(lines, label) {
    var view = document.getElementById('tle-view'), panel = document.getElementById('tle-panel');
    view.textContent = '';
    var r = document.createElement('span'); r.className = 'ruler'; r.textContent = ruler() + '\n'; view.appendChild(r);
    if (lines.length === 3) { view.appendChild(document.createTextNode(lines[0] + '\n')); }
    var l12 = lines.length === 3 ? lines.slice(1) : lines;
    view.appendChild(buildLine(l12[0], F1, 0, l12, panel)); view.appendChild(document.createTextNode('\n'));
    view.appendChild(buildLine(l12[1], F2, 1, l12, panel));
    panel.innerHTML = '<h3>' + esc(label) + '</h3><p class="small">Hover, tap or tab through the fields to see what each one means.</p>';
  }
  var examples = JSON.parse(document.getElementById('tle-examples').textContent);
  function showExample(key) { var ex = examples[key]; renderSet([ex.line0, ex.line1, ex.line2], ex.label); }
  document.querySelectorAll('[data-tle-example]').forEach(function (b) { b.addEventListener('click', function () {
    document.querySelectorAll('[data-tle-example]').forEach(function (o) { o.setAttribute('aria-pressed', o === b ? 'true' : 'false'); });
    showExample(b.getAttribute('data-tle-example'));
  }); });
  showExample('goes9');

  // Paste box: parsed here, sent nowhere.
  var ta = document.getElementById('tle-paste'), report = document.getElementById('tle-paste-report');
  function parsePasted() {
    var text = ta.value.replace(/\r/g, ''); if (!text.trim()) { report.innerHTML = ''; return; }
    var rows = text.split('\n').map(function (s) { return s.replace(/\s+$/, ''); }).filter(function (s) { return s.length; });
    var l1 = null, l2 = null, l0 = null;
    rows.forEach(function (s) { if (/^1 /.test(s) && !l1) l1 = s; else if (/^2 /.test(s) && !l2) l2 = s; else if (!l0 && !/^[12] /.test(s)) l0 = s; });
    var problems = [], infos = [];
    if (!l1 || !l2) { report.innerHTML = '<p class="result bad">Need a line starting with “1 ” and a line starting with “2 ”.</p>'; return; }
    [l1, l2].forEach(function (s, i) {
      if (s.length !== 69) problems.push('line ' + (i + 1) + ' has ' + s.length + ' characters, not 69');
      else { var ck = checksum(s); if (String(ck) !== s.charAt(68)) problems.push('line ' + (i + 1) + ' checksum is ' + s.charAt(68) + ', computed ' + ck); }
    });
    var f1 = l1.substr(2, 5), f2 = l2.substr(2, 5);
    if (f1 !== f2) problems.push('catalog fields differ between the lines (' + f1 + ' vs ' + f2 + ')');
    try { var n = A.decode(f1); infos.push('catalog number ' + n.toLocaleString('en-US') + (/^[A-Z]/.test(f1) ? ' (Alpha-5 field ' + f1 + ')' : '') + (n >= 100000 ? '; CelesTrak would not serve this object as a TLE' : '')); }
    catch (e) { problems.push('catalog field ' + JSON.stringify(f1) + ': ' + e.message); }
    var lines = [l0 || '', l1.padEnd(69, ' '), l2.padEnd(69, ' ')];
    renderSet(l0 ? lines : lines.slice(1), 'Your pasted line');
    report.innerHTML = (problems.length ? '<ul class="result bad">' + problems.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>' : '<p class="result ok">Both lines are 69 characters with valid checksums.</p>') + (infos.length ? '<ul>' + infos.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>' : '');
  }
  ta.addEventListener('input', parsePasted);
})();
