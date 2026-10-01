/* The Alpha-5 explorer on the story page: a catalog number the reader drags or types, shown as its five-character
   TLE field, with what the first character stands for, the skipped I and O, and the edges at 99,999, 100,000,
   339,999 and 340,000 (S-071). The encoding is alpha5.js's, the one the Tools page and the vector test use; this file
   only describes and draws. Nothing moves unless the reader moves it. No network. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./alpha5.js'));
  else root.Alpha5Explorer = factory(root.Alpha5);
})(typeof self !== 'undefined' ? self : this, function (A) {
  var CEILING = 339999, MAX = 349999;
  function fmt(n) { return Number(n).toLocaleString('en-US'); }

  // What the reader is shown for n: its field, what the first character stands for, and the edge or skip it sits at.
  function describe(n) {
    if (typeof n !== 'number' || !Number.isInteger(n)) return { zone: 'invalid', message: 'a catalog number is a whole number' };
    if (n < 0) return { zone: 'invalid', n: n, message: 'a negative number cannot be a catalog number' };
    if (n > CEILING) return { zone: 'none', n: n, field: null, edge: n === CEILING + 1 ? 'first-none' : null };
    var field = A.encode(n), lead = Math.floor(n / 10000);
    var d = { zone: n < 100000 ? 'digits' : 'letters', n: n, field: field, head: field.charAt(0), lead: lead, tail: field.slice(1), edge: null, skipped: '' };
    if (n === 99999) d.edge = 'last-digits';
    if (n === 100000) d.edge = 'first-letter';
    if (n === CEILING) d.edge = 'last-field';
    if (d.zone === 'letters') {
      d.counted = d.head.charCodeAt(0) - 55;  // counting on from A = 10 with no letter skipped: I would be 18, J 19
      d.skipped = lead >= 23 ? 'IO' : (lead >= 18 ? 'I' : '');
    }
    return d;
  }

  // The sentence beside the field. It names no digit that changes within a letter, so a screen reader, which hears it
  // through a live region, hears it again only when the reader crosses into another letter or onto an edge.
  function sentence(d) {
    if (d.zone === 'invalid') return (d.what || 'Not a catalog number') + ': ' + d.message + '.';
    if (d.zone === 'none') return 'Above 339,999 there is no letter left, so this number has no TLE form; only the OMM formats carry it, as an integer of up to nine digits.';
    var s = d.zone === 'digits'
      ? 'Below 100,000 the field is the number itself, padded with zeros to five digits.'
      : 'The first two digits, ' + d.lead + ', become one letter, ' + d.head + '; the last four digits stay as they are.';
    if (d.skipped) s += ' Counting on from A = 10, ' + d.head + ' would be ' + d.counted + ', but ' + (d.skipped === 'IO' ? 'I and O are' : 'I is') + ' skipped, so ' + d.head + ' is ' + d.lead + '.';
    if (d.edge === 'last-digits') s += ' 99,999 is the last number five digits can hold.';
    if (d.edge === 'first-letter') s += ' This is the first lettered number: SARAMAGO, catalogued on 11 July 2026.';
    if (d.edge === 'last-field') s += ' Z9999 is the last number with a TLE form.';
    return s;
  }

  // What the slider announces as its value: the number, the field spelt out, and what a letter stands for.
  function valuetext(d) {
    if (d.zone === 'invalid') return 'not a catalog number';
    if (d.zone === 'none') return fmt(d.n) + ', no TLE form';
    return fmt(d.n) + ', written ' + d.field.split('').join(' ') + (d.zone === 'letters' ? ', ' + d.head + ' stands for ' + d.lead : '');
  }

  return { describe: describe, sentence: sentence, valuetext: valuetext, fmt: fmt, CEILING: CEILING, MAX: MAX };
});

/* Story page wiring (browser only): one explorer in each [data-alpha5-explorer], the letter table of the same reading
   level hidden once it exists (the table stays for scripts off), and the scale drawn at its container's own width,
   one SVG unit to one CSS pixel, as the tracker's charts are, so its labels stay at text size. */
(function () {
  if (typeof document === 'undefined' || !window.Alpha5 || !window.Alpha5Explorer) return;
  var X = window.Alpha5Explorer, A = window.Alpha5, NS = 'http://www.w3.org/2000/svg';
  var STOPS = [99999, 100000, 180000, 230000, 339999, 340000];  // the format's edges and the two skips, all from the corpus vectors
  var THUMB = 28;  // the range thumb's width in site.css: the thumb's centre travels from THUMB/2 to width - THUMB/2
  var KEY = { 0: 1, 10: 1, 33: 1 };  // the characters labelled on a narrow scale: 0, A and Z, with the struck I and O
  var built = 0;

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function svg(tag, attrs, text) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }
  function bold(text) { return el('b', {}, text); }
  function fill(node, parts) { node.textContent = ''; parts.forEach(function (p) { node.appendChild(typeof p === 'string' ? document.createTextNode(p) : p); }); }

  document.querySelectorAll('[data-alpha5-explorer]').forEach(build);

  function build(mount) {
    var k = ++built, id = function (s) { return 'a5x' + k + '-' + s; };
    var today = parseInt(mount.getAttribute('data-today'), 10), todayAt = mount.getAttribute('data-today-at') || '';
    var n = 100000, drawnWidth = 0;

    var body = el('div', { class: 'a5x-body' });
    var readout = el('div', { class: 'a5x-readout', 'aria-hidden': 'true' });
    var number = el('p', { class: 'a5x-number' });
    var cells = el('p', { class: 'a5x-cells' });
    var cell = [];
    for (var i = 0; i < 5; i++) { cell.push(el('span', { class: 'a5x-cell' })); cells.appendChild(cell[i]); }
    var legend = el('p', { class: 'a5x-legend' });
    readout.appendChild(number); readout.appendChild(cells); readout.appendChild(legend);

    var scale = el('div', { class: 'a5x-scale' });
    var drawing = svg('svg', { class: 'a5x-svg', 'aria-hidden': 'true', focusable: 'false' });
    var range = el('input', { type: 'range', class: 'a5x-range', id: id('range'), min: '0', max: String(X.MAX), step: '1', value: String(n), 'aria-label': 'Catalog number', 'aria-describedby': id('sentence') });
    scale.appendChild(drawing); scale.appendChild(range);

    var controls = el('div', { class: 'a5x-controls' });
    var field = el('div', { class: 'a5x-field' });
    field.appendChild(el('label', { for: id('text') }, 'Type a number or a five-character field'));
    var text = el('input', { type: 'text', class: 'a5x-text', id: id('text'), inputmode: 'text', autocomplete: 'off', spellcheck: 'false', maxlength: '11', placeholder: '100000 or A0000', 'aria-describedby': id('sentence') });
    field.appendChild(text);
    var stops = el('div', { class: 'a5x-stops', role: 'group', 'aria-label': 'Edges of the format' });
    var stopButtons = STOPS.map(function (s) { var b = el('button', { type: 'button', 'data-n': String(s) }, X.fmt(s)); stops.appendChild(b); return b; });
    controls.appendChild(field); controls.appendChild(stops);

    var said = el('p', { class: 'a5x-sentence', id: id('sentence'), 'aria-live': 'polite' });
    body.appendChild(readout); body.appendChild(scale); body.appendChild(controls); body.appendChild(said);
    mount.textContent = '';
    mount.appendChild(body);

    // the letter table this explorer replaces, in the same reading level, steps aside; with scripts off it is all there is
    var level = mount.closest('.lvl') || document;
    level.querySelectorAll('[data-alpha5-fallback]').forEach(function (t) { t.hidden = true; });

    function x(v, W) { return THUMB / 2 + (W - THUMB) * v / X.MAX; }

    function draw(d) {
      var W = Math.max(280, Math.round(scale.clientWidth || 520)), H = 86, barY = 22, barH = 14;  // the thumb covers y 16 to 42: labels keep clear of it
      var segW = (W - THUMB) / 35, wide = segW >= 18, cur = Math.floor(Math.min(d.zone === 'invalid' ? -1 : d.n, X.MAX) / 10000);
      drawnWidth = W;
      drawing.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
      drawing.textContent = '';
      for (var s = 0; s < 35; s++) {
        var x0 = x(s * 10000, W), x1 = x(Math.min((s + 1) * 10000, X.MAX), W);
        var zone = s < 10 ? 'digits' : (s < 34 ? 'letters' : 'none');
        drawing.appendChild(svg('rect', { x: x0.toFixed(1), y: barY, width: Math.max(0, x1 - x0).toFixed(1), height: barH, class: 'seg ' + zone + (s === cur ? ' cur' : '') }));
        if (s < 34 && (wide || KEY[s])) {
          var ch = s < 10 ? String(s) : A.LETTERS.charAt(s - 10);
          drawing.appendChild(svg('text', { x: ((x0 + x1) / 2).toFixed(1), y: 12, 'text-anchor': 'middle', class: 'lbl ch' + (s === cur && wide ? ' cur' : '') }, ch));
        }
      }
      // I and O: the alphabet skips them, the numbers do not, so they sit struck through on the boundary between neighbours
      [[180000, 'I'], [230000, 'O']].forEach(function (p) {
        var bx = x(p[0], W);
        drawing.appendChild(svg('text', { x: bx.toFixed(1), y: 12, 'text-anchor': 'middle', class: 'lbl ch skip' }, p[1]));
        drawing.appendChild(svg('line', { x1: (bx - 4).toFixed(1), y1: 13, x2: (bx + 4).toFixed(1), y2: 2, class: 'strike' }));
      });
      [100000, 340000].forEach(function (v) { var bx = x(v, W).toFixed(1); drawing.appendChild(svg('line', { x1: bx, y1: barY - 3, x2: bx, y2: barY + barH + 4, class: 'tick' })); });
      drawing.appendChild(svg('text', { x: x(50000, W).toFixed(1), y: 58, 'text-anchor': 'middle', class: 'lbl' }, 'five digits'));
      drawing.appendChild(svg('text', { x: x(220000, W).toFixed(1), y: 58, 'text-anchor': 'middle', class: 'lbl' }, wide ? 'letters A to Z, no I or O' : 'letters'));
      drawing.appendChild(svg('text', { x: W, y: 58, 'text-anchor': 'end', class: 'lbl' }, wide ? 'no TLE form' : 'none'));
      if (!isNaN(today) && today >= 0 && today <= X.MAX) {
        var tx = x(today, W);
        drawing.appendChild(svg('line', { x1: tx.toFixed(1), y1: barY + barH, x2: tx.toFixed(1), y2: 68, class: 'today' }));
        drawing.appendChild(svg('text', { x: tx.toFixed(1), y: 82, 'text-anchor': 'start', class: 'lbl' }, 'today’s highest, ' + X.fmt(today) + (wide && todayAt ? ' (' + todayAt + ')' : '')));
      }
    }

    function render(next, from) {
      n = next;
      var d = typeof n === 'object' ? n : X.describe(n);
      if (d.zone === 'letters' || d.zone === 'digits') {
        var s = X.fmt(d.n), split = d.zone === 'letters' ? 2 : (d.n >= 10000 ? 1 : 0);
        fill(number, split ? [bold(s.slice(0, split)), s.slice(split)] : [s]);
        d.field.split('').forEach(function (c, i) { cell[i].textContent = c; cell[i].className = 'a5x-cell' + (i === 0 ? ' head' : ''); });
        fill(legend, d.zone === 'letters'
          ? [bold(d.head + ' = ' + d.lead), ', the first two digits', el('span', { class: 'sep' }, ' · '), bold(d.tail), ', the last four, as they are']
          : [bold(d.head), ', the first digit', el('span', { class: 'sep' }, ' · '), bold(d.tail), ', the last four']);
      } else {
        fill(number, [d.zone === 'none' ? X.fmt(d.n) : '—']);
        cell.forEach(function (c) { c.textContent = ''; c.className = 'a5x-cell none'; });
        fill(legend, [d.zone === 'none' ? 'no TLE form' : 'not a catalog number']);
      }
      var words = X.sentence(d);
      if (said.textContent !== words) said.textContent = words;
      if (d.zone !== 'invalid') {  // a refused field leaves the slider at the last number it held, and saying so
        if (from !== 'range') range.value = String(Math.min(d.n, X.MAX));
        range.setAttribute('aria-valuetext', X.valuetext(d));
      }
      if (from !== 'text') text.value = d.zone === 'invalid' ? text.value : String(d.n);
      stopButtons.forEach(function (b) { b.setAttribute('aria-current', d.n === parseInt(b.getAttribute('data-n'), 10) ? 'true' : 'false'); });
      draw(d);
    }

    range.addEventListener('input', function () { render(parseInt(range.value, 10), 'range'); });
    range.addEventListener('keydown', function (e) {
      if (e.key !== 'PageUp' && e.key !== 'PageDown') return;
      e.preventDefault();  // one character, exactly 10,000, rather than the browser's own page step
      var v = parseInt(range.value, 10) + (e.key === 'PageUp' ? 10000 : -10000);
      render(Math.max(0, Math.min(X.MAX, v)), 'key');
    });
    text.addEventListener('input', function () {
      var raw = text.value.trim();
      if (!raw) return;
      if (/^-?[0-9]+$/.test(raw)) { render(parseInt(raw, 10), 'text'); return; }
      if (raw.length < 5) return;  // a field still being typed: say nothing until it has its five characters
      try { render(A.decode(raw), 'text'); }
      catch (err) { render({ zone: 'invalid', what: 'Not an Alpha-5 field', message: err.message }, 'text'); }
    });
    stopButtons.forEach(function (b) { b.addEventListener('click', function () { render(parseInt(b.getAttribute('data-n'), 10), 'stop'); }); });
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(function () { if (Math.abs(Math.round(scale.clientWidth) - drawnWidth) > 1) draw(typeof n === 'object' ? n : X.describe(n)); }).observe(scale);
    }
    render(n, 'start');
  }
})();
