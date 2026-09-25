// Renders the tracker charts against a three-day history with a stub document: a day whose fetch failed draws the
// 'no data' cell and table row, never one of the two answers, and never a point on a line chart (S-023, S-026).
// `node --test` from the repository root, or `node tests/charts.test.js`.
const assert = require("node:assert/strict");
const path = require("path");
function node(name) {
  return { name, attrs: {}, children: [], _t: "",
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(c) { this.children.push(c); return c; },
    set textContent(t) { this._t = String(t); }, get textContent() { return this._t; },
    set innerHTML(h) { this._h = h; } };
}
global.document = { createElementNS: (ns, n) => node(n), createElement: (n) => node(n) };
const charts = require(path.join(__dirname, "..", "site/static/js/charts.js"));

const history = [
  { date: "2026-09-20", kind: "seed", metrics: { last30_tle: { ok: true, is_404: true }, supgp_starlink: { ok: true, nine_digit_present: false, nine_digit: 0 }, last30: { ok: true, highest: 100700 } } },
  { date: "2026-09-21", metrics: { last30_tle: { ok: true, is_404: false }, supgp_starlink: { ok: true, nine_digit_present: true, nine_digit: 5 }, last30: { ok: true, highest: 100789 } } },
  // the 2026-09-22 shape: HTTP 500, ok false, is_404 false (a 500 is not "TLE data returned")
  { date: "2026-09-22", status: "failed", metrics: { last30_tle: { ok: false, is_404: false, status: 500 }, supgp_starlink: { ok: false, nine_digit_present: false }, last30: { ok: false, highest: null } } },
];

for (const key of Object.keys(charts.SPECS)) assert.ok(charts.SPECS[key].okPath, key + " carries an okPath");

const expected = { tle404: ["bool-neutral", "bool-true", "bool-null"],  // a 404 is CelesTrak declining, a normal state: slate; data returned: green (S-048)
  ninebool: ["bool-neutral", "bool-true", "bool-null"] };  // no nine-digit ids is a normal state, drawn neutral, never red (S-047)
for (const key of Object.keys(expected)) {
  const c = node("div");
  charts.boolChart(c, history, charts.SPECS[key]);
  const rects = c.children[0].children.filter((e) => e.name === "rect");
  assert.deepEqual(rects.map((r) => r.attrs.class), expected[key], key + " cells");
  assert.equal(rects[2].children[0].textContent, "2026-09-22: no data", key + " tooltip");
  const rows = c.children[1].children[1].children[1].children;  // container > details > table > tbody > rows, newest first
  assert.equal(rows[0].children[1].textContent, "no data", key + " table cell for the failed day");
  assert.equal(rows.length, 3, key + " table rows");
}

const line = node("div");
charts.lineChart(line, history, charts.SPECS.highest);
assert.equal(line.children[0].children.filter((e) => e.name === "circle").length, 2, "the failed day is not a point on the line chart");
console.log(JSON.stringify({ ok: true, specs: Object.keys(charts.SPECS).length, days: history.length }));
