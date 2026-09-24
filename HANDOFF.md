# Handoff: how to pick this project up on another computer

For a Claude Code session (or a person) resuming work on the gp-omm-conformance corpus and this site.
Public-safe by design: no provider data, no credentials, no private paths. Updated 2026-09-23.

## Start here

1. Clone the two public repositories: `hneogy/gpconf-site` (this one) and `hneogy/gp-omm-conformance`
   (the corpus, v0.2.1, MIT). Read `DECISIONS.md` in each (site: S-001 onward; corpus: D-001 onward,
   append-only, corrections are new entries) and the corpus's `CLAUDE.md`, which is the decision policy:
   decide technical matters autonomously, log every non-trivial choice, and stop for anything involving
   terms of use, credentials, publishing, contacting people or spending.
2. The corpus's **private build repository** is not on GitHub (it holds raw CelesTrak bytes and the fetch
   logs). It lives in the maintainer's synced folder. Without it you can do everything on the site and on
   upstream matters; refreshing the corpus's fixtures or regenerating its public export needs it.
3. Every public action (push, release, issue, comment, pull request, deploy) needs the maintainer's
   explicit, per-action authorisation. Approval for one action does not carry to the next.

## State on 2026-09-23

| area | state |
|---|---|
| corpus | v0.2.1 released 2026-09-23 (tag v0.2.1 on b1407a5, GitHub release published 21:09:22 UTC): fixes to cases where the corpus reported a pass it had not checked (D-111 to D-119); seventeen cases unchanged, one writer check added; version DOI 10.5281/zenodo.22926017 (Zenodo record 22926017, minted 2026-09-23 21:48 UTC). v0.2.0 published 2026-09-23 (the writer-side case `tle-writer-alpha5` and `gpconf check-tle`); concept DOI 10.5281/zenodo.22867654 (v0.1.0: 10.5281/zenodo.22867655); independent audit in `AUDIT.md` covered v0.1.0 only |
| site | https://github.com/hneogy/gpconf-site, main at a06208b plus the S-032 commit (decisions to S-032), deployed by Cloudflare Pages at https://gpconf.neogy.dev (custom domain attached) and https://gpconf-site.pages.dev; `GITHUB_TOKEN` set (`/api/activity` reports `authenticated: true`); `ci.yml` runs the Python suite, `node --test` and the build on every push |
| site jobs | GitHub Actions: `tracker.yml` daily 06:17 UTC (5 CelesTrak endpoints + at most 4 drift checks, hard cap 10), `library.yml` Mondays 07:23 UTC; since S-024 both validate (tests + build) before committing, keep each run's JSON and log as a 30-day artifact, and rebase before pushing; the run of 2026-09-23 is the first through these gates |
| upstream | python-sgp4 #171 filed by the maintainer of this corpus; fix PR #172 reviewed by the library maintainer on 2026-09-22 with two suggestions; the head was amended to 9e8fc81 and pushed 2026-09-23 (slice suggestion taken, `or ''` kept for the None case, reasons given in the review threads); CI awaits the library maintainer's workflow approval. #169 reported by another user; PR #170 (another contributor's fix) tested against the corpus, report posted on the PR; the maintainer's design question on #170 is unanswered. strf hardening note filed as cbassa/strf#88 on 2026-09-23 |
| fork | https://github.com/hneogy/python-sgp4, branch `omm-empty-object-id` (PR #172's head, 9e8fc81) |
| ecosystem | SatNOGS listed on `/library/` as "in progress" from a maintainer's forum statement of 2026-09-22 (S-025); no other entries yet |

## Open items

- PR #172: wait for the library maintainer's second look and workflow approval; if he prefers the `.get()`
  default after the None argument, switch on the corpus maintainer's word. Post nothing without authorisation.
- PR #170 design question: draft a reply only if asked; post only with authorisation.
- strf #88: wait for a reply; it may settle the corpus's open questions about `rffit`.
- Corpus public repository at v0.2.1 (tag v0.2.1 on b1407a5, CI green); the v0.2.1 version DOI is in `build.py` and on the
  timeline (S-032). The corpus's own DOI slots are filled in the same round (corpus D-123).
- SatNOGS: when support for ids above 99999 lands (Libre Space forum thread 15354), set the entry's status in
  `site/content/ecosystem.json` to "supported" and add a dated timeline event; both need the maintainer's review.
- Tracker run of 2026-09-23: first run through the S-022/S-024 gates; check the workflow run, the artifact and the
  tracker page afterwards.

### Open questions

Claims in DECISIONS.md that are labelled inferred or untested. Verify before building on one; the session
that settles it removes the line here and appends the correcting entry to the log.

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
- Attribution stays exact: #171 "Issue filed by the maintainer of this corpus"; #172 "Fix submitted by the
  maintainer of this corpus"; #170 "Fix by karlhillx, tested against this corpus"; #169 "Reported upstream by
  another user".

## Working conventions

- Site: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; tests
  `.venv/bin/python -m unittest discover -s tests -t .` (28 tests; the JavaScript tests run through `node --test`,
  which the Python suite calls locally and `ci.yml` runs as its own step); build `python build.py`;
  local preview `python3 -m http.server -d dist 8765`; function emulation `npx wrangler pages dev dist --port 8788`.
- Commits are authored by the maintainer and carry a `Co-Authored-By: Claude Fable 5.1` trailer when the
  assistant wrote them. The site's decision log uses S-numbers, the corpus's D-numbers.
- Corpus runner: `python3 -m gpconf run --adapter tests.adapters.reference:Parser` (needs the fixtures fetched
  once with `tools/fetch.py`, under CelesTrak's policy).

## Memory seed for an assistant session

Save these as notes if the session keeps memory:

- **gp-omm-conformance corpus**: v0.2.1 released 2026-09-23 (tag on b1407a5; version DOI 10.5281/zenodo.22926017; v0.2.0's is
  10.5281/zenodo.22906966, concept DOI 10.5281/zenodo.22867654); seventeen cases; decisions to D-121; upstream #171 filed and fixed by PR #172
  (head 9e8fc81, awaiting the maintainer's second look); PR #170 tested and commented; strf note sent as
  cbassa/strf#88; every public action needs fresh authorisation; CelesTrak: each URL once, cache, never loop;
  no Space-Track data ever.
- **CelesTrak usage policy** (gp-data-formats FAQ, updated 2026-03-26): data refreshes at most every 2 h; more
  than 50 HTTP errors in 2 h or ~100 MB/day from one address leads to a firewall entry; never repeat a 403/404;
  use celestrak.org, not .com.
- **gpconf-site**: public repo, Cloudflare Pages at gpconf.neogy.dev, decisions to S-027; tracker daily, library
  weekly, both validating before they commit; Activity function `/api/activity` with hourly edge cache;
  hand-maintained ecosystem list on `/library/`; JavaScript tests through `node --test`.
- **Unverified claims are open questions**: a decision-log entry labelled untested or inferred is an open
  question, not a settled fact; verify before building on it; mark `[untested]`/`[inferred]` inline and list it
  under "Open questions" in the handoff file (rule added 2026-09-23 after two such claims proved false).
