/* History charts for the tracker page: tiny inline SVG, no library. Reads /data/tracker/history.json (same origin).
   Each chart is drawn at its container's own width, one SVG unit to one CSS pixel, so its labels are set at text size
   whatever the width, and it is drawn again when that width changes (S-068). */
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
  // the container's width in CSS pixels; 520 where there is no layout (the Node tests' stub document)
  function widthOf(container) { var w = container.clientWidth; return w > 0 ? Math.max(240, Math.round(w)) : 520; }

  function lineChart(container, entries, spec, opts) {
    var lead = !!(opts && opts.lead);
    var W = widthOf(container), H = lead ? 300 : 180, padL = 72, padR = 16, padT = lead ? 30 : 22, padB = 34;
    var pts = entries.map(function (e) { return { date: e.date, v: get(e, spec.path), seed: e.kind === 'seed', ok: get(e, spec.okPath) !== false }; })
                     .filter(function (p) { return p.v != null && p.ok; });
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': spec.title + ', ' + pts.length + ' data points' });
    if (!pts.length) { container.appendChild(el('svg', { viewBox: '0 0 520 60', role: 'img', 'aria-label': 'no data' })); return; }
    var vals = pts.map(function (p) { return p.v; });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    if (spec.zero) min = Math.min(0, min);
    if (spec.ref != null) { min = Math.min(min, spec.ref); max = Math.max(max, spec.ref); }
    if (max === min) { max = max + 1; min = min - 1; }
    var span = max - min; min -= span * 0.08; max += span * 0.08;
    var n = pts.length;
    var x = function (i) { return n === 1 ? (padL + (W - padL - padR) / 2) : padL + (W - padL - padR) * i / (n - 1); };
    var y = function (v) { return padT + (H - padT - padB) * (1 - (v - min) / (max - min)); };
    svg.appendChild(el('line', { x1: padL, y1: padT, x2: padL, y2: H - padB, class: 'axis' }));
    svg.appendChild(el('line', { x1: padL, y1: H - padB, x2: W - padR, y2: H - padB, class: 'axis' }));
    // a reference value, such as 100000 for the highest catalog number, is drawn as a dashed line and named
    if (spec.ref != null) {
      svg.appendChild(el('line', { x1: padL, y1: y(spec.ref), x2: W - padR, y2: y(spec.ref), class: 'ref' }));
      if (spec.refLabel) svg.appendChild(el('text', { x: W - padR, y: y(spec.ref) - 7, 'text-anchor': 'end', class: 'lbl' }, spec.refLabel));
    }
    var last = pts[pts.length - 1];
    [min + span * 0.08, max - span * 0.08].forEach(function (v, i) {
      // on the lead chart the latest value is named at its point, so the axis does not repeat it
      if (lead && i === 1 && Math.round(v) === last.v) return;
      svg.appendChild(el('text', { x: padL - 8, y: y(v) + 5, 'text-anchor': 'end', class: 'lbl' }, fmt(Math.round(v))));
    });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(p.v).toFixed(1); }).join(' ');
    if (n > 1) svg.appendChild(el('path', { d: d, class: 'series' }));
    pts.forEach(function (p, i) {
      var c = el('circle', { cx: x(i), cy: y(p.v), r: n > 40 ? 2 : 3.5, class: 'dot' + (p.seed ? ' seed' : '') });
      c.appendChild(el('title', {}, p.date + ': ' + fmt(p.v) + (p.seed ? ' (seed from the corpus)' : '')));
      svg.appendChild(c);
    });
    if (lead) svg.appendChild(el('text', { x: x(n - 1), y: y(last.v) - 12, 'text-anchor': n > 1 ? 'end' : 'middle', class: 'lbl val' }, fmt(last.v)));
    svg.appendChild(el('text', { x: padL, y: H - 8, class: 'lbl' }, pts[0].date));
    if (n > 1) svg.appendChild(el('text', { x: W - padR, y: H - 8, 'text-anchor': 'end', class: 'lbl' }, pts[n - 1].date));
    container.appendChild(svg);
    table(container, pts, spec, function (p) { return fmt(p.v); });
  }

  function boolChart(container, entries, spec) {
    // a day whose fetch failed has no answer: render it as 'no data', never as one of the two answers
    var pts = entries.map(function (e) {
      var ok = spec.okPath ? get(e, spec.okPath) !== false : true;
      return { date: e.date, v: ok ? get(e, spec.path) : null, seed: e.kind === 'seed' };
    });
    var W = widthOf(container), cell = Math.max(6, Math.min(28, Math.floor((W - 20) / Math.max(pts.length, 1)))), H = 64;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': spec.title + ', ' + pts.length + ' days' });
    pts.forEach(function (p, i) {
      // yesClass / noClass: an answer that is a normal state, not a fault, is drawn neutral; red is kept for faults (S-047, S-048)
      var cls = p.v === true ? (spec.yesClass || 'bool-true') : (p.v === false ? (spec.noClass || 'bool-false') : 'bool-null');
      var r = el('rect', { x: 10 + i * cell, y: 8, width: cell - 2, height: 26, rx: 3, class: cls });
      r.appendChild(el('title', {}, p.date + ': ' + (p.v === true ? spec.yes : p.v === false ? spec.no : 'no data')));
      svg.appendChild(r);
    });
    svg.appendChild(el('text', { x: 10, y: 56, class: 'lbl' }, pts.length ? pts[0].date : ''));
    if (pts.length > 1) svg.appendChild(el('text', { x: Math.max(10 + pts.length * cell - 2, 190), y: 56, 'text-anchor': 'end', class: 'lbl' }, pts[pts.length - 1].date));
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
    highest: { kind: 'line', title: 'highest catalog number in the last-30-days group', path: 'metrics.last30.highest', okPath: 'metrics.last30.ok', ref: 100000, refLabel: '100,000: the first six-digit number' },
    six: { kind: 'line', title: 'six-digit objects in the last-30-days group', path: 'metrics.last30.six_digit', okPath: 'metrics.last30.ok', zero: true },
    tle404: { kind: 'bool', title: 'last-30-days TLE request returns 404', path: 'metrics.last30_tle.is_404', okPath: 'metrics.last30_tle.ok', yes: '404 (no TLE)', no: 'TLE data returned', yesClass: 'bool-neutral', noClass: 'bool-true' },
    analystcsv: { kind: 'line', title: 'analyst objects in CSV', path: 'metrics.analyst.records', okPath: 'metrics.analyst.ok', zero: true },
    analysttle: { kind: 'line', title: 'analyst objects in TLE', path: 'metrics.analyst_tle.records', okPath: 'metrics.analyst_tle.ok', zero: true },
    nine: { kind: 'line', title: 'nine-digit ids in the Starlink SupGP feed', path: 'metrics.supgp_starlink.nine_digit', okPath: 'metrics.supgp_starlink.ok', zero: true },
    ninebool: { kind: 'bool', title: 'nine-digit ids present in the Starlink SupGP feed', path: 'metrics.supgp_starlink.nine_digit_present', okPath: 'metrics.supgp_starlink.ok', yes: 'present', no: 'none', noClass: 'bool-neutral' }
  };

  function draw(c, history) {
    var spec = SPECS[c.getAttribute('data-chart')];
    if (!spec) return;
    var open = !!c.querySelector('details[open]');  // a data table the reader opened stays open when the chart is redrawn
    c.textContent = '';
    (spec.kind === 'bool' ? boolChart : lineChart)(c, history, spec, { lead: !!c.closest('.lead') });
    if (open) c.querySelector('details').open = true;
    c.drawnWidth = c.clientWidth;
  }
  function run(history) {
    var charts = Array.prototype.slice.call(document.querySelectorAll('[data-chart]'));
    charts.forEach(function (c) { draw(c, history); });
    if (typeof ResizeObserver !== 'function') return;
    var ro = new ResizeObserver(function (changes) {
      changes.forEach(function (ch) { var c = ch.target; if (Math.abs(c.clientWidth - (c.drawnWidth || 0)) > 1) draw(c, history); });
    });
    charts.forEach(function (c) { ro.observe(c); });
  }
  // loadable from node for tests/charts.test.js; in the browser `module` is undefined and the page code below runs
  if (typeof module === 'object' && module.exports) { module.exports = { SPECS: SPECS, boolChart: boolChart, lineChart: lineChart }; return; }
  var mount = document.querySelector('[data-chart]');
  if (!mount) return;
  fetch('/data/tracker/history.json', { credentials: 'omit' }).then(function (r) { return r.json(); }).then(run).catch(function () {
    document.querySelectorAll('[data-chart]').forEach(function (c) { c.textContent = 'Chart data could not be loaded; the table above still shows the last values.'; });
  });
})();
