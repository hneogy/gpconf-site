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
         "library/index.html", "tools/index.html", "about/index.html", "404.html"]


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
