#!/usr/bin/env python3
"""Weekly library-status job for gpconf.neogy.dev.

Runs no-network reproducers against whatever python-sgp4 and Skyfield are installed (the
workflow installs the latest PyPI releases first) and records pass/fail per behaviour, the
versions, and the exception type and message when one is raised. Every input is built on the
CCSDS 502.0-B-3 annex G example values (GOES 9) or comes from the corpus's Alpha-5 vectors;
no provider data is involved and nothing is fetched.

    pip install --upgrade sgp4 skyfield
    python jobs/library_status.py
"""
from __future__ import annotations

import argparse
import io
import json
import platform
import sys
import traceback
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, dump_json, load_json, utcnow  # noqa: E402

LIBRARY_DIR = DATA / "library"
VECTORS = DATA / "vectors" / "alpha5.json"
CORPUS = "https://github.com/hneogy/gp-omm-conformance"
UPSTREAM = "https://github.com/brandon-rhodes/python-sgp4"

# CCSDS 502.0-B-3 annex G OMM example (GOES 9), as the corpus's upstream drafts use it.
ANNEX_G = {
    "OBJECT_NAME": "GOES 9", "OBJECT_ID": "1995-025A", "EPOCH": "2020-03-04T10:34:41.426400",
    "MEAN_MOTION": "1.00273272", "ECCENTRICITY": "0.0005013", "INCLINATION": "3.0539",
    "RA_OF_ASC_NODE": "81.7939", "ARG_OF_PERICENTER": "249.2363", "MEAN_ANOMALY": "150.1602",
    "EPHEMERIS_TYPE": "0", "CLASSIFICATION_TYPE": "U", "NORAD_CAT_ID": "23581",
    "ELEMENT_SET_NO": "925", "REV_AT_EPOCH": "4316", "BSTAR": "0.0001",
    "MEAN_MOTION_DOT": "-0.00000113", "MEAN_MOTION_DDOT": "0.0",
}
NINE_DIGIT_ID = "799501621"  # the nine-digit form CelesTrak uses for supplemental launch nominals

# The same values rendered as a TLE by the corpus renderer, classification set to C (checksums recomputed).
ANNEX_G_TLE_C = (
    "1 23581C 95025A   20064.44075725 -.00000113  00000+0  10000-3 0  9254",
    "2 23581   3.0539  81.7939 0005013 249.2363 150.1602  1.00273272 43169",
)

# Annex G values in CelesTrak's <ndm>-wrapped OMM 2.0 shape with an empty OBJECT_ID, as CelesTrak
# writes analyst objects (corpus docs/upstream/python-sgp4-xml-empty-object-id.md; upstream issue #171).
EMPTY_OBJECT_ID_XML = (
    '<?xml version="1.0" encoding="UTF-8"?><ndm xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:noNamespaceSchemaLocation="https://sanaregistry.org/r/ndmxml_unqualified/ndmxml-2.0.0-master-2.0.xsd">'
    '<omm id="CCSDS_OMM_VERS" version="2.0"><header><CREATION_DATE/><ORIGINATOR/></header><body><segment>'
    '<metadata><OBJECT_NAME>UNKNOWN</OBJECT_NAME><OBJECT_ID></OBJECT_ID><CENTER_NAME>EARTH</CENTER_NAME>'
    '<REF_FRAME>TEME</REF_FRAME><TIME_SYSTEM>UTC</TIME_SYSTEM><MEAN_ELEMENT_THEORY>SGP4</MEAN_ELEMENT_THEORY></metadata>'
    '<data><meanElements><EPOCH>2020-03-04T10:34:41.426400</EPOCH><MEAN_MOTION>1.00273272</MEAN_MOTION>'
    '<ECCENTRICITY>.0005013</ECCENTRICITY><INCLINATION>3.0539</INCLINATION><RA_OF_ASC_NODE>81.7939</RA_OF_ASC_NODE>'
    '<ARG_OF_PERICENTER>249.2363</ARG_OF_PERICENTER><MEAN_ANOMALY>150.1602</MEAN_ANOMALY></meanElements>'
    '<tleParameters><EPHEMERIS_TYPE>0</EPHEMERIS_TYPE><CLASSIFICATION_TYPE>U</CLASSIFICATION_TYPE>'
    '<NORAD_CAT_ID>81011</NORAD_CAT_ID><ELEMENT_SET_NO>999</ELEMENT_SET_NO><REV_AT_EPOCH>4316</REV_AT_EPOCH>'
    '<BSTAR>.1E-3</BSTAR><MEAN_MOTION_DOT>-.113E-5</MEAN_MOTION_DOT><MEAN_MOTION_DDOT>0</MEAN_MOTION_DDOT>'
    '</tleParameters></data></segment></body></omm></ndm>'
)


def _exc(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {str(exc)[:160]}"


def behaviour(bid, title, library, expected, upstream, fn):
    """Run fn(); it returns (passed: bool, detail: str). Exceptions are failures with the exception recorded."""
    rec = {"id": bid, "title": title, "library": library, "expected": expected, "upstream": upstream}
    try:
        passed, detail = fn()
        rec["result"] = "pass" if passed else "fail"
        rec["detail"] = detail
    except (ImportError, AttributeError, NameError) as exc:  # the harness or the environment, not the library (S-030)
        rec["result"] = "error"
        rec["detail"] = _exc(exc)
        rec["traceback_tail"] = traceback.format_exc().strip().splitlines()[-1][:200]
    except Exception as exc:  # the library raised: that is the finding
        rec["result"] = "fail"
        rec["detail"] = _exc(exc)
        rec["traceback_tail"] = traceback.format_exc().strip().splitlines()[-1][:200]
    return rec


def check_sgp4():
    from sgp4 import omm
    from sgp4.api import Satrec, accelerated

    def nine_digit():
        sat = Satrec()
        omm.initialize(sat, dict(ANNEX_G, NORAD_CAT_ID=NINE_DIGIT_ID))
        return sat.satnum == int(NINE_DIGIT_ID), f"loaded; satnum == {sat.satnum == int(NINE_DIGIT_ID)}"

    def empty_object_id():
        fields = next(omm.parse_xml(io.StringIO(EMPTY_OBJECT_ID_XML)))
        sat = Satrec()
        omm.initialize(sat, fields)
        return True, f"loaded; OBJECT_ID parsed as {type(fields.get('OBJECT_ID')).__name__}"

    def classification_omm():
        sat = Satrec()
        omm.initialize(sat, dict(ANNEX_G, CLASSIFICATION_TYPE="C"))
        return sat.classification == "C", f"classification after initialize: {sat.classification!r}"

    def classification_tle():
        sat = Satrec.twoline2rv(*ANNEX_G_TLE_C)
        return sat.classification == "C", f"classification after twoline2rv: {sat.classification!r} (accelerated={accelerated})"

    return [
        behaviour("sgp4-nine-digit-omm", "Nine-digit NORAD_CAT_ID loads through sgp4.omm.initialize", "python-sgp4",
                  f"a record with NORAD_CAT_ID {NINE_DIGIT_ID} loads and satnum equals it",
                  [{"label": "issue #169", "url": f"{UPSTREAM}/issues/169"}, {"label": "PR #170", "url": f"{UPSTREAM}/pull/170"},
                   {"label": "corpus test report on PR #170", "url": f"{UPSTREAM}/pull/170#issuecomment-5755703491"}], nine_digit),
        behaviour("sgp4-empty-object-id-xml", "Empty <OBJECT_ID/> in OMM XML loads through parse_xml and initialize", "python-sgp4",
                  "no exception; an empty OBJECT_ID is a legitimate CelesTrak value for analyst objects",
                  [{"label": "issue #171 (closed 2026-09-24)", "url": f"{UPSTREAM}/issues/171"}, {"label": "PR #172 (merged 2026-09-24; fixed in master, awaiting a release)", "url": f"{UPSTREAM}/pull/172"}], empty_object_id),
        behaviour("sgp4-classification-omm", "CLASSIFICATION_TYPE C survives sgp4.omm.initialize", "python-sgp4",
                  "sat.classification == 'C'",
                  [{"label": "corpus note", "url": f"{CORPUS}/blob/main/docs/upstream/python-sgp4-omm-initialize-drops-classification.md"}], classification_omm),
        behaviour("sgp4-classification-tle", "Classification C survives Satrec.twoline2rv", "python-sgp4",
                  "sat.classification == 'C' (the corpus found the pure-Python build resets it and the accelerated build keeps it)",
                  [{"label": "corpus note", "url": f"{CORPUS}/blob/main/docs/upstream/python-sgp4-omm-initialize-drops-classification.md"}], classification_tle),
    ]


def check_alpha5_vectors(vectors_path: Path):
    from sgp4.alpha5 import from_alpha5, to_alpha5
    v = load_json(vectors_path)
    valid = v["official_examples"] + v["boundaries"] + v["skip_boundaries"] + v["below_100000"]

    def result_of(fn, arg):
        try:
            return ("ok", fn(arg))
        except Exception as exc:
            return ("raised", type(exc).__name__)

    def encode():
        bad = [c["field"] for c in valid if result_of(to_alpha5, c["norad_cat_id"]) != ("ok", c["field"])]
        return not bad, f"{len(valid) - len(bad)}/{len(valid)} encode vectors" + (f"; wrong: {bad[:6]}" if bad else "")

    def decode():
        bad = [c["field"] for c in valid if result_of(from_alpha5, c["field"]) != ("ok", c["norad_cat_id"])]
        return not bad, f"{len(valid) - len(bad)}/{len(valid)} decode vectors" + (f"; wrong: {bad[:6]}" if bad else "")

    def reject_invalid():
        accepted = [c["field"] for c in v["decode_invalid"] if result_of(from_alpha5, c["field"])[0] == "ok"]
        return not accepted, f"{len(v['decode_invalid']) - len(accepted)}/{len(v['decode_invalid'])} invalid fields rejected" + (f"; accepted: {accepted}" if accepted else "")

    def reject_unrepresentable():
        accepted = [c["norad_cat_id"] for c in v["encode_unrepresentable"] if result_of(to_alpha5, c["norad_cat_id"])[0] == "ok"]
        return not accepted, f"{len(v['encode_unrepresentable']) - len(accepted)}/{len(v['encode_unrepresentable'])} unrepresentable numbers rejected" + (f"; accepted: {accepted}" if accepted else "")

    link = [{"label": "corpus case alpha5-encoding-vectors", "url": f"{CORPUS}/tree/main/fixtures/alpha5-encoding-vectors"}]
    return [
        behaviour("sgp4-alpha5-encode", "to_alpha5 matches every valid vector", "python-sgp4", "all valid vectors encode as the Space-Track table says", link, encode),
        behaviour("sgp4-alpha5-decode", "from_alpha5 matches every valid vector", "python-sgp4", "all valid vectors decode to their integer", link, decode),
        behaviour("sgp4-alpha5-reject-invalid", "from_alpha5 rejects I, O, lowercase and malformed fields", "python-sgp4",
                  "every invalid vector raises (Space-Track never uses I or O and defines capital letters only)", link, reject_invalid),
        behaviour("sgp4-alpha5-reject-unrepresentable", "to_alpha5 rejects numbers outside 0-339999", "python-sgp4",
                  "every unrepresentable number raises", link, reject_unrepresentable),
    ]


def check_skyfield():
    from skyfield.api import EarthSatellite, load
    ts = load.timescale(builtin=True)  # bundled leap-second data: no download

    def nine_digit():
        sat = EarthSatellite.from_omm(ts, dict(ANNEX_G, NORAD_CAT_ID=NINE_DIGIT_ID))
        return sat.model.satnum == int(NINE_DIGIT_ID), "loaded through EarthSatellite.from_omm"

    return [behaviour("skyfield-nine-digit-from-omm", "Nine-digit NORAD_CAT_ID loads through EarthSatellite.from_omm", "Skyfield",
                      f"a record with NORAD_CAT_ID {NINE_DIGIT_ID} loads (Skyfield delegates to python-sgp4)",
                      [{"label": "python-sgp4 issue #169", "url": f"{UPSTREAM}/issues/169"}], nine_digit)]


def versions() -> dict:
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for name in ("sgp4", "skyfield"):
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    try:
        from sgp4.api import accelerated
        out["sgp4_accelerated"] = bool(accelerated)
    except Exception:
        out["sgp4_accelerated"] = None
    return out


def run(vectors_path: Path = VECTORS) -> dict:
    checked_at = utcnow()
    results = []
    errors = {}
    for name, fn in (("python-sgp4", check_sgp4), ("alpha5-vectors", lambda: check_alpha5_vectors(vectors_path)), ("Skyfield", check_skyfield)):
        try:
            results.extend(fn())
        except Exception as exc:  # import failure etc.: recorded, the other groups still run
            errors[name] = _exc(exc)
    return {"checked_at": checked_at, "versions": versions(), "inputs": "CCSDS 502.0-B-3 annex G example values; corpus vectors/alpha5.json (v0.1.0)",
            "behaviours": results, "group_errors": errors,
            "counts": {"pass": sum(r["result"] == "pass" for r in results), "fail": sum(r["result"] == "fail" for r in results),
                       "error": sum(r["result"] == "error" for r in results)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(LIBRARY_DIR))
    ap.add_argument("--vectors", default=str(VECTORS))
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir)
    report = run(Path(args.vectors))
    history = load_json(data_dir / "history.json", default=[])
    history.append({"checked_at": report["checked_at"], "versions": report["versions"], "counts": report["counts"],
                    "results": {r["id"]: r["result"] for r in report["behaviours"]}})
    dump_json(data_dir / "latest.json", report)
    dump_json(data_dir / "history.json", history[-104:])
    v = report["versions"]
    print(f"{report['checked_at']} python-sgp4 {v.get('sgp4')} (accelerated={v.get('sgp4_accelerated')}) skyfield {v.get('skyfield')} python {v['python']}")
    for r in report["behaviours"]:
        print(f"  {r['result']:4} {r['id']}: {r['detail']}")
    if report["group_errors"]:
        print("  group errors:", report["group_errors"])
    print(f"  counts: {report['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
