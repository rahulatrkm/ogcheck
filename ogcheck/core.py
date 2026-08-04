"""OGCheck — the core Open Graph / social-preview validator.

Pure standard library (no third-party deps) so it runs and deploys anywhere for
free. Given a URL, it:

* fetches the HTML,
* parses Open Graph, Twitter Card, and basic SEO/JSON-LD tags,
* **verifies the referenced ``og:image`` actually returns HTTP 200** (the single
  most common silently-broken thing — the pain the research surfaced),
* scores the result and returns concrete, actionable issues.

This is the genuinely useful bit: it catches the "your link preview is broken and
nothing told you" problem before it costs someone traffic. It is deliberately
stateless and side-effect free (network reads only), which makes it cheap to host
and easy to test.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .safefetch import BlockedURL, open_url

USER_AGENT = "OGCheck/1.0 (+https://github.com/automaton/ogcheck)"

# The tags that matter for a correct social preview, and the severity if missing.
_REQUIRED_OG = {
    "og:title": "error",
    "og:description": "warning",
    "og:image": "error",
    "og:url": "warning",
    "og:type": "info",
}
_RECOMMENDED_TWITTER = {
    "twitter:card": "warning",
    "twitter:title": "info",
    "twitter:description": "info",
    "twitter:image": "info",
}


@dataclass
class Issue:
    """A single actionable finding."""

    severity: str  # error | warning | info
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "code": self.code, "message": self.message}


@dataclass
class Report:
    """The full validation result for a URL."""

    url: str
    ok: bool = False
    # None means the page could not be fetched, which is different from scoring zero.
    score: int | None = None
    title: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    image_url: str | None = None
    image_status: int | None = None
    issues: list[Issue] = field(default_factory=list)
    fetch_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "ok": self.ok,
            "score": self.score,
            "title": self.title,
            "tags": self.tags,
            "image_url": self.image_url,
            "image_status": self.image_status,
            "issues": [i.to_dict() for i in self.issues],
            "fetch_error": self.fetch_error,
        }


class _MetaParser(HTMLParser):
    """Extract <meta property/name=...> and <title> and <link rel=canonical>."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: dict[str, str] = {}
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = a.get("property") or a.get("name")
            content = a.get("content")
            if key and content:
                self.tags[key.lower()] = content
        elif tag == "title":
            self._in_title = True
        elif tag == "link" and a.get("rel", "").lower() == "canonical" and a.get("href"):
            self.tags["link:canonical"] = a["href"]

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip() and self.title is None:
            self.title = data.strip()


def _fetch_text(url: str, *, timeout: float, max_bytes: int = 2_000_000) -> str:
    _status, body, charset, _final = open_url(
        url, timeout=timeout, max_bytes=max_bytes, user_agent=USER_AGENT
    )
    return body.decode(charset or "utf-8", errors="replace")


def _check_image(url: str, *, timeout: float) -> int | None:
    """Return the HTTP status of the image URL, or None if unreachable."""
    try:
        status, _body, _charset, _final = open_url(
            url, timeout=timeout, max_bytes=1, user_agent=USER_AGENT
        )
        return int(status)
    except BlockedURL:
        # An og:image pointing inside the network is not a status to report.
        return None
    except Exception:
        return None


def validate_url(url: str, *, timeout: float = 10.0, check_image: bool = True) -> Report:
    """Validate the social-preview tags of ``url`` and return a :class:`Report`."""
    report = Report(url=url)
    if not urlparse(url).scheme:
        url = "https://" + url
        report.url = url

    try:
        html = _fetch_text(url, timeout=timeout)
    except BlockedURL as exc:
        report.fetch_error = str(exc)
        report.issues.append(Issue("error", "fetch_blocked", str(exc)))
        return report
    except Exception:
        # The wording is deliberately the same whatever went wrong. Echoing the
        # socket error told a caller the difference between a refused port, a
        # filtered one and a timeout, which is a port scanner with extra steps.
        message = "Could not fetch the page."
        report.fetch_error = message
        report.issues.append(Issue("error", "fetch_failed", message))
        return report

    return validate_html(html, url=report.url, timeout=timeout, check_image=check_image)


def validate_html(
    html: str,
    *,
    url: str = "",
    timeout: float = 10.0,
    check_image: bool = True,
) -> Report:
    """Validate already-fetched ``html`` (no network for parsing).

    Exposed for tests and for callers that already have the HTML. Image checking
    still requires the network unless ``check_image=False``.
    """
    report = Report(url=url)
    parser = _MetaParser()
    parser.feed(html)
    report.tags = parser.tags
    report.title = parser.tags.get("og:title") or parser.title

    _score_tags(report)

    if check_image:
        _validate_image(report, timeout=timeout)

    # Final score & pass/fail: any error caps the pass.
    has_error = any(i.severity == "error" for i in report.issues)
    report.ok = not has_error
    report.score = _compute_score(report)
    return report


def _score_tags(report: Report) -> None:
    for tag, severity in _REQUIRED_OG.items():
        if tag not in report.tags:
            report.issues.append(
                Issue(severity, f"missing:{tag}", f"Missing {tag} — social previews need it.")
            )
    for tag, severity in _RECOMMENDED_TWITTER.items():
        if tag not in report.tags and "twitter:card" not in report.tags:
            # Only nudge about Twitter tags once (via the card) to avoid noise.
            if tag == "twitter:card":
                report.issues.append(
                    Issue(
                        severity,
                        f"missing:{tag}",
                        "No Twitter Card tags — X previews may be plain.",
                    )
                )
            break


def _validate_image(report: Report, *, timeout: float) -> None:
    image = report.tags.get("og:image") or report.tags.get("twitter:image")
    if not image:
        return
    image = urljoin(report.url, image)
    report.image_url = image
    status = _check_image(image, timeout=timeout)
    report.image_status = status
    if status is None:
        report.issues.append(
            Issue("error", "image_unreachable", f"og:image is unreachable: {image}")
        )
    elif status >= 400:
        report.issues.append(
            Issue("error", "image_broken", f"og:image returns HTTP {status}: {image}")
        )


def _compute_score(report: Report) -> int:
    """A 0-100 score: start at 100, subtract per issue by severity."""
    penalty = {"error": 30, "warning": 10, "info": 3}
    score = 100
    for issue in report.issues:
        score -= penalty.get(issue.severity, 5)
    return max(0, score)


__all__ = ["Issue", "Report", "validate_html", "validate_url"]
