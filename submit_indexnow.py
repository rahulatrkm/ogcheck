"""Submit OGCheck URLs to search engines via IndexNow — no account required.

IndexNow (https://www.indexnow.org/) is supported by Bing and Yandex: host a key
file at the site root, then POST the URLs you want crawled. This actively asks
search engines to index the site without owning a Search Console property. Pure
standard library.

    python submit_indexnow.py
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

HOST = "ogcheck-app.azurewebsites.net"
KEY = "0f12fa59ec055b54eefb37fa82176ff3"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"

URLS = [
    f"https://{HOST}/",
    f"https://{HOST}/og-image-not-showing.html",
    f"https://{HOST}/check-open-graph-tags.html",
    f"https://{HOST}/social-preview-validator.html",
    f"https://{HOST}/robots-txt-checker.html",
    f"https://{HOST}/sitemap-validator.html",
    f"https://{HOST}/sitemap.xml",
]

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]


def submit(endpoint: str) -> int:
    payload = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": URLS}
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"{endpoint} -> {r.status} {r.reason}")
            return 0
    except urllib.error.HTTPError as exc:
        print(f"{endpoint} -> {exc.code} {exc.reason}: {exc.read().decode()[:200]}")
        return 0 if exc.code in (200, 202) else 1


def main() -> int:
    rc = 0
    for ep in ENDPOINTS:
        rc |= submit(ep)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
