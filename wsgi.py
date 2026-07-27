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

_WEB_DIR = Path(__file__).resolve().parent / "web"
_CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8",
}


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
        urls = query.get("url")
        if not urls or not urls[0].strip():
            body = json.dumps({"error": "provide ?url=<page to check>"}).encode()
            return respond("400 Bad Request", "application/json", body)
        report = validate_url(urls[0].strip())
        return respond("200 OK", "application/json", json.dumps(report.to_dict()).encode())
    if path in ("/robots", "/sitemap"):
        urls = query.get("url")
        if not urls or not urls[0].strip():
            body = json.dumps({"error": "provide ?url=<site>"}).encode()
            return respond("400 Bad Request", "application/json", body)
        from ogcheck.sitehealth import validate_robots, validate_sitemap

        check = validate_robots if path == "/robots" else validate_sitemap
        result = check(urls[0].strip()).to_dict()
        return respond("200 OK", "application/json", json.dumps(result).encode())
    if path.endswith((".html", ".xml", ".txt")) and "/" not in path[1:]:
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
