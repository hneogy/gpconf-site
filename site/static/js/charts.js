/* History charts for the tracker page: tiny inline SVG, no library. Reads /data/tracker/history.json (same origin). */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  function el(name, attrs, text) {
    var e = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function get(entry, path) {
    return path.split('.').reduce(function (o, k) { return o == null ? null : o[k]; }, entry);
  }
  function fmt(n) { return n == null ? '—' : Number(n).toLocaleString('en-US'); }

  function lineChart(container, entries, spec) {
    var W = 520, H = 200, padL = 62, padR = 12, padT = 14, padB = 34;
    var pts = entries.map(function (e) { return { date: e.date, v: get(e, spec.path), seed: e.kind === 'seed', ok: get(e, spec.okPath) !== false }; })
                     .filter(function (p) { return p.v != null && p.ok; });
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': spec.title + ', ' + pts.length + ' data points' });
    if (!pts.length) { container.appendChild(el('svg', { viewBox: '0 0 520 60', role: 'img', 'aria-label': 'no data' })); return; }
    var vals = pts.map(function (p) { return p.v; });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    if (spec.zero) min = Math.min(0, min);
    if (max === min) { max = max + 1; min = min - 1; }
    var span = max - min; min -= span * 0.08; max += span * 0.08;
    var n = pts.length;
    var x = function (i) { return n === 1 ? (padL + (W - padL - padR) / 2) : padL + (W - padL - padR) * i / (n - 1); };
    var y = function (v) { return padT + (H - padT - padB) * (1 - (v - min) / (max - min)); };
    svg.appendChild(el('line', { x1: padL, y1: padT, x2: padL, y2: H - padB, class: 'axis' }));
    svg.appendChild(el('line', { x1: padL, y1: H - padB, x2: W - padR, y2: H - padB, class: 'axis' }));
    [min + span * 0.08, max - span * 0.08].forEach(function (v) {
      svg.appendChild(el('text', { x: padL - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'lbl' }, fmt(Math.round(v))));
    });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(p.v).toFixed(1); }).join(' ');
    if (n > 1) svg.appendChild(el('path', { d: d, class: 'series' }));
    pts.forEach(function (p, i) {
      var c = el('circle', { cx: x(i), cy: y(p.v), r: n > 40 ? 2 : 3.5, class: 'dot' + (p.seed ? ' seed' : '') });
      c.appendChild(el('title', {}, p.date + ': ' + fmt(p.v) + (p.seed ? ' (seed from the corpus)' : '')));
      svg.appendChild(c);
    });
    svg.appendChild(el('text', { x: padL, y: H - 10, class: 'lbl' }, pts[0].date));
    if (n > 1) svg.appendChild(el('text', { x: W - padR, y: H - 10, 'text-anchor': 'end', class: 'lbl' }, pts[n - 1].date));
    container.appendChild(svg);
    table(container, pts, spec, function (p) { return fmt(p.v); });
  }

  function boolChart(container, entries, spec) {
    var pts = entries.map(function (e) { return { date: e.date, v: get(e, spec.path), seed: e.kind === 'seed' }; });
    var W = 520, cell = Math.max(6, Math.min(24, Math.floor((W - 20) / Math.max(pts.length, 1)))), H = 60;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': spec.title + ', ' + pts.length + ' days' });
    pts.forEach(function (p, i) {
      var cls = p.v === true ? 'bool-true' : (p.v === false ? 'bool-false' : 'bool-null');
      var r = el('rect', { x: 10 + i * cell, y: 8, width: cell - 2, height: 26, rx: 3, class: cls });
      r.appendChild(el('title', {}, p.date + ': ' + (p.v === true ? spec.yes : p.v === false ? spec.no : 'no data')));
      svg.appendChild(r);
    });
    svg.appendChild(el('text', { x: 10, y: 52, class: 'lbl' }, pts.length ? pts[0].date : ''));
    if (pts.length > 1) svg.appendChild(el('text', { x: 10 + pts.length * cell - 2, y: 52, 'text-anchor': 'end', class: 'lbl' }, pts[pts.length - 1].date));
    container.appendChild(svg);
    table(container, pts, spec, function (p) { return p.v === true ? spec.yes : p.v === false ? spec.no : 'no data'; });
  }

  function table(container, pts, spec, cellText) {
    var det = document.createElement('details');
    var sum = document.createElement('summary'); sum.textContent = 'Data table (' + pts.length + ' rows)'; det.appendChild(sum);
    var t = document.createElement('table'); var tb = document.createElement('tbody');
    var th = document.createElement('tr'); th.innerHTML = '<th scope="col">date</th><th scope="col">' + spec.title + '</th>';
    t.appendChild(document.createElement('thead')).appendChild(th);
    pts.slice().reverse().forEach(function (p) {
      var tr = document.createElement('tr'); var a = document.createElement('td'); var b = document.createElement('td');
      a.textContent = p.date + (p.seed ? ' (seed)' : ''); b.textContent = cellText(p); tr.appendChild(a); tr.appendChild(b); tb.appendChild(tr);
    });
    t.appendChild(tb); det.appendChild(t); container.appendChild(det);
  }

  var SPECS = {
    highest: { kind: 'line', title: 'highest catalog number in the last-30-days group', path: 'metrics.last30.highest', okPath: 'metrics.last30.ok' },
    six: { kind: 'line', title: 'six-digit objects in the last-30-days group', path: 'metrics.last30.six_digit', okPath: 'metrics.last30.ok', zero: true },
    tle404: { kind: 'bool', title: 'last-30-days TLE request returns 404', path: 'metrics.last30_tle.is_404', yes: '404 (no TLE)', no: 'TLE data returned' },
    analystcsv: { kind: 'line', title: 'analyst objects in CSV', path: 'metrics.analyst.records', okPath: 'metrics.analyst.ok', zero: true },
    analysttle: { kind: 'line', title: 'analyst objects in TLE', path: 'metrics.analyst_tle.records', okPath: 'metrics.analyst_tle.ok', zero: true },
    nine: { kind: 'line', title: 'nine-digit ids in the Starlink SupGP feed', path: 'metrics.supgp_starlink.nine_digit', okPath: 'metrics.supgp_starlink.ok', zero: true },
    ninebool: { kind: 'bool', title: 'nine-digit ids present in the Starlink SupGP feed', path: 'metrics.supgp_starlink.nine_digit_present', yes: 'present', no: 'none' }
  };

  function run(history) {
    document.querySelectorAll('[data-chart]').forEach(function (c) {
      var spec = SPECS[c.getAttribute('data-chart')];
      if (!spec) return;
      c.textContent = '';
      (spec.kind === 'bool' ? boolChart : lineChart)(c, history, spec);
    });
  }
  var mount = document.querySelector('[data-chart]');
  if (!mount) return;
  fetch('/data/tracker/history.json', { credentials: 'omit' }).then(function (r) { return r.json(); }).then(run).catch(function () {
    document.querySelectorAll('[data-chart]').forEach(function (c) { c.textContent = 'Chart data could not be loaded; the table above still shows the last values.'; });
  });
})();
