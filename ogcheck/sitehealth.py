"""Site-health checks that complement the OG validator.

Two more genuinely-useful, pure-stdlib checks that share OGCheck's audience
(developers and SEO-minded site owners) and its zero-dependency, free-to-host
design:

* :func:`validate_robots` — is ``robots.txt`` reachable, parseable, and does it
  point at a sitemap?
* :func:`validate_sitemap` — is ``sitemap.xml`` reachable, valid XML, and does it
  list URLs?

Bundling these turns OGCheck from one tool into a small "site health" suite —
more value per visitor, more SEO landing pages, at no extra hosting cost.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from ogcheck.core import Issue

USER_AGENT = "OGCheck/1.0 (+https://github.com/rahulatrkm/ogcheck)"


@dataclass
class SiteHealthReport:
    """Result of a robots.txt or sitemap.xml check."""

    url: str
    kind: str  # "robots" | "sitemap"
    ok: bool = False
    status: int | None = None
    details: dict[str, object] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "kind": self.kind,
            "ok": self.ok,
            "status": self.status,
            "details": self.details,
            "issues": [i.to_dict() for i in self.issues],
        }


def _origin(url: str) -> str:
    if not urlparse(url).scheme:
        url = "https://" + url
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def _fetch(url: str, *, timeout: float) -> tuple[int | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(2_000_000).decode("utf-8", errors="replace")
            return int(response.status), body
    except urllib.error.HTTPError as exc:
        return int(exc.code), ""
    except Exception:  # noqa: BLE001 - unreachable/DNS/TLS
        return None, ""


def validate_robots(url: str, *, timeout: float = 10.0) -> SiteHealthReport:
    """Check ``<origin>/robots.txt`` — reachable, parseable, points at a sitemap."""
    robots_url = urljoin(_origin(url) + "/", "robots.txt")
    report = SiteHealthReport(url=robots_url, kind="robots")
    status, body = _fetch(robots_url, timeout=timeout)
    report.status = status

    if status is None:
        report.issues.append(Issue("error", "unreachable", "robots.txt is unreachable."))
        return report
    if status == 404:
        report.issues.append(
            Issue("warning", "missing", "No robots.txt (crawlers assume everything is allowed).")
        )
        return report
    if status >= 400:
        report.issues.append(Issue("error", "http_error", f"robots.txt returned HTTP {status}."))
        return report

    directives = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")]
    sitemaps = [ln.split(":", 1)[1].strip() for ln in directives if ln.lower().startswith("sitemap:")]
    has_user_agent = any(ln.lower().startswith("user-agent:") for ln in directives)

    report.details = {"directive_count": len(directives), "sitemaps": sitemaps}
    if not has_user_agent:
        report.issues.append(
            Issue("warning", "no_user_agent", "robots.txt has no User-agent line.")
        )
    if not sitemaps:
        report.issues.append(
            Issue("info", "no_sitemap", "robots.txt does not reference a Sitemap: URL.")
        )
    # Disallow-all is a common accidental foot-gun ("Disallow: /").
    if any(ln.lower().replace(" ", "") == "disallow:/" for ln in directives):
        report.issues.append(
            Issue("warning", "disallow_all", "robots.txt blocks the whole site (Disallow: /).")
        )

    report.ok = not any(i.severity == "error" for i in report.issues)
    return report


def validate_sitemap(url: str, *, timeout: float = 10.0) -> SiteHealthReport:
    """Check ``<origin>/sitemap.xml`` — reachable, valid XML, lists URLs."""
    sitemap_url = urljoin(_origin(url) + "/", "sitemap.xml")
    report = SiteHealthReport(url=sitemap_url, kind="sitemap")
    status, body = _fetch(sitemap_url, timeout=timeout)
    report.status = status

    if status is None:
        report.issues.append(Issue("error", "unreachable", "sitemap.xml is unreachable."))
        return report
    if status == 404:
        report.issues.append(
            Issue("warning", "missing", "No sitemap.xml — search engines crawl less efficiently.")
        )
        return report
    if status >= 400:
        report.issues.append(Issue("error", "http_error", f"sitemap.xml returned HTTP {status}."))
        return report

    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        report.issues.append(Issue("error", "invalid_xml", f"sitemap.xml is not valid XML: {exc}"))
        return report

    # Count <loc> entries (namespace-agnostic).
    locs = [el for el in root.iter() if el.tag.endswith("}loc") or el.tag == "loc"]
    report.details = {"url_count": len(locs), "root": root.tag.split("}")[-1]}
    if not locs:
        report.issues.append(Issue("warning", "empty", "sitemap.xml lists no URLs."))

    report.ok = not any(i.severity == "error" for i in report.issues)
    return report


__all__ = ["SiteHealthReport", "validate_robots", "validate_sitemap"]
