"""Tests for the site-health checks (robots.txt + sitemap.xml).

Uses a monkeypatched fetch so no network is required.
"""

from __future__ import annotations

import ogcheck.sitehealth as sh
from ogcheck.sitehealth import validate_robots, validate_sitemap

_GOOD_ROBOTS = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n"
_DISALLOW_ALL = "User-agent: *\nDisallow: /\n"
_GOOD_SITEMAP = (
    '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://example.com/</loc></url>"
    "<url><loc>https://example.com/a</loc></url></urlset>"
)


def _patch(monkeypatch, status, body):
    monkeypatch.setattr(sh, "_fetch", lambda url, timeout: (status, body))


def test_good_robots_passes(monkeypatch) -> None:
    _patch(monkeypatch, 200, _GOOD_ROBOTS)
    r = validate_robots("https://example.com")
    assert r.ok
    assert r.details["sitemaps"] == ["https://example.com/sitemap.xml"]
    assert not [i for i in r.issues if i.severity == "error"]


def test_missing_robots_is_warning(monkeypatch) -> None:
    _patch(monkeypatch, 404, "")
    r = validate_robots("https://example.com")
    assert any(i.code == "missing" for i in r.issues)


def test_disallow_all_is_flagged(monkeypatch) -> None:
    _patch(monkeypatch, 200, _DISALLOW_ALL)
    r = validate_robots("https://example.com")
    assert any(i.code == "disallow_all" for i in r.issues)


def test_unreachable_robots_is_error(monkeypatch) -> None:
    _patch(monkeypatch, None, "")
    r = validate_robots("https://example.com")
    assert not r.ok
    assert any(i.code == "unreachable" for i in r.issues)


def test_good_sitemap_counts_urls(monkeypatch) -> None:
    _patch(monkeypatch, 200, _GOOD_SITEMAP)
    r = validate_sitemap("https://example.com")
    assert r.ok
    assert r.details["url_count"] == 2


def test_invalid_sitemap_xml_is_error(monkeypatch) -> None:
    _patch(monkeypatch, 200, "<not-xml")
    r = validate_sitemap("https://example.com")
    assert not r.ok
    assert any(i.code == "invalid_xml" for i in r.issues)


def test_missing_sitemap_is_warning(monkeypatch) -> None:
    _patch(monkeypatch, 404, "")
    r = validate_sitemap("https://example.com")
    assert any(i.code == "missing" for i in r.issues)


def test_reports_serialize(monkeypatch) -> None:
    _patch(monkeypatch, 200, _GOOD_ROBOTS)
    data = validate_robots("https://example.com").to_dict()
    assert data["kind"] == "robots"
    assert isinstance(data["issues"], list)
