# Handoff: how to pick this project up on another computer

For a Claude Code session (or a person) resuming work on the gp-omm-conformance corpus and this site.
Public-safe by design: no provider data, no credentials, no private paths. Updated 2026-09-21.

## Start here

1. Clone the two public repositories: `hneogy/gpconf-site` (this one) and `hneogy/gp-omm-conformance`
   (the corpus, v0.1.0, MIT). Read `DECISIONS.md` in each (site: S-001 onward; corpus: D-001 onward,
   append-only, corrections are new entries) and the corpus's `CLAUDE.md`, which is the decision policy:
   decide technical matters autonomously, log every non-trivial choice, and stop for anything involving
   terms of use, credentials, publishing, contacting people or spending.
2. The corpus's **private build repository** is not on GitHub (it holds raw CelesTrak bytes and the fetch
   logs). It lives in the maintainer's synced folder. Without it you can do everything on the site and on
   upstream matters; refreshing the corpus's fixtures or regenerating its public export needs it.
3. Every public action (push, release, issue, comment, pull request, deploy) needs the maintainer's
   explicit, per-action authorisation. Approval for one action does not carry to the next.

## State on 2026-09-21

| area | state |
|---|---|
| corpus | v0.1.0 published; concept DOI 10.5281/zenodo.22867654, version DOI 10.5281/zenodo.22867655; independent audit in `AUDIT.md` |
| site | https://github.com/hneogy/gpconf-site, deployed by Cloudflare Pages at https://gpconf-site.pages.dev; custom domain gpconf.neogy.dev not yet attached; `GITHUB_TOKEN` secret not yet set (`/api/activity` reports `authenticated: false`) |
| site jobs | GitHub Actions: `tracker.yml` daily 06:17 UTC (5 CelesTrak endpoints + at most 4 drift checks, hard cap 10), `library.yml` Mondays 07:23 UTC, `ci.yml` on push; workflow permissions set to write so the jobs can commit their JSON |
| upstream | python-sgp4 #171 filed by the maintainer of this corpus; fix PR #172 opened at the library maintainer's invitation, awaiting review. #169 reported by another user; PR #170 (another contributor's fix) tested against the corpus, report posted on the PR. The library maintainer asked on #170 how large catalog numbers should be stored and what `.satnum_str` is used for; no reply has been drafted |
| fork | https://github.com/hneogy/python-sgp4, branch `omm-empty-object-id` (PR #172's head) |

## Open items

- Maintainer's Cloudflare steps: attach the custom domain to the Pages project; add `GITHUB_TOKEN`
  (fine-grained, public repositories read-only, created and pasted by the maintainer, never through a
  session) and redeploy; then confirm `https://gpconf.neogy.dev/api/activity` shows `"authenticated": true`.
- PR #172: wait for review; respond only with authorisation.
- PR #170 design question: draft a reply only if asked; post only with authorisation.
- Corpus public export: the private README's "Upstream" section and updated upstream drafts are not yet in
  the public repository; that refresh needs the private build repository and a fresh authorisation to push.

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
  `.venv/bin/python -m unittest discover -s tests -t .` (23 tests, node needed for two); build `python build.py`;
  local preview `python3 -m http.server -d dist 8765`; function emulation `npx wrangler pages dev dist --port 8788`.
- Commits are authored by the maintainer and carry a `Co-Authored-By: Claude Fable 5.1` trailer when the
  assistant wrote them. The site's decision log uses S-numbers, the corpus's D-numbers.
- Corpus runner: `python3 -m gpconf run --adapter tests.adapters.reference:Parser` (needs the fixtures fetched
  once with `tools/fetch.py`, under CelesTrak's policy).

## Memory seed for an assistant session

Save these as three notes if the session keeps memory:

- **gp-omm-conformance corpus**: published v0.1.0 with DOIs; decisions to D-094; upstream #171 filed and fixed by
  PR #172 (awaiting review); PR #170 tested and commented; every public action needs fresh authorisation;
  CelesTrak: each URL once, cache, never loop; no Space-Track data ever.
- **CelesTrak usage policy** (gp-data-formats FAQ, updated 2026-03-26): data refreshes at most every 2 h; more
  than 50 HTTP errors in 2 h or ~100 MB/day from one address leads to a firewall entry; never repeat a 403/404;
  use celestrak.org, not .com.
- **gpconf-site**: public repo, Cloudflare Pages, decisions to S-017; tracker daily, library weekly; Activity
  function `/api/activity` with hourly edge cache; custom domain and `GITHUB_TOKEN` are the maintainer's steps.
