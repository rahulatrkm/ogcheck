"""OGCheck HTTP API — zero-dependency, deploy-anywhere JSON service.

Uses only the standard library so it runs on any free tier (Render/Fly free
container, a cheap VPS, or locally). Endpoints:

* ``GET /``            → the landing page (static HTML)
* ``GET /healthz``     → ``{"status": "ok"}``
* ``GET /check?url=…`` → the validation :class:`~ogcheck.core.Report` as JSON

A tiny in-memory rate limit keeps the free tier from being abused. This is the
paid product's surface; API keys / higher limits are layered on when there is
demand — start simple.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ogcheck.core import validate_url
from ogcheck.keys import rate_for, verify_key

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Per-IP rate limit. The ceiling depends on whether a valid Pro API key is
# presented: free tier gets FREE_RATE, a valid key gets PRO_RATE.
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


class Handler(BaseHTTPRequestHandler):
    server_version = "OGCheck/1.0"

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json({"error": "not found"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self._send_file(_WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        if route == "/healthz":
            self._send_json({"status": "ok"})
            return
        if route == "/check":
            self._handle_check(parse_qs(parsed.query))
            return
        if route in ("/robots", "/sitemap"):
            self._handle_sitehealth(route, parse_qs(parsed.query))
            return
        if route == "/sitemap.xml":
            self._send_file(_WEB_DIR / "sitemap.xml", "application/xml")
            return
        if route == "/robots.txt":
            self._send_file(_WEB_DIR / "robots.txt", "text/plain; charset=utf-8")
            return
        # Social preview. Crawlers reject an image served as anything but image/*.
        if route == "/og.png":
            self._send_file(_WEB_DIR / "og.png", "image/png")
            return
        # Serve any generated SEO page by slug (safe: no path traversal).
        if route.endswith(".html") and "/" not in route[1:]:
            self._send_file(_WEB_DIR / route.lstrip("/"), "text/html; charset=utf-8")
            return
        # IndexNow key file (plain text at site root, proves ownership).
        if route.endswith(".txt") and "/" not in route[1:]:
            self._send_file(_WEB_DIR / route.lstrip("/"), "text/plain; charset=utf-8")
            return
        self._send_json({"error": "not found"}, status=404)

    def _handle_check(self, query: dict[str, list[str]]) -> None:
        ip = self.client_address[0]
        record = verify_key(self.headers.get("X-API-Key"))
        if not _rate_ok(ip, rate_for(record)):
            self._send_json(
                {"error": "rate limit exceeded — upgrade to Pro for higher limits"},
                status=429,
            )
            return
        urls = query.get("url")
        if not urls or not urls[0].strip():
            self._send_json({"error": "provide ?url=<page to check>"}, status=400)
            return
        report = validate_url(urls[0].strip())
        self._send_json(report.to_dict())

    def _handle_sitehealth(self, route: str, query: dict[str, list[str]]) -> None:
        ip = self.client_address[0]
        record = verify_key(self.headers.get("X-API-Key"))
        if not _rate_ok(ip, rate_for(record)):
            self._send_json({"error": "rate limit exceeded — upgrade to Pro"}, status=429)
            return
        urls = query.get("url")
        if not urls or not urls[0].strip():
            self._send_json({"error": "provide ?url=<site>"}, status=400)
            return
        from ogcheck.sitehealth import validate_robots, validate_sitemap

        check = validate_robots if route == "/robots" else validate_sitemap
        self._send_json(check(urls[0].strip()).to_dict())

    def log_message(self, *args: object) -> None:  # keep the console quiet
        return


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API server (blocking)."""
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"OGCheck API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":  # pragma: no cover
    import os

    serve(port=int(os.environ.get("PORT", "8000")))
