/* Strict Alpha-5 encoder/decoder per Space-Track's definition (A=10 … Z=33, I and O skipped, capitals only,
   ceiling 339999). Loadable from node for the vector test and from the tools page. No network. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.Alpha5 = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  var LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  function encode(n) {
    if (typeof n !== 'number' || !Number.isInteger(n)) throw new Error('the catalog number must be an integer');
    if (n < 0) throw new Error('a negative number cannot be a catalog number');
    if (n > 339999) throw new Error('above the Alpha-5 ceiling of 339999: this number has no TLE form at all');
    if (n < 100000) return String(n).padStart(5, '0');
    return LETTERS[Math.floor(n / 10000) - 10] + String(n % 10000).padStart(4, '0');
  }
  function decode(field) {
    if (typeof field !== 'string') throw new Error('the field must be text');
    if (field.length !== 5) throw new Error('the field must be exactly five characters (got ' + field.length + ')');
    var head = field.charAt(0), tail = field.slice(1);
    if (!/^[0-9]{4}$/.test(tail)) throw new Error('characters 2 to 5 must be digits');
    if (/^[0-9]$/.test(head)) return parseInt(field, 10);
    if (head === 'I' || head === 'O') throw new Error('the letter ' + head + ' is never used in Alpha-5 (it looks like a digit)');
    var idx = LETTERS.indexOf(head);
    if (idx < 0) {
      if (/^[a-z]$/.test(head)) throw new Error('lowercase letters are not defined; Alpha-5 uses capital letters only');
      throw new Error('the first character must be a digit or a capital letter A to Z, not I or O');
    }
    return (idx + 10) * 10000 + parseInt(tail, 10);
  }
  function selfTest(v) {
    var failures = [], passed = 0;
    var valid = [].concat(v.official_examples, v.boundaries, v.skip_boundaries, v.below_100000);
    valid.forEach(function (c) {
      try { var e = encode(c.norad_cat_id); if (e === c.field) passed++; else failures.push({ kind: 'encode', input: c.norad_cat_id, got: e, want: c.field }); }
      catch (err) { failures.push({ kind: 'encode', input: c.norad_cat_id, error: err.message }); }
      try { var d = decode(c.field); if (d === c.norad_cat_id) passed++; else failures.push({ kind: 'decode', input: c.field, got: d, want: c.norad_cat_id }); }
      catch (err2) { failures.push({ kind: 'decode', input: c.field, error: err2.message }); }
    });
    v.decode_invalid.forEach(function (c) { try { failures.push({ kind: 'invalid field accepted', input: c.field, got: decode(c.field) }); } catch (e) { passed++; } });
    v.encode_unrepresentable.forEach(function (c) { try { failures.push({ kind: 'unrepresentable number accepted', input: c.norad_cat_id, got: encode(c.norad_cat_id) }); } catch (e) { passed++; } });
    return { summary: { passed: passed, failed: failures.length, valid_vectors: valid.length, invalid_fields: v.decode_invalid.length, unrepresentable: v.encode_unrepresentable.length }, failures: failures };
  }
  var table = LETTERS.split('').map(function (L, i) { return { letter: L, value: i + 10, from: (i + 10) * 10000, to: (i + 10) * 10000 + 9999 }; });
  return { encode: encode, decode: decode, selfTest: selfTest, table: table, LETTERS: LETTERS };
});

/* Tools page wiring (browser only). Reads the vectors from an inline JSON data block; sends nothing anywhere. */
(function () {
  if (typeof document === 'undefined') return;
  var input = document.getElementById('a5-input');
  if (!input) return;
  var A = window.Alpha5, out = document.getElementById('a5-result');
  function show(html, cls) { out.className = 'result ' + (cls || ''); out.innerHTML = html; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function run() {
    var raw = input.value.trim();
    if (!raw) { show('', ''); return; }
    var parts = [];
    if (/^[0-9]+$/.test(raw)) {
      var n = parseInt(raw, 10);
      try { var f = A.encode(n); parts.push('<p><strong>' + n.toLocaleString('en-US') + '</strong> as a TLE catalog field: <code>' + esc(f) + '</code>' + (n >= 100000 ? ' (Alpha-5: the letter ' + f.charAt(0) + ' stands for ' + Math.floor(n / 10000) + ')' : ' (five digits, unchanged)') + '.</p>'); }
      catch (e) { parts.push('<p><strong>' + n.toLocaleString('en-US') + '</strong> cannot be encoded: ' + esc(e.message) + '. It can only be carried by the OMM formats.</p>'); }
      if (raw.length === 5) { try { parts.push('<p>Read as a five-character field, <code>' + esc(raw) + '</code> decodes to <strong>' + A.decode(raw).toLocaleString('en-US') + '</strong>.</p>'); } catch (e2) { /* covered above */ } }
      show(parts.join(''), 'ok');
    } else {
      try { var v = A.decode(raw); show('<p>Field <code>' + esc(raw) + '</code> decodes to catalog number <strong>' + v.toLocaleString('en-US') + '</strong>' + (/^[A-Z]/.test(raw) ? ' (letter ' + raw.charAt(0) + ' = ' + Math.floor(v / 10000) + ')' : '') + '.</p>', 'ok'); }
      catch (e3) { show('<p>Rejected: ' + esc(e3.message) + '.</p>', 'bad'); }
    }
  }
  input.addEventListener('input', run);
  document.querySelectorAll('[data-a5-example]').forEach(function (b) { b.addEventListener('click', function () { input.value = b.getAttribute('data-a5-example'); run(); input.focus(); }); });
  var tbl = document.getElementById('a5-table');
  if (tbl) { tbl.innerHTML = A.table.map(function (r) { return '<tr><td><code>' + r.letter + '</code></td><td class="num">' + r.value + '</td><td class="num">' + r.from.toLocaleString('en-US') + ' – ' + r.to.toLocaleString('en-US') + '</td></tr>'; }).join(''); }
  var btn = document.getElementById('a5-selftest'), res = document.getElementById('a5-selftest-result'), data = document.getElementById('alpha5-vectors');
  if (btn && data) btn.addEventListener('click', function () {
    var r = A.selfTest(JSON.parse(data.textContent)), s = r.summary;
    res.className = 'result ' + (s.failed ? 'bad' : 'ok');
    res.textContent = (s.failed ? 'FAILED: ' : 'All vectors pass: ') + s.passed + ' checks passed, ' + s.failed + ' failed (' + s.valid_vectors + ' valid vectors encoded and decoded, ' + s.invalid_fields + ' invalid fields rejected, ' + s.unrepresentable + ' unrepresentable numbers rejected).';
  });
})();
