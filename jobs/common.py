"""Shared helpers for the scheduled jobs. Standard library only.

The Fetcher is the only thing in this repository that talks to CelesTrak. Its rules are the
site's fetch policy (README, "Data rules"): a fixed User-Agent naming the project and site,
each URL at most once per run, a hard cap of requests per run, no redirects, no retries, a
pause between requests. Bodies are kept in memory; an optional local cache directory (ignored
by git) exists only so a person can inspect what a local run received.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_URL = "https://gpconf.neogy.dev"
USER_AGENT = ("gpconf-site/0.1 (+https://gpconf.neogy.dev; scheduled tracker, at most 10 requests per day; "
              "https://github.com/hneogy/gp-omm-conformance)")
MAX_REQUESTS_PER_RUN = 10
PAUSE_SECONDS = 2.0
TIMEOUT_SECONDS = 60


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def load_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


class PolicyError(RuntimeError):
    """Raised before a request that would break the fetch policy; nothing is sent."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # a 301/302 becomes an HTTPError and is recorded, never followed


class Fetcher:
    def __init__(self, *, max_requests: int = MAX_REQUESTS_PER_RUN, pause: float = PAUSE_SECONDS,
                 cache_dir: str | Path | None = None, opener=None, sleep=time.sleep):
        self.max_requests = max_requests
        self.pause = pause
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.requested: list[str] = []
        self.log: list[dict] = []
        self._opener = opener or urllib.request.build_opener(_NoRedirect)
        self._sleep = sleep

    def get(self, url: str, label: str):
        if url in self.requested:
            raise PolicyError(f"URL requested twice in one run: {url}")
        if len(self.requested) >= self.max_requests:
            raise PolicyError(f"request cap {self.max_requests} reached; refusing {url}")
        if self.requested and self.pause:
            self._sleep(self.pause)
        self.requested.append(url)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        started = utcnow()
        status, body, error = None, b"", None
        try:
            with self._opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as exc:  # 4xx/5xx and refused redirects: recorded, never retried
            status = exc.code
            try:
                body = exc.read()
            except Exception:  # pragma: no cover
                body = b""
        except Exception as exc:  # network failure: recorded, never retried
            error = f"{type(exc).__name__}: {exc}"[:200]
        rec = {"label": label, "url": url, "requested_at": started, "status": status, "bytes": len(body),
               "sha256": hashlib.sha256(body).hexdigest() if body else None, "error": error}
        self.log.append(rec)
        if self.cache_dir is not None and body:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / f"{label}.bin").write_bytes(body)
        return status, body, rec
