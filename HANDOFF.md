# Handoff: how to pick this project up on another computer

For a Claude Code session (or a person) resuming work on the gp-omm-conformance corpus and this site.
Public-safe by design: no provider data, no credentials, no private paths. Updated 2026-09-28.

## Start here

1. Clone the two public repositories: `hneogy/gpconf-site` (this one) and `hneogy/gp-omm-conformance`
   (the corpus, v0.4.0, MIT; also on PyPI as `gpconf`). Read `DECISIONS.md` in each (site: S-001 onward; corpus:
   D-001 onward, append-only, corrections are new entries) and the corpus's `CLAUDE.md`, which is the decision
   policy: decide technical matters autonomously, log every non-trivial choice, and stop for anything involving
   terms of use, credentials, publishing, contacting people or spending. Its "Outreach text" section governs every
   message to another project.
2. The corpus's **private build repository** is not on GitHub (it holds raw CelesTrak bytes and the fetch
   logs). It lives in the maintainer's synced folder. Without it you can do everything on the site and on
   upstream matters; refreshing the corpus's fixtures or regenerating its public export needs it.
3. Every public action (push, release, issue, comment, pull request, deploy) needs the maintainer's
   explicit, per-action authorisation. Approval for one action does not carry to the next.

## State on 2026-09-27

| area | state |
|---|---|
| corpus | v0.4.0 released 2026-09-27 (tag v0.4.0 on e5fa812, GitHub release "v0.4.0 — corrupt input" published 20:20:09 UTC, `gpconf` 0.4.0 on PyPI, version DOI 10.5281/zenodo.23002261): eighteen cases, the eighteenth, `corrupt-input`, handing a parser one corrupt input between valid records; the naive parser fails 15 and python-sgp4 2.27 fails 8. v0.3.0 released the same day (installable with pip, presets, a GitHub Action, the refusal channel; version DOI 10.5281/zenodo.22986178); v0.2.1 and v0.2.0 on 2026-09-23 (10.5281/zenodo.22926017, 10.5281/zenodo.22906966); concept DOI 10.5281/zenodo.22867654 (v0.1.0: 10.5281/zenodo.22867655); the independent audit in `AUDIT.md` covered v0.1.0 only |
| site | https://github.com/hneogy/gpconf-site, decisions to S-058, at corpus v0.4.0 since S-057; deployed by Cloudflare Pages at https://gpconf.neogy.dev (custom domain attached) and https://gpconf-site.pages.dev; `GITHUB_TOKEN` set (`/api/activity` reports `authenticated: true`); `ci.yml` runs the Python suite, `node --test` and the build on every push; the three workflows run on `ubuntu-24.04` (S-054) and on the first Node 24 majors of their actions (S-055) |
| site jobs | GitHub Actions: `tracker.yml` daily 06:17 UTC (5 CelesTrak endpoints + at most 4 drift checks, hard cap 10), `library.yml` Mondays 07:23 UTC; since S-024 both validate (tests + build) before committing, keep each run's JSON and log as a 30-day artifact, and rebase before pushing; the tracker has committed on S-055's actions (2026-09-27), and the library job's first run on them is Monday 2026-09-28 |
| hand-run table | `/library/`: eight libraries run by hand, each at a pinned version. libsgp4 (release v3.0) and astroz (release v0.14.0) against v0.4.0's eighteen cases on 2026-09-27; PyEphem, satellite.js, Gpredict, gods-eye-view, SatDump and tle.js against v0.2.1's seventeen on 2026-09-24, where they stay until each library's second-round report is filed (S-056) |
| upstream | Twelve issues filed by the maintainer of this corpus with ten projects: python-sgp4 #171 (closed by #172), strf #88, Gpredict #426, satellite.js #185, libsgp4 #45, gods-eye-view #751, SatDump #1221 (closed by the reporter on 2026-09-27), tle.js #62, astroz #97, #98 and #102 (fixed, in astroz v0.13.0 and v0.14.0), PyEphem #296; the others open on 2026-09-27, strf #88 without a reply. Pull requests from the maintainer's account: python-sgp4 #172 (merged 2026-09-24, in no release yet; the latest is 2.27), satellite.js #186 (merged 2026-09-26, in no release yet; the latest is 7.1.0) and #187 (open), gods-eye-view #767 (open). Comments: libsgp4 #44 (after its v3.0) and PR #42; python-sgp4 PR #170, another contributor's fix for #169 (another user's report), tested against the corpus; #169 and #170 open |
| forks | the maintainer's forks hold the pull requests' branches: `hneogy/python-sgp4` `omm-empty-object-id` (#172), `hneogy/satellite-js` `fix/json2satrec-epoch-microseconds` (#186) and `feat/alpha5-to-number` (#187), `hneogy/gods-eye-view` `fix/alpha5-norad-id` (#767) |
| ecosystem | `/library/` lists SatNOGS as "in progress" (a maintainer's forum statement of 2026-09-22, S-025) and Gpredict as "not supported" (its maintainer on pull request #412, 2026-07-19) |

## Open items

- The six first-round rows on `/library/`: each moves to its second round only with the entry that links that
  library's second-round report (S-056); never as a tidy-up, with a release, or from the counts in the corpus's
  decision log or recipe READMEs, which stay as they are (a count is not a finding's specifics).
- python-sgp4 #172 and satellite.js #186 are merged and in no release: when a release carries one, its report
  labels say released, in the shape S-050 and S-051 gave libsgp4 and astroz; the maintainer reviews the change.
- The library job of Monday 2026-09-28, 07:23 UTC, is the first on S-055's actions: check that it commits (see
  the open questions).
- SatNOGS: when support for ids above 99999 lands (Libre Space forum thread 15354), set the entry's status in
  `site/content/ecosystem.json` to "supported" and add a dated timeline event; both need the maintainer's review.
- strf #88: wait for a reply; it may settle the corpus's open questions about `rffit`.
- PR #170 design question: draft a reply only if asked; post only with authorisation.

### Open questions

Claims in DECISIONS.md that are labelled inferred or untested. Verify before building on one; the session
that settles it removes the line here and appends the correcting entry to the log.

- S-055 [inferred]: the library job pushes its commit with the token `actions/checkout@v5` persists, as the
  tracker job did on 2026-09-27. Settled by the job's run of Monday 2026-09-28, 07:23 UTC.
- S-027 [untested]: does the `"type": "module"` declaration carry the activity test's import on Node 20.x
  and 22.0–22.6, before module-syntax detection existed? Only Node 22.23.2 (CI) and 26.5 (local) were run.
  Settled by one `node --test` on those versions (official Docker images, or a one-off matrix run of
  `ci.yml`).
- S-027 [untested]: does `node --test` pass on Node 24, the next LTS line, which CI moves to when Node 22
  reaches end of life? Settled by one `ci.yml` run with `node-version: "24"`.

## Rules that must survive any handoff

- Real data only. Every value traces to a recorded URL, retrieval time and SHA-256. Never invent element sets.
- No Space-Track data anywhere; never run the Space-Track verification tool; never ask for credentials.
- SupGP (supplemental) element values stay out of everything public.
- This site shows counts, yes/no states and timestamps only. Its worked examples are the CCSDS 502.0-B-3
  annex G values and the corpus's published derived SARAMAGO line. Visitors never trigger CelesTrak requests.
- Never run `jobs/tracker.py` more than once per day; each URL once per run; no retries.
- A finding about another project appears here only after it has been reported to that project (the corpus
  `CLAUDE.md`, "Findings about other projects"). The hand-run rows report what the corpus measured; reports found by
  probes written to verify a fix stay off them (S-051 as amended).
- Messages to other projects follow the corpus `CLAUDE.md`'s "Outreach text" section: the one-sentence finding,
  one reproduction, one measured number, in prose; the evidence stays in the corpus. No follow-up that only says a
  finding is still present in a new release when the cited lines are unchanged (corpus D-164).
- Attribution stays exact: #171 "Issue filed by the maintainer of this corpus"; #172 "Fix submitted by the
  maintainer of this corpus"; #170 "Fix by karlhillx, tested against this corpus"; #169 "Reported upstream by
  another user".

## Working conventions

- Site: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; tests
  `.venv/bin/python -m unittest discover -s tests -t .` (49 tests; the JavaScript tests run through `node --test`,
  which the Python suite calls locally and `ci.yml` runs as its own step); build `python build.py`;
  local preview `python3 -m http.server -d dist 8765`; function emulation `npx wrangler pages dev dist --port 8788`.
  A step passes on its own exit code.
- After a push, compare the pages Cloudflare serves with a local build of the same commit: they match but for the
  "Page built" line and, on the home page, the two `email_off` comments, which Cloudflare removes as it honours them.
  Fetch the static files through the hashed URLs the pages name (S-065): Cloudflare's edge keeps `/static/*` for a
  day and a deploy does not refresh it, so the bare path can serve the previous deploy's file.
  Cloudflare's email-address obfuscation is on for the zone and rewrites address-shaped text, `name@v0.4.0` included;
  such text goes between `<!--email_off-->` and `<!--/email_off-->`, and the suite fails on any outside that pair
  (S-058).
- At a corpus release the site takes, under its own S-decision (S-053, S-057): `build.py`'s version and
  version-DOI constants (the DOI once Zenodo mints it), the case counts on the pages, `site/content/failures.json`
  from the tag's `docs/FAILURES.md`, timeline events for the release and its DOI, the release literals in
  `tests/test_site.py`, and this file's state table.
- Commits carry no `Co-Authored-By` trailer (the maintainer's instruction, 2026-09-24); published history is not
  rewritten. The site's decision log uses S-numbers, the corpus's D-numbers.
- Corpus runner: `pip install gpconf`, then `gpconf run --preset reference` runs the 5 cases that need no provider
  data; `gpconf fetch` (once: ~60 requests, 2 s apart, cached, under CelesTrak's policy) lets all eighteen run. From
  a clone: `python3 -m gpconf run --adapter tests.adapters.reference:Parser`, after `tools/fetch.py`.

## Memory seed for an assistant session

Save these as notes if the session keeps memory:

- **gp-omm-conformance corpus**: v0.4.0 released 2026-09-27 (tag on e5fa812; `gpconf` 0.4.0 on PyPI; version DOI
  10.5281/zenodo.23002261, v0.3.0's 10.5281/zenodo.22986178, concept DOI 10.5281/zenodo.22867654); eighteen cases;
  twelve issues filed upstream with ten projects, python-sgp4 #172 and satellite.js #186 merged; every public action
  needs fresh authorisation; CelesTrak: each URL once, cache, never loop; no Space-Track data ever.
- **CelesTrak usage policy** (gp-data-formats FAQ, updated 2026-03-26): data refreshes at most every 2 h; more
  than 50 HTTP errors in 2 h or ~100 MB/day from one address leads to a firewall entry; never repeat a 403/404;
  use celestrak.org, not .com.
- **gpconf-site**: public repo, Cloudflare Pages at gpconf.neogy.dev, decisions to S-058, at corpus v0.4.0 (S-057);
  tracker daily, library weekly, both validating before they commit; Activity function `/api/activity` with hourly
  edge cache; hand-maintained ecosystem list on `/library/`; six hand-run rows held for their reports (S-056);
  address-shaped text inside `<!--email_off-->` (S-058); JavaScript tests through `node --test`.
- **Unverified claims are open questions**: a decision-log entry labelled untested or inferred is an open
  question, not a settled fact; verify before building on it; mark `[untested]`/`[inferred]` inline and list it
  under "Open questions" in the handoff file (rule added 2026-09-23 after two such claims proved false).
- **No `Co-Authored-By` trailer** on any commit in the maintainer's repositories (2026-09-24); old history stays.
- **Held rows, public counts** (S-056): the six first-round rows wait for their reports because this site is the
  surface maintainers read, not because counts are secret; the counts stay in the corpus's log and READMEs, never
  trimmed to match.
- **"The catalog passed 99,999" is accurate** (corpus D-188); only a sentence that makes 99,999 the most the
  five-digit field or range can hold is wrong.
