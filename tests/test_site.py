"""Build the site into a temporary directory and check the page contract: every page has both
reading levels, no external script/style/font, no inline event handlers, and the tools are
client-side only. Also runs the JavaScript Alpha-5 vector test when node is available."""
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

    def test_function_builder(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        proc = subprocess.run([node, str(ROOT / "tests/activity-function.test.mjs")], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"ok":true', proc.stdout.replace(" ", ""))


class Alpha5JavaScript(unittest.TestCase):
    def test_vectors(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        proc = subprocess.run([node, str(ROOT / "tests/alpha5-vectors.test.js")], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"failed":0', proc.stdout.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
