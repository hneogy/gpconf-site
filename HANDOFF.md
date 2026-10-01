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
| site | https://github.com/hneogy/gpconf-site, decisions to S-071, at corpus v0.4.0 since S-057, set as a report since S-061 to S-065, the home page restructured by S-070 (2026-09-28) and the story page's first explorable figure, the Alpha-5 explorer, by S-071 (2026-10-01); deployed by Cloudflare Pages at https://gpconf.neogy.dev (custom domain attached) and https://gpconf-site.pages.dev; `GITHUB_TOKEN` set (`/api/activity` reports `authenticated: true`); `ci.yml` runs the Python suite, `node --test` and the build on every push; the three workflows run on `ubuntu-24.04` (S-054) and on the first Node 24 majors of their actions (S-055) |
| site jobs | GitHub Actions: `tracker.yml` daily 06:17 UTC (5 CelesTrak endpoints + at most 4 drift checks, hard cap 10), `library.yml` Mondays 07:23 UTC; since S-024 both validate (tests + build) before committing, keep each run's JSON and log as a 30-day artifact, and rebase before pushing; both have committed on S-055's actions, the tracker on 2026-09-27 and the library job on 2026-09-28 (S-067) |
| hand-run table | `/library/`: eight libraries run by hand, each at a pinned version. libsgp4 (release v3.0) and astroz (release v0.14.0) against v0.4.0's eighteen cases on 2026-09-27; PyEphem, satellite.js, Gpredict, gods-eye-view, SatDump and tle.js against v0.2.1's seventeen on 2026-09-24, where they stay until each library's second-round report is filed (S-056) |
| upstream | Twelve issues filed by the maintainer of this corpus with ten projects: python-sgp4 #171 (closed by #172), strf #88, Gpredict #426, satellite.js #185, libsgp4 #45, gods-eye-view #751, SatDump #1221 (closed by the reporter on 2026-09-27), tle.js #62, astroz #97, #98 and #102 (fixed, in astroz v0.13.0 and v0.14.0), PyEphem #296; the others open on 2026-09-27, strf #88 without a reply. Pull requests from the maintainer's account: python-sgp4 #172 (merged 2026-09-24, in no release yet; the latest is 2.27), satellite.js #186 (merged 2026-09-26) and #187 (merged 2026-09-28), both in no release yet (the latest is 7.1.0), gods-eye-view #767 (open). Comments: libsgp4 #44 (after its v3.0) and PR #42; python-sgp4 PR #170, another contributor's fix for #169 (another user's report), tested against the corpus; #169 and #170 open |
| forks | the maintainer's forks hold the pull requests' branches: `hneogy/python-sgp4` `omm-empty-object-id` (#172), `hneogy/satellite-js` `fix/json2satrec-epoch-microseconds` (#186) and `feat/alpha5-to-number` (#187), `hneogy/gods-eye-view` `fix/alpha5-norad-id` (#767) |
| ecosystem | `/library/` lists SatNOGS as "in progress" (a maintainer's forum statement of 2026-09-22, S-025) and Gpredict as "not supported" (its maintainer on pull request #412, 2026-07-19) |

## Open items

- The six first-round rows on `/library/`: each moves to its second round only with the entry that links that
  library's second-round report (S-056); never as a tidy-up, with a release, or from the counts in the corpus's
  decision log or recipe READMEs, which stay as they are (a count is not a finding's specifics).
- **Expiring claims (S-070): python-sgp4 #172 and satellite.js #186 and #187 are merged and in no release, and the
  site says so in these lines, each false the day a release carries the fix:**
  - the home page's provenance line "python-sgp4 #172, and satellite.js #186 and #187, all from this project and not
    yet released" (`site/templates/pages/index.html`), which names all three;
  - the hand-run labels for #186 and #187, "awaiting a release" (`site/content/library-runs.json`), which then say
    released, in the shape S-050 and S-051 gave libsgp4 and astroz; the row stays as run until a run of the release
    is published;
  - for #172, the library page's next-step callout ("not in 2.27") and its "What the rows mean" item ("reaches users
    with the next release"), and the findings page's empty-`OBJECT_ID` paragraph ("it reaches users with the
    library's next release"). The timeline's #172 entry is dated and stays as written.

  What makes each false: a python-sgp4 release after 2.27 whose tag contains 8126f77 (#172's merge); a satellite.js
  release after 7.1.0 whose tag contains e5927a1 (#186) or 984c3d1 (#187). Check at the start of a session and before
  any push that touches these pages: `curl -s https://pypi.org/pypi/sgp4/json` (`info.version`) and
  `curl -s https://registry.npmjs.org/satellite.js` (`dist-tags.latest`); for a newer version, whether its tag holds
  the commit, `curl -s https://api.github.com/repos/brandon-rhodes/python-sgp4/compare/8126f77...TAG` (or
  `shashwatak/satellite-js/compare/e5927a1...TAG`, `984c3d1...TAG`): `"status": "ahead"` or `"identical"` means the
  release carries it. The weekly library job records the sgp4 it installed in `data/library/latest.json`
  (`versions.sgp4`), the first sign for #172; nothing in the repository watches npm. No test guards these lines:
  the suite runs offline, and the tracker and library jobs run it before committing their data, so a test that asked
  PyPI or npm would fail on a registry outage and, the day a release lands, block both jobs' commits, the tracker's
  perishable daily counts among them. Updating the lines is a site change with its own S-decision, reviewed first.
- The story page as an explorable explanation (S-071): the Alpha-5 explorer is built; the owner's ranking for the rest
  is the checksum and the letter O second (an editable line whose check digit still passes with an O for a 0, the
  corrupt-input case), then the TLE and OMM anatomy, the epoch, and CelesTrak's 404. Each is proposed before it is
  built: what the reader should understand, what is on screen, the control, the edges, and the scripts-off form.
- SatNOGS: when support for ids above 99999 lands (Libre Space forum thread 15354), set the entry's status in
  `site/content/ecosystem.json` to "supported" and add a dated timeline event; both need the maintainer's review.
- strf #88: wait for a reply; it may settle the corpus's open questions about `rffit`.
- PR #170 design question: draft a reply only if asked; post only with authorisation.

### Open questions

Claims in DECISIONS.md that are labelled inferred or untested. Verify before building on one; the session
that settles it removes the line here and appends the correcting entry to the log.

- S-071 [untested]: what a screen reader speaks on the story page's Alpha-5 explorer. The slider's name, its value
  text ("100,000, written A 0 0 0 0, A stands for 10"), its description and the live region were read from the page;
  no screen reader was run. Settled by VoiceOver (macOS) or NVDA on `/migration/`: focus the slider at 100,000,
  press Page Up once, and note what is spoken, in what order, and whether the sentence is announced once per letter.
- S-064 [untested]: the print rule no longer forces a table's rows and cells into blocks; no print preview was made.
  Settled by a print preview of `/library/` at the Technical level, where the notes band under "Runs by hand" and the
  Behaviours table's detail column should keep their table layout.
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
  `.venv/bin/python -m unittest discover -s tests -t .` (50 tests; the JavaScript tests run through `node --test`,
  which the Python suite calls locally and `ci.yml` runs as its own step); build `python build.py`;
  local preview `python3 -m http.server -d dist 8765`; function emulation `npx wrangler pages dev dist --port 8788`.
  A step passes on its own exit code.
- After a push, compare the pages Cloudflare serves with a local build of the same commit: they match but for the
  "Page built" line and, on the home page, the two `email_off` comments, which Cloudflare removes as it honours them.
  Fetch the static files through the hashed URLs the pages name (S-065): Cloudflare's edge keeps `/static/*` for a
  day and a deploy does not refresh it, so the bare path can serve the previous deploy's file. Request the pages as a
  browser does, with `Accept: text/html`: when Web Analytics is on in the Cloudflare dashboard, Cloudflare adds its
  beacon (`static.cloudflareinsights.com`) only to such requests, and curl's default `Accept: */*` gets the page
  without it. No page may carry it: the About page says there are no outside scripts, and the setting cannot be seen
  from the repository (S-066).
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
  twelve issues filed upstream with ten projects, python-sgp4 #172 and satellite.js #186 and #187 merged; every public action
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
