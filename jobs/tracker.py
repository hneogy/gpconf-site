#!/usr/bin/env python3
"""Daily tracker job for gpconf.neogy.dev.

Fetches five CelesTrak endpoints once each, plus up to four stable-source drift checks so that
every stable source is re-checked about once a week, and writes data/tracker/{history,latest,
drift}.json. Only counts, yes/no states, HTTP statuses, byte counts, hashes and timestamps are
computed and stored. No element set is stored: bodies stay in memory, or go to a local
--cache-dir that git ignores. Standard library only.

    python jobs/tracker.py                  # the scheduled run (9 requests at most)
    python jobs/tracker.py --no-drift       # 5 requests
    python jobs/tracker.py --rebuild-latest # no network: regenerate latest.json
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, ROOT, SITE_URL, Fetcher, PolicyError, dump_json, load_json, parse_ts, utcnow  # noqa: E402

SOURCES = ROOT / "jobs" / "sources.json"
TRACKER_DIR = DATA / "tracker"
DRIFT_MIN_AGE_DAYS = 6.5
DEFAULT_MAX_DRIFT = 4
METRIC_FIELDS = {
    "last30": ["records", "highest", "six_digit", "nine_digit", "below_100000"],
    "last30_tle": ["status", "is_404", "records"],
    "analyst": ["records", "six_digit", "below_100000"],
    "analyst_tle": ["status", "is_404", "records"],
    "supgp_starlink": ["records", "nine_digit", "nine_digit_present"],
}


# ---------------------------------------------------------------- measurements (counts only)

def csv_catnrs(body: bytes) -> list[int]:
    text = body.decode("utf-8", "replace")
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("NORAD_CAT_ID") or "").strip()
        if value:
            out.append(int(value))
    return out


def tle_record_count(body: bytes) -> int:
    """Number of TLE line-1s (69 characters, starting '1 ')."""
    return sum(1 for ln in body.decode("utf-8", "replace").splitlines()
               if ln.startswith("1 ") and len(ln.rstrip("\r")) == 69)


def summarise_ids(ids: list[int]) -> dict:
    return {
        "records": len(ids),
        "highest": max(ids) if ids else None,
        "six_digit": sum(100000 <= i < 1000000 for i in ids),
        "nine_digit": sum(i >= 100000000 for i in ids),
        "below_100000": sum(i < 100000 for i in ids),
    }


def fetch_csv_metrics(fetcher: Fetcher, src: dict) -> dict:
    status, body, rec = fetcher.get(src["url"], src["id"])
    m = {"ok": False, "status": status, "checked_at": rec["requested_at"], "bytes": rec["bytes"]}
    if status == 200:
        try:
            m.update(summarise_ids(csv_catnrs(body)))
            m["ok"] = True
        except Exception as exc:
            m["error"] = f"parse: {type(exc).__name__}"
    else:
        m["error"] = rec["error"] or f"HTTP {status}"
    return m


def fetch_tle_metrics(fetcher: Fetcher, src: dict) -> dict:
    status, body, rec = fetcher.get(src["url"], src["id"])
    m = {"ok": False, "status": status, "checked_at": rec["requested_at"], "bytes": rec["bytes"],
         "is_404": status == 404}
    if status == 200:
        m["records"] = tle_record_count(body)
        m["ok"] = True
    elif status == 404:  # a legitimate outcome for this format, not a failure of the check
        m["records"] = 0
        m["ok"] = True
        head = body.strip().lower()
        m["body_is_no_gp_data"] = head.startswith(b"no gp data found") or head.startswith(b"no supgp data")
    else:
        m["error"] = rec["error"] or f"HTTP {status}"
    return m


def run_daily(fetcher: Fetcher, sources: dict) -> tuple[dict, dict]:
    by_id = {s["id"]: s for s in sources["daily"]}
    metrics = {
        "last30": fetch_csv_metrics(fetcher, by_id["last30-csv"]),
        "last30_tle": fetch_tle_metrics(fetcher, by_id["last30-tle"]),
        "analyst": fetch_csv_metrics(fetcher, by_id["analyst-csv"]),
        "analyst_tle": fetch_tle_metrics(fetcher, by_id["analyst-tle"]),
        "supgp_starlink": fetch_csv_metrics(fetcher, by_id["supgp-starlink-csv"]),
    }
    sg = metrics["supgp_starlink"]
    if sg["ok"]:
        sg["nine_digit_present"] = sg["nine_digit"] > 0
    relations = {}
    for a, b, key in (("last30", "last30_tle", "last30_tle_equals_below_100000"),
                      ("analyst", "analyst_tle", "analyst_tle_equals_below_100000")):
        ma, mb = metrics[a], metrics[b]
        relations[key] = (ma["below_100000"] == mb["records"]) if ma["ok"] and mb["ok"] else None
    return metrics, relations


# ---------------------------------------------------------------- weekly drift, a few sources per day

def due_drift_sources(drift_state: dict, now_iso: str, max_n: int) -> list[dict]:
    now = parse_ts(now_iso)

    def due(s):
        lc = s.get("last_checked")
        return (not lc) or (now - parse_ts(lc)) >= timedelta(days=DRIFT_MIN_AGE_DAYS)

    todo = [s for s in drift_state["sources"] if due(s)]
    todo.sort(key=lambda s: (s.get("last_checked") or "", s["id"]))
    return todo[:max_n]


def classify_drift(status, error, sha256, source: dict) -> str:
    """'match' or 'drift' only when CelesTrak answered the question: a 200, or the 404 recorded for the
    two sources whose baseline is the 16-byte 'No GP data found' body. A 5xx, a 403 or 429, any other
    status or a transport failure is an error page, not the source, and its hash is never compared
    (on 2026-09-22 nine HTTP 500 pages were hashed and four stable sources were falsely marked drifted,
    S-022). A 200 where 404 was recorded, or a 404 where 200 was recorded, is the provider's answer
    changing, which is the alarm S-009 asks for: drift."""
    if error or status not in (200, 404):
        return "error"
    if status != source["baseline_http_status"]:
        return "drift"
    return "match" if sha256 == source["sha256"] else "drift"


def run_drift(fetcher: Fetcher, drift_state: dict, now_iso: str, max_n: int) -> list[dict]:
    checked = []
    for s in due_drift_sources(drift_state, now_iso, max_n):
        status, _body, rec = fetcher.get(s["url"], "drift-" + s["id"])
        result = classify_drift(status, rec["error"], rec["sha256"], s)
        s["last_status"] = result
        s["last_http_status"] = status
        if result == "error":
            s["last_error_at"] = rec["requested_at"]  # last_checked stays as it was: the source remains due
        else:
            s["last_checked"] = rec["requested_at"]
            s["last_sha256"] = rec["sha256"]
        s.setdefault("history", []).append({"checked_at": rec["requested_at"], "result": result, "http_status": status})
        s["history"] = s["history"][-12:]
        checked.append({"id": s["id"], "result": result, "http_status": status})
    return checked


def drift_summary(drift_state: dict, now_iso: str) -> dict:
    now = parse_ts(now_iso)
    srcs = drift_state["sources"]
    recent = [s for s in srcs if s.get("last_checked") and now - parse_ts(s["last_checked"]) <= timedelta(days=8)]
    return {
        "sources": len(srcs),
        "checked_in_last_8_days": len(recent),
        "match": sum(s.get("last_status") == "match" for s in srcs),
        "drift": sum(s.get("last_status") == "drift" for s in srcs),
        "error": sum(s.get("last_status") == "error" for s in srcs),
        "never_checked": sum(1 for s in srcs if not s.get("last_checked") and not s.get("last_error_at")),  # never attempted; an errored attempt counts under "error"
        "last_check": max((s["last_checked"] for s in srcs if s.get("last_checked")), default=None),
        "baseline": drift_state.get("baseline"),
        "per_source": [{"id": s["id"], "case": s["case"], "last_checked": s.get("last_checked"),
                        "last_status": s.get("last_status"), "last_http_status": s.get("last_http_status"),
                        "last_error_at": s.get("last_error_at")} for s in srcs],
    }


# ---------------------------------------------------------------- outputs

def build_latest(history: list[dict], drift_state: dict, now_iso: str, fetch_log=None) -> dict:
    last_successful = {}
    for group, fields in METRIC_FIELDS.items():
        for entry in reversed(history):
            m = (entry.get("metrics") or {}).get(group)
            if m and m.get("ok") and any(m.get(f) is not None for f in fields):
                last_successful[group] = {**{f: m.get(f) for f in fields},
                                          "checked_at": m.get("checked_at") or entry.get("checked_at"),
                                          "entry_date": entry["date"], "seed": entry.get("kind") == "seed"}
                break
    return {
        "generated_at": now_iso,
        "site": SITE_URL,
        "latest": history[-1] if history else None,
        "last_successful": last_successful,
        "drift": drift_summary(drift_state, now_iso),
        "history_entries": len(history),
        "fetch_log": fetch_log or [],
    }


def summary_lines(entry: dict) -> list[str]:
    m = entry["metrics"]
    lines = [f"{entry['date']} {entry['checked_at']} status={entry['status']}"]
    for key in METRIC_FIELDS:
        g = m.get(key) or {}
        shown = {k: g.get(k) for k in METRIC_FIELDS[key] if g.get(k) is not None}
        lines.append(f"  {key}: ok={g.get('ok')} http={g.get('status')} {shown}" + (f" error={g['error']}" if g.get("error") else ""))
    lines.append(f"  relations: {entry.get('relations')}")
    lines.append(f"  drift: {entry.get('drift')}")
    lines.append(f"  fetch: {entry.get('fetch')}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(TRACKER_DIR))
    ap.add_argument("--sources", default=str(SOURCES))
    ap.add_argument("--cache-dir", help="local, git-ignored directory for the raw bodies of this run (inspection only)")
    ap.add_argument("--no-drift", action="store_true", help="skip the stable-source drift checks (5 requests instead of up to 9)")
    ap.add_argument("--max-drift", type=int, default=DEFAULT_MAX_DRIFT)
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--rebuild-latest", action="store_true", help="no network: regenerate latest.json from history.json and drift.json")
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir)
    sources = load_json(args.sources)
    history = load_json(data_dir / "history.json", default=[])
    drift_state = load_json(data_dir / "drift.json")
    now = utcnow()

    if args.rebuild_latest:
        dump_json(data_dir / "latest.json", build_latest(history, drift_state, now))
        print(f"latest.json rebuilt from {len(history)} history entries; no request made")
        return 0

    fetcher = Fetcher(cache_dir=args.cache_dir, pause=args.pause)
    try:
        metrics, relations = run_daily(fetcher, sources)
        drift_checked = [] if args.no_drift else run_drift(fetcher, drift_state, now, args.max_drift)
    except PolicyError as exc:
        print(f"POLICY: {exc}", file=sys.stderr)
        return 2

    oks = [m["ok"] for m in metrics.values()]
    status = "ok" if all(oks) else ("failed" if not any(oks) else "partial")
    entry = {
        "date": now[:10], "checked_at": now, "kind": "scheduled", "status": status,
        "metrics": metrics, "relations": relations,
        "drift": {"checked": len(drift_checked), "results": drift_checked},
        "fetch": {"requests": len(fetcher.log),
                  "errors": sum(1 for r in fetcher.log if r["error"] or r["status"] not in (200, 404)),
                  "bytes": sum(r["bytes"] for r in fetcher.log)},
    }
    history = [e for e in history if not (e["date"] == entry["date"] and e.get("kind") == "scheduled")] + [entry]
    dump_json(data_dir / "history.json", history)
    dump_json(data_dir / "drift.json", drift_state)
    dump_json(data_dir / "latest.json", build_latest(history, drift_state, now, fetcher.log))
    print("\n".join(summary_lines(entry)))
    for r in fetcher.log:
        print(f"  GET {r['status']} {r['bytes']:>8} B  {r['label']}  {r['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
