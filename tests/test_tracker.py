"""Unit tests for the tracker job. Inputs are built from the CCSDS 502.0-B-3 annex G example
values with the catalog number varied; no provider data is used."""
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jobs"))
import common  # noqa: E402
import tracker  # noqa: E402

HEADER = ("OBJECT_NAME,OBJECT_ID,EPOCH,MEAN_MOTION,ECCENTRICITY,INCLINATION,RA_OF_ASC_NODE,ARG_OF_PERICENTER,"
          "MEAN_ANOMALY,EPHEMERIS_TYPE,CLASSIFICATION_TYPE,NORAD_CAT_ID,ELEMENT_SET_NO,REV_AT_EPOCH,BSTAR,"
          "MEAN_MOTION_DOT,MEAN_MOTION_DDOT")
ROW = "GOES 9,1995-025A,2020-03-04T10:34:41.426400,1.00273272,.0005013,3.0539,81.7939,249.2363,150.1602,0,U,{id},925,4316,.1E-3,-.113E-5,0"
TLE = ("GOES 9                  \r\n"
       "1 23581U 95025A   20064.44075725 -.00000113  00000+0  10000-3 0  9254\r\n"
       "2 23581   3.0539  81.7939 0005013 249.2363 150.1602  1.00273272 43169\r\n")


def csv_body(ids):
    return ("\r\n".join([HEADER] + [ROW.format(id=i) for i in ids]) + "\r\n").encode()


class _Resp(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """Serves canned responses by URL; 404s raise HTTPError like urllib does."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def open(self, req, timeout=None):
        self.calls.append((req.full_url, req.get_header("User-agent")))
        status, body = self.table[req.full_url]
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "err", {}, io.BytesIO(body))
        return _Resp(status, body)


def sources():
    return json.loads((ROOT / "jobs" / "sources.json").read_text())


class Measurements(unittest.TestCase):
    def test_csv_counts(self):
        s = tracker.summarise_ids(tracker.csv_catnrs(csv_body([25544, 100000, 100789, 799501621])))
        self.assertEqual(s, {"records": 4, "highest": 799501621, "six_digit": 2, "nine_digit": 1, "below_100000": 1})

    def test_empty_csv(self):
        self.assertEqual(tracker.summarise_ids(tracker.csv_catnrs(csv_body([]))), {"records": 0, "highest": None, "six_digit": 0, "nine_digit": 0, "below_100000": 0})

    def test_tle_count(self):
        self.assertEqual(tracker.tle_record_count(TLE.encode() * 3), 3)


class Policy(unittest.TestCase):
    def test_same_url_twice_is_refused_before_sending(self):
        op = FakeOpener({"https://example.invalid/a": (200, b"x")})
        f = common.Fetcher(opener=op, pause=0)
        f.get("https://example.invalid/a", "a")
        with self.assertRaises(common.PolicyError):
            f.get("https://example.invalid/a", "a-again")
        self.assertEqual(len(op.calls), 1)

    def test_cap_is_enforced(self):
        table = {f"https://example.invalid/{i}": (200, b"x") for i in range(12)}
        f = common.Fetcher(opener=FakeOpener(table), pause=0, max_requests=10)
        for i in range(10):
            f.get(f"https://example.invalid/{i}", str(i))
        with self.assertRaises(common.PolicyError):
            f.get("https://example.invalid/10", "10")

    def test_user_agent_names_project_and_site(self):
        op = FakeOpener({"https://example.invalid/a": (200, b"x")})
        common.Fetcher(opener=op, pause=0).get("https://example.invalid/a", "a")
        ua = op.calls[0][1]
        self.assertIn("gpconf-site", ua)
        self.assertIn("https://gpconf.neogy.dev", ua)

    def test_404_is_recorded_not_retried(self):
        op = FakeOpener({"https://example.invalid/a": (404, b"No GP data found")})
        f = common.Fetcher(opener=op, pause=0)
        status, body, rec = f.get("https://example.invalid/a", "a")
        self.assertEqual((status, body), (404, b"No GP data found"))
        self.assertEqual(len(op.calls), 1)

    def test_daily_plan_fits_the_budget(self):
        s = sources()
        self.assertEqual(len(s["daily"]), 5)
        self.assertLessEqual(len(s["daily"]) + tracker.DEFAULT_MAX_DRIFT, common.MAX_REQUESTS_PER_RUN)
        self.assertEqual(len({d["url"] for d in s["daily"]}), 5)
        self.assertEqual(len(s["stable"]), 22)
        for src in s["daily"] + s["stable"]:
            self.assertTrue(src["url"].startswith("https://celestrak.org/"))


class DailyRun(unittest.TestCase):
    def table(self):
        s = {d["id"]: d["url"] for d in sources()["daily"]}
        return {
            s["last30-csv"]: (200, csv_body([100404, 100789])),
            s["last30-tle"]: (404, b"No GP data found"),
            s["analyst-csv"]: (200, csv_body([81011, 270000, 270449])),
            s["analyst-tle"]: (200, TLE.encode()),
            s["supgp-starlink-csv"]: (200, csv_body([72000, 799501621, 799501622])),
        }

    def test_metrics_and_relations(self):
        f = common.Fetcher(opener=FakeOpener(self.table()), pause=0)
        metrics, relations = tracker.run_daily(f, sources())
        self.assertEqual(metrics["last30"]["highest"], 100789)
        self.assertEqual(metrics["last30"]["six_digit"], 2)
        self.assertTrue(metrics["last30_tle"]["is_404"])
        self.assertTrue(metrics["last30_tle"]["body_is_no_gp_data"])
        self.assertEqual(metrics["analyst"]["below_100000"], 1)
        self.assertEqual(metrics["analyst_tle"]["records"], 1)
        self.assertEqual(metrics["supgp_starlink"]["nine_digit"], 2)
        self.assertTrue(metrics["supgp_starlink"]["nine_digit_present"])
        self.assertEqual(relations, {"last30_tle_equals_below_100000": True, "analyst_tle_equals_below_100000": True})
        self.assertEqual(len(f.log), 5)

    def test_failure_is_partial_not_fatal(self):
        t = self.table()
        url = [u for u in t if "FILE=starlink" in u][0]
        t[url] = (503, b"")
        f = common.Fetcher(opener=FakeOpener(t), pause=0)
        metrics, _ = tracker.run_daily(f, sources())
        self.assertFalse(metrics["supgp_starlink"]["ok"])
        self.assertTrue(metrics["last30"]["ok"])

    def test_no_element_values_in_outputs(self):
        f = common.Fetcher(opener=FakeOpener(self.table()), pause=0)
        metrics, relations = tracker.run_daily(f, sources())
        text = json.dumps({"m": metrics, "r": relations, "log": f.log})
        for needle in ("1.00273272", "0005013", "81.7939", "249.2363", "150.1602", "20064.44075725", "GOES"):
            self.assertNotIn(needle, text)


class Drift(unittest.TestCase):
    def state(self):
        st = json.loads((ROOT / "data" / "tracker" / "drift.json").read_text())
        for s in st["sources"]:  # independent of whatever the live job has checked so far
            s.update({"last_checked": None, "last_status": None, "last_http_status": None, "history": []})
        return st

    def test_rotation_picks_oldest_first_and_caps(self):
        st = self.state()
        old, recent = st["sources"][0], st["sources"][1]
        old["last_checked"] = "2026-09-01T00:00:00Z"      # checked long ago: due
        recent["last_checked"] = "2026-09-20T00:00:00Z"   # checked yesterday: not due
        now = "2026-09-21T06:00:00Z"
        due4 = tracker.due_drift_sources(st, now, 4)
        self.assertEqual(len(due4), 4)                    # the cap
        self.assertTrue(all(d.get("last_checked") is None for d in due4))  # never-checked sources come first
        due_all = tracker.due_drift_sources(st, now, 25)
        ids = [d["id"] for d in due_all]
        self.assertEqual(len(due_all), 21)                # everything except the recently checked one
        self.assertNotIn(recent["id"], ids)
        self.assertEqual(ids[-1], old["id"])              # the dated one sorts after the never-checked ones

    def test_match_and_drift_are_hash_only(self):
        import hashlib
        st = self.state()
        st["sources"] = st["sources"][:2]
        good, changed = st["sources"]
        good["sha256"] = hashlib.sha256(b"No GP data found").hexdigest()
        table = {good["url"]: (200, b"No GP data found"), changed["url"]: (200, b"different bytes")}
        f = common.Fetcher(opener=FakeOpener(table), pause=0)
        checked = {c["id"]: c["result"] for c in tracker.run_drift(f, st, "2026-09-21T06:00:00Z", 4)}
        self.assertEqual(checked, {good["id"]: "match", changed["id"]: "drift"})
        summ = tracker.drift_summary(st, "2026-09-21T06:00:00Z")
        self.assertEqual((summ["match"], summ["drift"], summ["never_checked"]), (1, 1, 0))


    def test_error_page_is_error_not_drift_and_stays_due(self):
        """2026-09-22: CelesTrak answered HTTP 500 with an error page; the old code hashed the page and marked four
        stable sources drifted. A non-answer must be 'error', must not touch last_checked, and must stay due."""
        import hashlib
        st = self.state()
        st["sources"] = st["sources"][:4]
        five, fourofour, was404, was200 = st["sources"]
        for s in (five, was404, was200):
            s["baseline_http_status"] = 200
        fourofour["baseline_http_status"] = 404
        fourofour["sha256"] = hashlib.sha256(b"No GP data found").hexdigest()
        was200["last_checked"] = "2026-09-15T00:00:00Z"   # matched a week ago
        error_page = b"<html>Internal Server Error</html>"
        table = {five["url"]: (500, error_page), fourofour["url"]: (404, b"No GP data found"),
                 was404["url"]: (404, b"No GP data found"), was200["url"]: (500, error_page)}
        f = common.Fetcher(opener=FakeOpener(table), pause=0)
        now = "2026-09-22T06:44:00Z"
        checked = {c["id"]: c["result"] for c in tracker.run_drift(f, st, now, 4)}
        self.assertEqual(checked, {five["id"]: "error", fourofour["id"]: "match", was404["id"]: "drift", was200["id"]: "error"})
        self.assertIsNone(five["last_checked"])                       # untouched: never checked successfully
        self.assertEqual(was200["last_checked"], "2026-09-15T00:00:00Z")  # untouched: last success stands
        at = {r["label"]: r["requested_at"] for r in f.log}            # errors are stamped with the request time, like successes
        self.assertEqual(five["last_error_at"], at["drift-" + five["id"]])
        self.assertNotIn("last_sha256", five)                         # the error page's hash is not recorded as the source's
        self.assertEqual(five["history"][-1], {"checked_at": at["drift-" + five["id"]], "result": "error", "http_status": 500})
        due = {s["id"] for s in tracker.due_drift_sources(st, "2026-09-23T06:44:00Z", 10)}
        self.assertIn(five["id"], due)                                # still due the next day
        self.assertIn(was200["id"], due)
        self.assertNotIn(fourofour["id"], due)                        # a real check consumed its weekly slot
        summ = tracker.drift_summary(st, now)
        self.assertEqual((summ["match"], summ["drift"], summ["error"], summ["never_checked"]), (1, 1, 2, 0))
        self.assertEqual([p["last_error_at"] for p in summ["per_source"] if p["id"] == five["id"]], [at["drift-" + five["id"]]])


class Outputs(unittest.TestCase):
    """--rebuild-latest over a fixture history built here, not the committed data: the committed values change
    with every catalogued object, and a test that pinned them turned the validation gate red on the first new
    day (S-028). Shape is asserted, never a live number."""

    @staticmethod
    def entry(date, kind, status, groups):
        metrics = {}
        for group, fields in tracker.METRIC_FIELDS.items():
            g = groups.get(group)
            if g is None:  # the fetch failed for this group that day: no answer, ok False
                metrics[group] = {"ok": False, "status": 500, "error": "HTTP 500", "checked_at": f"{date}T06:44:00Z", **{f: None for f in fields}}
            else:
                metrics[group] = {"ok": True, "status": 200, "checked_at": f"{date}T06:44:00Z", **g}
        return {"date": date, "checked_at": f"{date}T06:44:30Z", "kind": kind, "status": status, "metrics": metrics,
                "relations": {}, "drift": {"results": []}, "fetch": {"requests": 5, "errors": 0}}

    def test_rebuild_latest_from_fixture_history(self):
        ok1 = {"last30": {"records": 10, "highest": 100010, "six_digit": 10, "nine_digit": 0, "below_100000": 0},
               "last30_tle": {"status": 404, "is_404": True, "records": 0},
               "analyst": {"records": 5, "six_digit": 3, "below_100000": 2},
               "analyst_tle": {"status": 200, "is_404": False, "records": 2},
               "supgp_starlink": {"records": None, "nine_digit": 4, "nine_digit_present": True}}
        ok2 = {**ok1, "last30": {"records": 12, "highest": 100012, "six_digit": 12, "nine_digit": 0, "below_100000": 0}}
        ok2.pop("supgp_starlink")  # that group failed on day 2: its last success stays the seed day's
        history = [self.entry("2026-09-01", "seed", "ok", ok1),
                   self.entry("2026-09-02", "scheduled", "ok", ok2),
                   self.entry("2026-09-03", "scheduled", "failed", {})]
        drift = {"baseline": {"corpus_version": "0.0.0"},
                 "sources": [{"id": "a", "case": "c", "url": "https://example.invalid/a", "sha256": "0" * 64, "bytes": 1,
                              "baseline_http_status": 200, "baseline_retrieved": "2026-09-01T00:00:00Z",
                              "last_checked": "2026-09-02T06:44:00Z", "last_status": "match", "last_http_status": 200, "history": []},
                             {"id": "b", "case": "c", "url": "https://example.invalid/b", "sha256": "1" * 64, "bytes": 1,
                              "baseline_http_status": 200, "baseline_retrieved": "2026-09-01T00:00:00Z",
                              "last_checked": None, "last_status": None, "last_http_status": None, "history": []}]}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "history.json").write_text(json.dumps(history))
            (Path(d) / "drift.json").write_text(json.dumps(drift))
            self.assertEqual(tracker.main(["--data-dir", d, "--rebuild-latest"]), 0)
            latest = json.loads((Path(d) / "latest.json").read_text())
        for key in ("generated_at", "site", "latest", "last_successful", "drift", "history_entries", "fetch_log"):
            self.assertIn(key, latest)
        self.assertEqual(latest["latest"], history[-1])                 # the newest entry, even a failed one
        self.assertEqual(latest["history_entries"], 3)
        ls = latest["last_successful"]
        self.assertEqual(set(ls), set(tracker.METRIC_FIELDS))           # every group has a last success
        for group, fields in tracker.METRIC_FIELDS.items():
            self.assertEqual(set(ls[group]), set(fields) | {"checked_at", "entry_date", "seed"}, group)
        self.assertEqual(ls["last30"]["entry_date"], "2026-09-02")      # the latest ok day, not the failed one
        self.assertEqual(ls["last30"]["highest"], 100012)               # a fixture value, not a live one
        self.assertFalse(ls["last30"]["seed"])
        self.assertEqual(ls["supgp_starlink"]["entry_date"], "2026-09-01")  # the group that failed on day 2 keeps day 1
        self.assertTrue(ls["supgp_starlink"]["seed"])
        self.assertTrue(ls["last30_tle"]["is_404"])
        dr = latest["drift"]
        self.assertEqual((dr["sources"], dr["match"], dr["drift"], dr["error"], dr["never_checked"]), (2, 1, 0, 0, 1))
        self.assertEqual([p["id"] for p in dr["per_source"]], ["a", "b"])

    def test_rebuild_latest_from_empty_history(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "history.json").write_text("[]")
            (Path(d) / "drift.json").write_text(json.dumps({"baseline": {}, "sources": []}))
            self.assertEqual(tracker.main(["--data-dir", d, "--rebuild-latest"]), 0)
            latest = json.loads((Path(d) / "latest.json").read_text())
        self.assertIsNone(latest["latest"])
        self.assertEqual(latest["last_successful"], {})
        self.assertEqual(latest["history_entries"], 0)


if __name__ == "__main__":
    unittest.main()
