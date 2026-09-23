#!/usr/bin/env python3
"""Build gpconf.neogy.dev into dist/.

Static output only: Jinja2 templates from site/templates, static files from site/static, the
jobs' computed JSON from data/. Pages are rendered with the latest tracker and library data so
they work without JavaScript; scripts add charts and the client-side tools.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined, select_autoescape

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DATA = ROOT / "data"
DIST = ROOT / "dist"
SITE_URL = "https://gpconf.neogy.dev"

PAGES = [
    ("index", "index.html", "/"),
    ("migration", "migration/index.html", "/migration/"),
    ("findings", "findings/index.html", "/findings/"),
    ("tracker", "tracker/index.html", "/tracker/"),
    ("library", "library/index.html", "/library/"),
    ("tools", "tools/index.html", "/tools/"),
    ("about", "about/index.html", "/about/"),
    ("activity", "activity/index.html", "/activity/"),
    ("404", "404.html", "/404.html"),
]
NAV = [
    {"id": "migration", "href": "/migration/", "simple": "The story", "technical": "The migration"},
    {"id": "findings", "href": "/findings/", "label": "Findings"},
    {"id": "tracker", "href": "/tracker/", "label": "Live tracker"},
    {"id": "library", "href": "/library/", "label": "Library status"},
    {"id": "tools", "href": "/tools/", "label": "Tools"},
    {"id": "activity", "href": "/activity/", "label": "Activity"},
    {"id": "about", "href": "/about/", "label": "How it was built"},
]
CORPUS = {
    "repo": "https://github.com/hneogy/gp-omm-conformance",
    "blob": "https://github.com/hneogy/gp-omm-conformance/blob/main",
    "tree": "https://github.com/hneogy/gp-omm-conformance/tree/main",
    "concept_doi": "10.5281/zenodo.22867654",
    "concept_doi_url": "https://doi.org/10.5281/zenodo.22867654",
    "version_doi": "10.5281/zenodo.22906966",
    "version_doi_url": "https://zenodo.org/records/22906966",
    "version": "0.2.0",
    "version_doi_version": "0.2.0",  # the release the version DOI above belongs to; keep the three in step at each release
    "issue_171": "https://github.com/brandon-rhodes/python-sgp4/issues/171",
    "issue_169": "https://github.com/brandon-rhodes/python-sgp4/issues/169",
    "pr_170": "https://github.com/brandon-rhodes/python-sgp4/pull/170",
    "pr_170_comment": "https://github.com/brandon-rhodes/python-sgp4/pull/170#issuecomment-5755703491",
    "pr_172": "https://github.com/brandon-rhodes/python-sgp4/pull/172",
    "site_repo": None,
}
HEADERS = """/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
  Cache-Control: public, max-age=300

/data/*
  Cache-Control: public, max-age=600
  Access-Control-Allow-Origin: *

/static/*
  Cache-Control: public, max-age=86400
"""


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_int(value):
    if value is None or isinstance(value, Undefined):  # a metric absent from a failed day renders as a dash, not a crash
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def fmt_ts(value, with_time=True):
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return dt.strftime("%Y-%m-%d %H:%M UTC") if with_time else dt.strftime("%Y-%m-%d")


def yesno(value):
    if isinstance(value, Undefined):
        return "unknown"
    return {True: "yes", False: "no"}.get(value, "unknown")


def context() -> dict:
    tracker_latest = load(DATA / "tracker" / "latest.json")
    tracker_history = load(DATA / "tracker" / "history.json", [])
    library_latest = load(DATA / "library" / "latest.json")
    library_history = load(DATA / "library" / "history.json", [])
    return {
        "site_url": SITE_URL,
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "nav": NAV,
        "corpus": CORPUS,
        "tracker": tracker_latest,
        "tracker_history": tracker_history,
        "library": library_latest,
        "library_history": library_history,
        "sources": load(ROOT / "jobs" / "sources.json"),
        "examples": load(SITE / "content" / "examples.json"),
        "failures": load(SITE / "content" / "failures.json"),
        "ecosystem": load(SITE / "content" / "ecosystem.json", {"entries": []}),
        "alpha5_vectors": load(DATA / "vectors" / "alpha5.json"),
        "timeline": load(DATA / "timeline.json", {"events": []}),
    }


def main(out: Path = DIST) -> Path:
    env = Environment(loader=FileSystemLoader(str(SITE / "templates")), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update({"fmt_int": fmt_int, "fmt_ts": fmt_ts, "yesno": yesno})
    ctx = context()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for page_id, rel, href in PAGES:
        html = env.get_template(f"pages/{page_id}.html").render(page_id=page_id, page_href=href, **ctx)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    shutil.copytree(SITE / "static", out / "static")
    for sub in ("tracker", "library", "vectors"):
        src = DATA / sub
        if src.exists():
            (out / "data" / sub).mkdir(parents=True, exist_ok=True)
            for f in src.glob("*.json"):
                shutil.copy(f, out / "data" / sub / f.name)
    shutil.copy(SITE / "content" / "examples.json", out / "data" / "examples.json")
    (out / "_headers").write_text(HEADERS)
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    urls = "".join(f"  <url><loc>{SITE_URL}{href}</loc></url>\n" for _, _, href in PAGES if not href.endswith(".html"))
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    return out


if __name__ == "__main__":
    target = main(Path(sys.argv[1]) if len(sys.argv) > 1 else DIST)
    n = sum(1 for _ in target.rglob("*") if _.is_file())
    print(f"built {n} files into {target}")
