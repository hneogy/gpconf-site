// Runs the site's client-side Alpha-5 implementation against the corpus vectors. `node tests/alpha5-vectors.test.js`
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
const alpha5 = require(path.join(root, "site/static/js/alpha5.js"));
const v = JSON.parse(fs.readFileSync(path.join(root, "data/vectors/alpha5.json"), "utf8"));
const r = alpha5.selfTest(v);
console.log(JSON.stringify(r.summary));
if (r.failures.length) { console.error(r.failures.slice(0, 10)); process.exit(1); }
