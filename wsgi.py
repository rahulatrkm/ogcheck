"""App Service / WSGI entrypoint for OGCheck.

Azure App Service (Linux, Python) runs a WSGI app via gunicorn. OGCheck's core
is framework-free, so this thin WSGI adapter exposes the same routes as the
stdlib server (landing page, SEO pages, /check, /healthz) without any extra
dependency. ``app`` is the WSGI callable App Service looks for.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

from ogcheck.core import validate_url
from ogcheck.keys import rate_for, verify_key

_WEB_DIR = Path(__file__).resolve().parent / "web"
_CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
}

# Per-IP rate limiting for the deployed app (free vs. Pro by API key).
import time  # noqa: E402
from collections import defaultdict  # noqa: E402

_RATE_WINDOW_S = 60.0
_hits: dict[str, list[float]] = defaultdict(list)


def _rate_ok(ip: str, limit: int) -> bool:
    now = time.monotonic()
    window = _hits[ip]
    window[:] = [t for t in window if now - t < _RATE_WINDOW_S]
    if len(window) >= limit:
        return False
    window.append(now)
    return True


def client_ip(environ) -> str:
    """The address to rate limit, read the only way that is not spoofable.

    Behind Render every request arrives from the same proxy address, so using
    REMOTE_ADDR alone put every user of the service in one shared bucket: thirty
    requests from anyone locked out everybody. The obvious repair -- trust
    X-Forwarded-For -- is worse, because the client sends that header and the
    proxy only *appends* to it, so `X-Forwarded-For: <anything>` on each request
    lands in a fresh bucket every time and the limit stops existing.

    The last entry is the one the proxy in front of us wrote, and it is the only
    part of the header a caller cannot choose.
    """
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]
    return environ.get("REMOTE_ADDR", "?")


def _file_response(name: str):
    path = _WEB_DIR / name
    if not path.exists() or "/" in name:
        return None
    ctype = _CONTENT.get(path.suffix, "application/octet-stream")
    return ctype, path.read_bytes()


def app(environ, start_response):
    """Minimal WSGI app — same routes as the stdlib server."""
    path = environ.get("PATH_INFO", "/")
    query = parse_qs(environ.get("QUERY_STRING", ""))
    ip = client_ip(environ)
    api_record = verify_key(environ.get("HTTP_X_API_KEY"))

    def respond(status: str, ctype: str, body: bytes):
        start_response(status, [
            ("Content-Type", ctype),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [body]

    if path in ("/", "/index.html"):
        got = _file_response("index.html")
        if got:
            return respond("200 OK", got[0], got[1])
    if path == "/healthz":
        return respond("200 OK", "application/json", b'{"status": "ok"}')
    if path == "/check":
        if not _rate_ok(ip, rate_for(api_record)):
            return respond("429 Too Many Requests", "application/json",
                           b'{"error": "rate limit exceeded - upgrade to Pro for higher limits"}')
        urls = query.get("url")
        if not urls or not urls[0].strip():
            body = json.dumps({"error": "provide ?url=<page to check>"}).encode()
            return respond("400 Bad Request", "application/json", body)
        report = validate_url(urls[0].strip())
        return respond("200 OK", "application/json", json.dumps(report.to_dict()).encode())
    if path in ("/robots", "/sitemap"):
        if not _rate_ok(ip, rate_for(api_record)):
            return respond("429 Too Many Requests", "application/json",
                           b'{"error": "rate limit exceeded - upgrade to Pro"}')
        urls = query.get("url")
        if not urls or not urls[0].strip():
            body = json.dumps({"error": "provide ?url=<site>"}).encode()
            return respond("400 Bad Request", "application/json", body)
        from ogcheck.sitehealth import validate_robots, validate_sitemap

        check = validate_robots if path == "/robots" else validate_sitemap
        result = check(urls[0].strip()).to_dict()
        return respond("200 OK", "application/json", json.dumps(result).encode())
    if path.endswith((".html", ".xml", ".txt", ".png")) and "/" not in path[1:]:
        got = _file_response(path.lstrip("/"))
        if got:
            return respond("200 OK", got[0], got[1])

    return respond("404 Not Found", "application/json", b'{"error": "not found"}')


# Generate SEO pages at import time so App Service serves them (idempotent).
import contextlib

with contextlib.suppress(Exception):  # pragma: no cover - deployment convenience
    from ogcheck.seo import build

    build()


__all__ = ["app"]
