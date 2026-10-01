// The story page's Alpha-5 explorer (S-071) describes a number with the Tools page's own encoder. Every corpus vector must
// come out as the vectors say, the edges and the two skips must be named, and the sentence a screen reader hears through
// the live region must not change inside a letter. `node --test` from the repository root, or `node tests/alpha5-explorer.test.js`.
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const X = require(path.join(root, "site/static/js/alpha5-explorer.js"));
const v = JSON.parse(fs.readFileSync(path.join(root, "data/vectors/alpha5.json"), "utf8"));

const valid = [].concat(v.official_examples, v.boundaries, v.skip_boundaries, v.below_100000);
for (const c of valid) {
  const d = X.describe(c.norad_cat_id);
  assert.equal(d.field, c.field, `${c.norad_cat_id} is written ${c.field}`);
  assert.equal(d.zone, c.norad_cat_id < 100000 ? "digits" : "letters", `${c.norad_cat_id} zone`);
  assert.equal(d.lead, Math.floor(c.norad_cat_id / 10000), `${c.norad_cat_id}: what the first character stands for`);
  assert.equal(d.head + d.tail, c.field);
}
for (const c of v.encode_unrepresentable) {
  const d = X.describe(c.norad_cat_id);
  assert.ok(d.zone === "none" || d.zone === "invalid", `${c.norad_cat_id} has no field`);
  assert.equal(d.field == null, true);
}

// the four edges the page names, and the two places the alphabet skips a letter
assert.equal(X.describe(99999).edge, "last-digits");
assert.equal(X.describe(100000).edge, "first-letter");
assert.equal(X.describe(339999).edge, "last-field");
assert.deepEqual([X.describe(340000).zone, X.describe(340000).edge], ["none", "first-none"]);
assert.deepEqual([X.describe(179999).head, X.describe(179999).skipped], ["H", ""]);
assert.deepEqual([X.describe(180000).head, X.describe(180000).lead, X.describe(180000).skipped], ["J", 18, "I"]);
assert.deepEqual([X.describe(229999).head, X.describe(229999).skipped], ["N", "I"]);
assert.deepEqual([X.describe(230000).head, X.describe(230000).lead, X.describe(230000).skipped], ["P", 23, "IO"]);
assert.match(X.sentence(X.describe(100000)), /The first two digits, 10, become one letter, A; the last four digits stay as they are\./);
assert.match(X.sentence(X.describe(100000)), /SARAMAGO/);
assert.match(X.sentence(X.describe(180000)), /J would be 19, but I is skipped, so J is 18\./);
assert.match(X.sentence(X.describe(230000)), /P would be 25, but I and O are skipped, so P is 23\./);
assert.match(X.sentence(X.describe(339999)), /Z9999 is the last number with a TLE form\./);
assert.match(X.sentence(X.describe(340000)), /no TLE form/);
assert.match(X.sentence(X.describe(25544)), /^Below 100,000 the field is the number itself/);

// what the slider announces
assert.equal(X.valuetext(X.describe(100000)), "100,000, written A 0 0 0 0, A stands for 10");
assert.equal(X.valuetext(X.describe(25544)), "25,544, written 2 5 5 4 4");
assert.equal(X.valuetext(X.describe(340000)), "340,000, no TLE form");

// the live region's sentence is the same for every number inside a letter and inside the no-field zone,
// so a screen reader is not read a new sentence at every step of the slider
assert.equal(X.sentence(X.describe(181234)), X.sentence(X.describe(189998)));
assert.equal(X.sentence(X.describe(340001)), X.sentence(X.describe(349999)));
assert.notEqual(X.sentence(X.describe(179999)), X.sentence(X.describe(180000)));

console.log(JSON.stringify({ ok: true, vectors: valid.length, unrepresentable: v.encode_unrepresentable.length }));
