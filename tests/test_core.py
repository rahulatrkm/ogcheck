"""Tests for OGCheck core — offline, using fixture HTML (no network)."""

from __future__ import annotations

from ogcheck.core import validate_html

_GOOD = """
<html><head>
  <title>My Great Post</title>
  <meta property="og:title" content="My Great Post" />
  <meta property="og:description" content="A wonderful read." />
  <meta property="og:image" content="https://example.com/img.png" />
  <meta property="og:url" content="https://example.com/post" />
  <meta property="og:type" content="article" />
  <meta name="twitter:card" content="summary_large_image" />
</head><body>hi</body></html>
"""

_MISSING = "<html><head><title>Bare</title></head><body>hi</body></html>"

_MISSING_IMAGE = """
<html><head>
  <meta property="og:title" content="No image" />
  <meta property="og:description" content="desc" />
  <meta property="og:url" content="https://example.com" />
  <meta property="og:type" content="website" />
</head></html>
"""


def test_good_page_passes_with_high_score() -> None:
    report = validate_html(_GOOD, url="https://example.com/post", check_image=False)
    assert report.ok
    assert report.score >= 95
    assert report.title == "My Great Post"
    assert report.tags["og:image"] == "https://example.com/img.png"
    assert not [i for i in report.issues if i.severity == "error"]


def test_missing_tags_fail_with_actionable_issues() -> None:
    report = validate_html(_MISSING, url="https://example.com", check_image=False)
    assert not report.ok  # missing og:title and og:image are errors
    codes = {i.code for i in report.issues}
    assert "missing:og:title" in codes
    assert "missing:og:image" in codes
    assert report.score < 50


def test_missing_image_is_an_error() -> None:
    report = validate_html(_MISSING_IMAGE, url="https://example.com", check_image=False)
    assert not report.ok
    assert any(i.code == "missing:og:image" for i in report.issues)


def test_title_falls_back_to_html_title() -> None:
    report = validate_html(_MISSING, url="https://example.com", check_image=False)
    assert report.title == "Bare"


def test_report_serializes() -> None:
    report = validate_html(_GOOD, url="https://example.com/post", check_image=False)
    data = report.to_dict()
    assert data["ok"] is True
    assert isinstance(data["issues"], list)
    assert data["score"] == report.score


def test_image_check_flags_broken_image(monkeypatch) -> None:
    # Inject a fake image checker that reports a 404 — no real network.
    from ogcheck import core

    monkeypatch.setattr(core, "_check_image", lambda url, timeout: 404)
    report = validate_html(_GOOD, url="https://example.com/post", check_image=True)
    assert not report.ok
    assert report.image_status == 404
    assert any(i.code == "image_broken" for i in report.issues)


def test_image_check_passes_on_200(monkeypatch) -> None:
    from ogcheck import core

    monkeypatch.setattr(core, "_check_image", lambda url, timeout: 200)
    report = validate_html(_GOOD, url="https://example.com/post", check_image=True)
    assert report.ok
    assert report.image_status == 200
