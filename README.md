# gpconf-site

The public site for the [gp-omm-conformance](https://github.com/hneogy/gp-omm-conformance) corpus:
**https://gpconf.neogy.dev** (Cloudflare Pages). A static site with two reading levels per page, a daily
tracker of derived measurements from CelesTrak, a weekly library-status check, and two client-side tools.

Maintainer: Honorius Neogy (NEOGY LLC). Licence: MIT. Built with AI assistance under human direction;
decisions are logged in [`DECISIONS.md`](DECISIONS.md).

## Data rules (audit these)

1. **Derived measurements only.** The site shows counts, yes/no states, HTTP statuses, byte counts,
   hashes and timestamps. It never displays element sets from CelesTrak, never any SupGP (supplemental)
   values, never any Space-Track data. The tracker job reads only the `NORAD_CAT_ID` column and TLE line
   counts; `tests/test_tracker.py::DailyRun::test_no_element_values_in_outputs` asserts that no element
   value from the test input reaches any output.
2. **Worked examples** use the CCSDS 502.0-B-3 annex G example values (GOES 9, as printed in the standard
   and as rendered into a TLE by the corpus renderer) and the derived Alpha-5 line already published in the
   public corpus (`derived/alpha5-tle/alpha5-A-100000-saramago-first.tle`). See `site/content/examples.json`.
3. **Visitors never trigger requests to CelesTrak.** Scheduled GitHub Actions jobs fetch; they commit
   computed JSON to `data/`; the pages are rendered from that JSON at build time and the browser fetches
   only same-origin files. The Content-Security-Policy in `dist/_headers` forbids any other connection.
4. **Fetch etiquette.** At most 10 CelesTrak requests per day (5 daily endpoints + at most 4 weekly drift
   checks), each URL once per run, a User-Agent naming the project and the site URL, no redirects, no
   retries, 2 s between requests. Enforced in `jobs/common.py` (`Fetcher`: a repeated URL or the 11th
   request raises before anything is sent) and tested. One run per day (`.github/workflows/tracker.yml`).
5. **Space-Track guard.** `.gitignore` refuses any Space-Track-named path, as the corpus does.

CelesTrak's policy (https://celestrak.org/NORAD/documentation/gp-data-formats.php, FAQ addendum updated
2026-03-26): data refreshes at most every 2 hours; more than 50 HTTP errors in 2 hours, or more than about
100 MB per day from one address, leads to a firewall entry; never repeat a 403 or 404. The tracker's daily
volume is a few hundred kilobytes and at most one expected 404.

## Layout

| path | what |
|---|---|
| `build.py` | renders `site/templates/pages/*.html` (Jinja2) with the data in `data/` into `dist/`; copies `site/static/` and the JSON; writes `_headers`, `robots.txt`, `sitemap.xml` |
| `site/templates/` | `base.html` (header, nav, level and theme toggles, footer) and the seven pages plus `404.html`; every content page has `.lvl-simple` and `.lvl-technical` blocks |
| `site/static/` | `css/site.css` (light/dark, system fonts), `js/theme.js` (pre-paint level/theme), `js/site.js` (toggles), `js/charts.js` (SVG history charts), `js/alpha5.js` (strict encoder/decoder + self-test), `js/tle.js` (TLE anatomy and paste box) |
| `site/content/` | `examples.json` (the two worked examples with provenance), `failures.json` (the three-parser table from the corpus's FAILURES.md) |
| `jobs/common.py` | the `Fetcher` with the policy guards; JSON helpers |
| `jobs/tracker.py` | daily job: 5 endpoints + drift rotation → `data/tracker/{history,latest,drift}.json` |
| `jobs/library_status.py` | weekly job: reproducers and Alpha-5 vectors against installed python-sgp4/Skyfield → `data/library/{latest,history}.json` |
| `jobs/sources.json` | the URLs, the policy constants, and the 22 stable sources with the corpus manifest's SHA-256s |
| `data/vectors/` | `alpha5.json` vendored from corpus v0.1.0 with `PROVENANCE.md` |
| `tests/` | policy, measurement, drift, output and build-contract tests; a node test for the JavaScript Alpha-5 module |
| `.github/workflows/` | `tracker.yml` (daily 06:17 UTC), `library.yml` (Mondays 07:23 UTC), `ci.yml` (tests and build on push) |
| `functions/api/activity.js` | Cloudflare Pages Function serving `/api/activity` (see below) |
| `data/timeline.json` | hand-maintained project milestones shown on the Activity page; every entry links to a public record |
| `wrangler.toml` | Pages configuration for `wrangler pages dev` and for the connected project |

## Tracker metrics

Daily: highest catalog number and six-digit count in the `last-30-days` CSV; whether the same group's
TLE request returns HTTP 404 (and the record count when it does not); analyst group CSV record count,
six-digit count and TLE record count, with the relation "TLE records = CSV records below 100000"; whether
nine-digit ids are present in the Starlink SupGP CSV and how many. Weekly, rotated at ≤4 per day: SHA-256
match/drift for each of the corpus's 22 stable `gp-first.php` sources. History is seeded with the corpus's
published counts of 2026-09-21 (marked `kind: seed`). A failed fetch marks the measurement `ok: false`; the
run is `partial`; `latest.json` carries the last successful value per measurement with its timestamp.

## Activity page and the `/api/activity` function

The Activity page shows four upstream items (brandon-rhodes/python-sgp4 issues #169 and #171, pull
requests #170 and #172), the corpus repository's latest release and last push, this site's repository, and
a hand-maintained timeline. Sources are public only; the page shows state, dates, counts and links and
never copies titles, bodies or comment text (the function does not read them into its output; a test
asserts it). Attributions are fixed text in the template.

`functions/api/activity.js` runs as a Cloudflare Pages Function. On a cache miss it makes seven GitHub
REST calls, stores the result in the edge cache for one hour (`FRESH_SECONDS`) and a "last good" copy for
30 days, and serves the cached copy to every visitor, so GitHub sees about one refresh per hour per edge
location (the Cache API is per location; worldwide that is a handful of refreshes an hour, far below the
API limits). If GitHub fails, the last good copy is served with its original `generated_at`, `stale: true`
and a reason; if none exists the function answers 503 and the page falls back to its static links.
Responses carry `x-gpconf-cache: HIT|MISS|STALE|NONE`.

**Secret:** `GITHUB_TOKEN`, read from the environment (`env.GITHUB_TOKEN`), never committed and never
echoed. Create a GitHub fine-grained personal access token with *Repository access: Public repositories
(read-only)* and no additional permissions (the default read-only metadata access is enough for public
issues, pull requests, releases and repositories). Store it in Cloudflare Pages as an encrypted
environment variable named `GITHUB_TOKEN` (Settings → Environment variables, Production and Preview), or
with `wrangler pages secret put GITHUB_TOKEN`. Without a token the function still works within GitHub's
unauthenticated limit of 60 requests per hour per address.

Local test, emulating the function with wrangler (optional `.dev.vars` from `.dev.vars.example`):

```bash
python3 build.py && npx wrangler pages dev dist --port 8788
curl -s -D - http://127.0.0.1:8788/api/activity | sed -n '1,12p'
```

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -v      # no network
.venv/bin/python build.py && python3 -m http.server -d dist 8080
```

The jobs (network: the tracker makes at most 9 CelesTrak requests; do not run it more than once per day):

```bash
python3 jobs/tracker.py --cache-dir .cache/tracker      # cache is git-ignored; inspect, then delete
python3 -m venv venv-lib && venv-lib/bin/pip install --upgrade sgp4 skyfield && venv-lib/bin/python jobs/library_status.py
```

## Deploy (owner's steps, not yet done)

1. Create the GitHub repository and push. Actions need `contents: write` for the two data-committing
   workflows (repository setting "Workflow permissions: read and write").
2. Cloudflare Pages → connect the repository; build command `pip install -r requirements.txt && python build.py`;
   output directory `dist`; `.python-version` selects Python 3.13 on the v3 build image.
3. Custom domain `gpconf.neogy.dev` (the zone is already on Cloudflare).

## Accessibility and performance

Semantic landmarks, skip link, visible focus, `aria-pressed` toggles, an `aria-live` announcement on level
change, charts with `role="img"` labels and data tables, tables that scroll rather than overflow on phones,
`prefers-color-scheme` plus a manual theme, `prefers-reduced-motion` respected. No web fonts, no images
beyond an SVG favicon, no third-party requests; the largest page is the tools page at well under 100 KB.
