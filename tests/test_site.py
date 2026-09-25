"""Build the site into a temporary directory and check the page contract: every page has both
reading levels, no external script/style/font, no inline event handlers, and the tools are
client-side only. Also runs the JavaScript tests through `node --test` when node is available and not in CI."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PAGES = ["index.html", "migration/index.html", "findings/index.html", "tracker/index.html",
         "library/index.html", "tools/index.html", "about/index.html", "activity/index.html", "404.html"]


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build
        cls.tmp = tempfile.mkdtemp()
        build.main(Path(cls.tmp))
        cls.pages = {p: (Path(cls.tmp) / p).read_text(encoding="utf-8") for p in PAGES}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_pages_exist_with_both_levels(self):
        for name, html in self.pages.items():
            if name == "404.html":
                continue
            self.assertIn('class="lvl lvl-simple', html, name)
            self.assertIn('class="lvl lvl-technical', html, name)
            self.assertIn('id="level-toggle"', html, name)
            self.assertIn("<main", html, name)
            self.assertIn('class="skip-link"', html, name)

    def test_library_runs_are_complete_and_rendered(self):
        """Every hand-run row names a version, a date and at least one filed report; every row links a filed
        report (corpus D-134 convention: nothing unreported on the page); the page renders every row and both provenance sentences."""
        from markupsafe import escape
        runs = json.loads((ROOT / "site" / "content" / "library-runs.json").read_text(encoding="utf-8"))
        html = self.pages["library/index.html"]
        self.assertGreaterEqual(len(runs["runs"]), 8)
        self.assertIn("PyEphem", [r["library"] for r in runs["runs"]], "PyEphem joined the table when its report was filed (2026-09-25)")
        for r in runs["runs"]:
            for key in ("library", "project_url", "version", "version_detail", "run_date", "reads", "failed", "breakdown", "finding", "reports"):
                self.assertTrue(r.get(key), f"{r.get('library')}: {key}")
            self.assertRegex(r["run_date"], r"^\d{4}-\d{2}-\d{2}$", r["library"])
            self.assertTrue(r["project_url"].startswith("https://"), r["library"])
            for u in r["reports"]:
                self.assertTrue(u["url"].startswith("https://") or u["url"].startswith("#"), f"{r['library']}: {u}")
                self.assertIn(u["url"], html, f"{r['library']}: report link not rendered")
            self.assertIn(str(escape(r["finding"])), html, r["library"])  # the template autoescapes, e.g. the apostrophe in "master's"
            self.assertTrue(r.get("gate", {}).get("short") and r["gate"].get("full"), f"{r['library']}: gate column (D-142)")
            self.assertIn("snapshot 2026-09-21", r["gate"]["full"], r["library"])
            self.assertIn(str(escape(r["gate"]["full"])), html, r["library"])
            for word in ("LOADS", "PARTLY", "verdict"):
                self.assertNotIn(word, r["gate"]["short"] + r["gate"]["full"], r["library"])
            self.assertIn(str(escape(r["failed"])), html, r["library"])
        self.assertIn("not a verdict on the project", html)
        self.assertIn("The counts do not rank the libraries", html)
        self.assertIn("reproduced on the library", html)
        self.assertIn("so their users are not affected today", html)
        self.assertIn("HTTP 404", html)
        self.assertIn("Refused and dropped are not distinguished for these eight runs", html)  # corpus D-144 footnote
        # Pull requests carry their state and date in the label, in the python-sgp4 row's shape (S-044).
        for r in runs["runs"]:
            for u in r["reports"]:
                if u["label"].startswith("PR #"):
                    self.assertRegex(u["label"], r"^PR #\d+ \((open|merged|closed) \d{4}-\d{2}-\d{2}; [^)]+\)$", f"{r['library']}: {u['label']}")
        for url in ("https://github.com/shashwatak/satellite-js/pull/186", "https://github.com/shashwatak/satellite-js/pull/187",
                    "https://github.com/bilawalsidhu/gods-eye-view/pull/767"):
            self.assertIn(url, html)

    def test_no_external_resources(self):
        for name, html in self.pages.items():
            for m in re.finditer(r'<(script|link|img|iframe)\b[^>]*>', html):
                tag = m.group(0)
                if 'rel="canonical"' in tag:
                    continue  # the canonical URL names this site itself; it loads nothing
                self.assertNotRegex(tag, r'(src|href)="https?://', f"{name}: {tag}")
            self.assertNotRegex(html, r'\son[a-z]+="', name)
            self.assertNotIn("<style", html, name)
            self.assertNotIn(' style="', html, name)

    def test_headers_and_robots(self):
        headers = (Path(self.tmp) / "_headers").read_text()
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("connect-src 'self'", headers)
        self.assertIn("form-action 'none'", headers)
        self.assertTrue((Path(self.tmp) / "robots.txt").exists())
        self.assertTrue((Path(self.tmp) / "data/tracker/latest.json").exists())
        self.assertTrue((Path(self.tmp) / "data/vectors/alpha5.json").exists())

    def test_tools_scripts_do_not_fetch_or_post(self):
        for js in ("tle.js", "alpha5.js"):
            text = (ROOT / "site/static/js" / js).read_text()
            self.assertNotIn("fetch(", text, js)
            self.assertNotIn("XMLHttpRequest", text, js)
            self.assertNotIn("sendBeacon", text, js)
            self.assertNotIn("WebSocket", text, js)

    def test_no_forbidden_values_in_pages(self):
        # SupGP element values are never on the site; the only CelesTrak-derived lines are the published
        # derived Alpha-5 example (SARAMAGO first record) and the CCSDS annex G rendering.
        for name, html in self.pages.items():
            self.assertNotIn("space-track.org/basicspacedata", html.lower(), name)


class FailedDayRendering(unittest.TestCase):
    """A tracker day whose fetches failed has no numbers in its metrics (the 2026-09-22 run: nine HTTP 500s
    from CelesTrak); the page must render it as a marked row with dashes, never crash the build."""

    def test_helpers_treat_undefined_as_missing(self):
        import build
        from jinja2 import Undefined
        self.assertEqual(build.fmt_int(Undefined(name="highest")), "—")
        self.assertEqual(build.yesno(Undefined(name="is_404")), "unknown")
        self.assertEqual(build.fmt_int(None), "—")
        self.assertEqual(build.fmt_int(100789), "100,789")

    def test_failed_day_is_marked_in_the_history_table(self):
        import build
        import json
        history = json.loads((ROOT / "data" / "tracker" / "history.json").read_text())
        failed = [e for e in history if e.get("status") and e["status"] != "ok"]
        if not failed:
            self.skipTest("no failed day in the tracker history")
        tmp = tempfile.mkdtemp()
        build.main(Path(tmp))
        html = (Path(tmp) / "tracker" / "index.html").read_text()
        for e in failed:
            self.assertIn(f"{e['date']} ({e['status']})", html)
            # the noscript table: every column of a failed day is a dash, and the TLE-404 cell is never a "no"
            # (is_404 is False on a 500, which is not "TLE data returned")
            row = re.search(rf"<tr><td>{e['date']} \({e['status']}\)</td>(.*?)</tr>", html)
            self.assertIsNotNone(row, e["date"])
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(1))
            self.assertEqual(len(cells), 6, cells)
            if e["status"] == "failed":
                self.assertEqual(cells, ["—"] * 6, cells)
            elif not e["metrics"]["last30_tle"].get("ok"):
                self.assertEqual(cells[2], "—", cells)


class Ecosystem(unittest.TestCase):
    """The hand-maintained ecosystem list: every entry is a linked, dated public statement, rendered
    outside the job-generated library table and labelled as statements, not results."""
    def test_entries_are_linked_and_dated(self):
        data = json.loads((ROOT / "site/content/ecosystem.json").read_text(encoding="utf-8"))
        self.assertIn("tested", data["_provenance"])
        self.assertTrue(data["entries"])
        for e in data["entries"]:
            for key in ("project", "status", "date", "url", "source", "simple", "technical"):
                self.assertTrue(e.get(key), f"{e.get('project')}: {key}")
            self.assertRegex(e["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(e["url"].startswith("https://"), e["url"])
            self.assertIn(e["status"], ("in progress", "supported", "not supported"))

    def test_rendered_after_the_job_data_and_on_the_timeline(self):
        import build
        tmp = tempfile.mkdtemp()
        try:
            build.main(Path(tmp))
            library = (Path(tmp) / "library/index.html").read_text(encoding="utf-8")
            activity = (Path(tmp) / "activity/index.html").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp)
        note = "Statements, not results: nothing in this list has been run against the corpus."
        self.assertEqual(library.count(note), 1)
        self.assertLess(library.index("Run history"), library.index("Elsewhere in the ecosystem"))
        url = "https://community.libre.space/t/the-catalog-passed-99-999-in-july-a-test-corpus-for-tle-omm-parsers/15354/2"
        self.assertIn(f'<a href="{url}">Fredy, SatNOGS maintainer, on the Libre Space forum, 2026-09-22</a>', library)
        self.assertIn('<span class="badge warn">in progress</span>', library)
        self.assertNotIn("within weeks", library + activity)
        self.assertIn(f'<a href="{url}">SatNOGS: support above 99,999 in progress</a>', activity)


class Activity(unittest.TestCase):
    def test_attributions_are_exact_and_no_thread_text(self):
        import build
        tmp = tempfile.mkdtemp()
        try:
            build.main(Path(tmp))
            html = (Path(tmp) / "activity/index.html").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp)
        for phrase in ("Issue filed by the maintainer of this corpus", "Fix submitted by the maintainer of this corpus",
                       "Fix by karlhillx, tested against this corpus", "Reported upstream by another user"):
            self.assertEqual(html.count(phrase), 1, phrase)
        self.assertIn('data-activity-item="python-sgp4#172"', html)
        self.assertIn("timeline", html)

    def test_function_has_no_secret_and_only_public_sources(self):
        text = (ROOT / "functions/api/activity.js").read_text()
        self.assertNotRegex(text, r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")
        self.assertIn("env.GITHUB_TOKEN", text)
        for repo in ("brandon-rhodes/python-sgp4", "hneogy/gp-omm-conformance", "hneogy/gpconf-site"):
            self.assertIn(repo, text)
        self.assertNotIn("title", text.split("// Only state")[1].split("export async function buildActivity")[0].replace("titles", ""))

    def test_function_is_a_declared_es_module(self):
        # tests/activity-function.test.mjs imports functions/api/activity.js, an ES module with a .js name. Node treats
        # it as such because the nearest package.json, functions/package.json, declares "type": "module"; without that
        # declaration Node would fall back to module-syntax detection (S-027). Fail loudly if the declaration goes.
        pkg = json.loads((ROOT / "functions/package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg.get("type"), "module", pkg)


class JavaScript(unittest.TestCase):
    """Local convenience: the Node scripts (tests/*.test.js, *.test.mjs) through Node's built-in runner. Skipped
    without node, and in CI, where ci.yml runs `node --test` as its own step so nothing runs twice (S-026)."""
    def test_node_test_runner(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        if os.environ.get("CI"):
            self.skipTest("run by the node --test step of the workflow")
        proc = subprocess.run([node, "--test"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("fail 0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
