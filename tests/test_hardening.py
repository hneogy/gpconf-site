"""S-030: the jobs and templates against bad days (audit items 11.2 to 11.9).

Each test names its item. Everything runs offline against canned responses and temporary data directories."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "jobs"))

import build  # noqa: E402
import common  # noqa: E402
import library_status  # noqa: E402
import tracker  # noqa: E402
from tests.test_tracker import FakeOpener, csv_body, sources, TLE  # noqa: E402

HTML = b"<!DOCTYPE html>\n<html><head><title>Maintenance</title></head><body>Back soon</body></html>\n"


def good_table():
    s = {d["id"]: d["url"] for d in sources()["daily"]}
    return {s["last30-csv"]: (200, csv_body([100404, 100789])), s["last30-tle"]: (404, b"No GP data found"),
            s["analyst-csv"]: (200, csv_body([81011, 270000, 270449])), s["analyst-tle"]: (200, TLE.encode()),
            s["supgp-starlink-csv"]: (200, csv_body([72000, 799501621, 799501622]))}


def url_of(sid):
    return {d["id"]: d["url"] for d in sources()["daily"]}[sid]


def fetch(table):
    return common.Fetcher(opener=FakeOpener(table), pause=0)


class UnexpectedBodies(unittest.TestCase):
    """11.2 and 11.3."""

    def test_200_with_an_html_body_is_an_error_not_zeros(self):
        table = {u: (200, HTML) for u in good_table()}
        metrics, relations = tracker.run_daily(fetch(table), sources())
        for key, m in metrics.items():
            self.assertFalse(m["ok"], key)
            self.assertIn("unexpected body", m.get("error", ""), key)
            self.assertIsNone(m.get("records"), key)                 # no count is recorded, not a zero
        self.assertEqual(set(relations.values()), {None})

    def test_200_with_the_no_data_text_on_a_tle_endpoint_is_an_error(self):
        table = good_table()
        table[url_of("last30-tle")] = (200, b"No GP data found")
        metrics, _ = tracker.run_daily(fetch(table), sources())
        m = metrics["last30_tle"]
        self.assertFalse(m["ok"])
        self.assertFalse(m["is_404"])
        self.assertIn("unexpected body", m["error"])

    def test_200_csv_without_the_catalog_column_is_an_error(self):
        table = good_table()
        table[url_of("last30-csv")] = (200, b"OBJECT_NAME,EPOCH\r\nX,2026-09-01T00:00:00\r\n")
        metrics, _ = tracker.run_daily(fetch(table), sources())
        self.assertFalse(metrics["last30"]["ok"])
        self.assertIn("unexpected body", metrics["last30"]["error"])

    def test_404_with_a_foreign_body_is_an_error(self):
        table = good_table()
        table[url_of("last30-tle")] = (404, HTML)
        metrics, _ = tracker.run_daily(fetch(table), sources())
        m = metrics["last30_tle"]
        self.assertTrue(m["is_404"])
        self.assertFalse(m["body_is_no_gp_data"])
        self.assertFalse(m["ok"])
        self.assertIn("404 with unexpected body", m["error"])

    def test_last_successful_does_not_adopt_an_error_day(self):
        good, _ = tracker.run_daily(fetch(good_table()), sources())
        bad, _ = tracker.run_daily(fetch({u: (200, HTML) for u in good_table()}), sources())
        history = [{"date": "2026-09-24", "checked_at": "2026-09-24T06:44:00Z", "kind": "scheduled", "status": "ok", "metrics": good},
                   {"date": "2026-09-25", "checked_at": "2026-09-25T06:44:00Z", "kind": "scheduled", "status": "failed", "metrics": bad}]
        latest = tracker.build_latest(history, {"sources": []}, "2026-09-25T07:00:00Z")
        for group in tracker.METRIC_FIELDS:
            self.assertEqual(latest["last_successful"][group]["entry_date"], "2026-09-24", group)
        self.assertEqual(latest["last_successful"]["last30"]["highest"], 100789)


class Reruns(unittest.TestCase):
    """11.5: a same-day rerun makes no request; the day after a 403 day makes no request and says so."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copy(ROOT / "data" / "tracker" / "drift.json", self.tmp)
        (Path(self.tmp) / "history.json").write_text("[]")
        self.opener = FakeOpener(good_table())
        self._fetcher, self._utcnow = tracker.Fetcher, tracker.utcnow
        tracker.Fetcher = lambda **kw: common.Fetcher(opener=self.opener, pause=0)
        self.now = "2026-09-24T06:20:00Z"
        tracker.utcnow = lambda: self.now

    def tearDown(self):
        tracker.Fetcher, tracker.utcnow = self._fetcher, self._utcnow
        shutil.rmtree(self.tmp)

    def run_main(self, *extra):
        return tracker.main(["--data-dir", self.tmp, "--no-drift", *extra])

    def history(self):
        return json.loads((Path(self.tmp) / "history.json").read_text())

    def test_same_day_rerun_reuses_the_days_data(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(len(self.opener.calls), 5)
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(len(self.opener.calls), 5)                  # nothing requested again
        self.assertEqual(len(self.history()), 1)
        latest = json.loads((Path(self.tmp) / "latest.json").read_text())
        self.assertEqual(latest["latest"]["date"], "2026-09-24")
        self.assertEqual(self.run_main("--force"), 0)
        self.assertEqual(len(self.opener.calls), 10)                 # --force repeats, and replaces the day's entry
        self.assertEqual(len(self.history()), 1)

    def test_the_day_after_a_403_day_makes_no_request_and_says_so(self):
        refused = {u: (403, b"Forbidden") for u in good_table()}
        self.opener = FakeOpener(refused)
        self.assertEqual(self.run_main(), 0)
        h = self.history()
        self.assertEqual((h[-1]["status"], h[-1]["fetch"]["errors"]), ("failed", 5))
        self.opener = FakeOpener(good_table())
        self.now = "2026-09-25T06:20:00Z"
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(len(self.opener.calls), 0)                  # skipped
        h = self.history()
        self.assertEqual((h[-1]["date"], h[-1]["kind"], h[-1]["status"]), ("2026-09-25", "scheduled", "skipped"))
        self.assertIn("403", h[-1]["reason"])
        self.assertIn("2026-09-24", h[-1]["reason"])
        self.assertEqual(h[-1]["fetch"]["requests"], 0)
        self.now = "2026-09-26T06:20:00Z"
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(len(self.opener.calls), 5)                  # resumes the day after the skip
        self.assertEqual(self.history()[-1]["status"], "ok")


class Rendering(unittest.TestCase):
    """11.4, 11.6, 11.7 and the skipped day of 11.5, through build.py on a temporary data directory."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = Path(self.tmp) / "data"
        shutil.copytree(ROOT / "data", self.data)
        self.out = Path(self.tmp) / "dist"
        self._data = build.DATA
        build.DATA = self.data

    def tearDown(self):
        build.DATA = self._data
        shutil.rmtree(self.tmp)

    def entry(self, date, status, groups, kind="scheduled"):
        metrics = {}
        for group, fields in tracker.METRIC_FIELDS.items():
            g = groups.get(group)
            if g is None:
                metrics[group] = {"ok": False, "status": 500, "error": "HTTP 500", "checked_at": f"{date}T06:44:00Z", **{f: None for f in fields}}
            else:
                metrics[group] = {"ok": True, "status": 200, "checked_at": f"{date}T06:44:00Z", **g}
        return {"date": date, "checked_at": f"{date}T06:44:30Z", "kind": kind, "status": status, "metrics": metrics,
                "relations": {}, "drift": {"checked": 0, "results": []}, "fetch": {"requests": 5, "errors": 0, "bytes": 0}}

    def write_tracker(self, history):
        drift = json.loads((self.data / "tracker" / "drift.json").read_text())
        (self.data / "tracker" / "history.json").write_text(json.dumps(history))
        (self.data / "tracker" / "latest.json").write_text(json.dumps(tracker.build_latest(history, drift, "2026-09-26T00:00:00Z")))

    def page(self, name):
        build.main(self.out)
        return (self.out / name).read_text(encoding="utf-8")

    OK1 = {"last30": {"records": 10, "highest": 100010, "six_digit": 10, "nine_digit": 0, "below_100000": 0},
           "last30_tle": {"status": 404, "is_404": True, "records": 0},
           "analyst": {"records": 5, "six_digit": 3, "below_100000": 2},
           "analyst_tle": {"status": 200, "is_404": False, "records": 2},
           "supgp_starlink": {"records": None, "nine_digit": 4, "nine_digit_present": True}}

    def test_empty_history_builds(self):
        self.write_tracker([])
        html = self.page("tracker/index.html")
        self.assertIn("No successful measurement has been recorded yet", html)
        self.assertNotIn('class="value">—', html)                    # no grid of dashes pretending to be values
        self.page("index.html")

    def test_a_group_that_has_never_been_ok_renders_a_dash_not_a_crash(self):
        groups = dict(self.OK1); groups.pop("last30_tle")
        self.write_tracker([self.entry("2026-09-24", "partial", groups)])
        html = self.page("tracker/index.html")
        self.assertIn("100,010", html)
        tile = html[html.index("last-30-days TLE request"):]
        tile = tile[:tile.index("</div>")]
        self.assertIn("no successful check yet", tile)
        self.assertNotIn("some still fit", tile)                     # a never-ok group must not read as an answer
        self.page("index.html")

    def test_partial_day_tile_shows_one_timestamp_per_metric(self):
        groups = dict(self.OK1); groups.pop("analyst_tle")
        self.write_tracker([self.entry("2026-09-24", "ok", self.OK1), self.entry("2026-09-25", "partial", groups)])
        html = self.page("tracker/index.html")
        tile = html[html.index("Analyst group, CSV vs TLE record count"):]
        tile = tile[:tile.index("</div>")]
        self.assertIn("2026-09-25", tile)
        self.assertIn("2026-09-24", tile)                            # the TLE count's own, older time

    def test_skipped_day_is_explained_on_the_page(self):
        skipped = {"date": "2026-09-25", "checked_at": "2026-09-25T06:20:00Z", "kind": "scheduled", "status": "skipped",
                   "reason": "the previous run on 2026-09-24 was refused with HTTP 403; no request was made today", "metrics": {},
                   "relations": {}, "drift": {"checked": 0, "results": []}, "fetch": {"requests": 0, "errors": 0, "bytes": 0}}
        self.write_tracker([self.entry("2026-09-24", "ok", self.OK1), skipped])
        html = self.page("tracker/index.html")
        self.assertIn("no request was made today", html)
        self.assertIn("2026-09-25 (skipped)", html)

    def test_library_import_failure_renders_as_a_failure(self):
        latest = {"checked_at": "2026-09-28T07:23:00Z", "versions": {"sgp4": None, "sgp4_accelerated": None, "skyfield": "1.55", "python": "3.13.7"},
                  "inputs": "x", "behaviours": [], "group_errors": {"python-sgp4": "ModuleNotFoundError: No module named 'sgp4'"},
                  "counts": {"pass": 0, "fail": 0, "error": 0}}
        history = json.loads((self.data / "library" / "history.json").read_text())
        history.append({"checked_at": latest["checked_at"], "versions": latest["versions"], "counts": latest["counts"], "results": {}})
        (self.data / "library" / "latest.json").write_text(json.dumps(latest))
        (self.data / "library" / "history.json").write_text(json.dumps(history))
        html = self.page("library/index.html")
        self.assertIn('class="callout bad"', html)
        self.assertIn("could not run", html)
        self.assertNotIn("0 pass, 0 fail", html)
        self.assertIn("could not run", html[html.index("Run history"):])


class LibraryClassification(unittest.TestCase):
    """11.7: a harness or environment exception is an error, a library exception is the finding."""

    def test_harness_exception_is_error_and_library_exception_is_fail(self):
        def boom_import():
            raise ImportError("no module")
        def boom_type():
            raise TypeError("'NoneType' object is not subscriptable")
        self.assertEqual(library_status.behaviour("a", "t", "lib", "exp", [], boom_import)["result"], "error")
        self.assertEqual(library_status.behaviour("b", "t", "lib", "exp", [], boom_type)["result"], "fail")
        self.assertEqual(library_status.behaviour("c", "t", "lib", "exp", [], lambda: (False, "d"))["result"], "fail")
        self.assertEqual(library_status.behaviour("d", "t", "lib", "exp", [], lambda: (True, "d"))["result"], "pass")


class DataConsistency(unittest.TestCase):
    """11.8: the published latest.json agrees with the history it was built from."""

    def test_latest_matches_the_history_tail(self):
        latest = json.loads((ROOT / "data" / "tracker" / "latest.json").read_text())
        history = json.loads((ROOT / "data" / "tracker" / "history.json").read_text())
        self.assertEqual(latest["latest"], history[-1])
        self.assertEqual(latest["history_entries"], len(history))


class Workflows(unittest.TestCase):
    """11.9: the artifact upload runs whatever the run step did, unless the workflow was cancelled."""

    def test_artifact_upload_runs_unless_cancelled(self):
        for name in ("tracker.yml", "library.yml"):
            text = (ROOT / ".github" / "workflows" / name).read_text()
            i = text.index("actions/upload-artifact@v4")
            block = text[text.rfind("- name:", 0, i):text.index("- name:", i)]
            self.assertIn("if: ${{ !cancelled() }}", block, name)


if __name__ == "__main__":
    unittest.main()
