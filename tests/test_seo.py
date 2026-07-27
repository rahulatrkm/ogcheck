"""Tests for the SEO page generator — offline, writes to a temp dir."""

from __future__ import annotations

from ogcheck import validate_html
from ogcheck.seo import build, pages


def test_builds_all_pages_plus_sitemap(tmp_path) -> None:
    written = build(out_dir=tmp_path)
    names = {p.name for p in written}
    for page in pages():
        assert page.slug in names
    assert "sitemap.xml" in names
    assert "robots.txt" in names


def test_generated_pages_have_valid_og_tags(tmp_path) -> None:
    # Dog-fooding: our own SEO pages must pass our own validator.
    build(out_dir=tmp_path)
    for page in pages():
        html = (tmp_path / page.slug).read_text(encoding="utf-8")
        report = validate_html(html, url=f"https://ogcheck.dev/{page.slug}", check_image=False)
        errors = [i for i in report.issues if i.severity == "error"]
        assert not errors, f"{page.slug} has OG errors: {errors}"
        assert report.tags["og:title"]


def test_pages_are_interlinked(tmp_path) -> None:
    build(out_dir=tmp_path)
    all_pages = pages()
    for page in all_pages:
        html = (tmp_path / page.slug).read_text(encoding="utf-8")
        # Each page links to every other page (related guides) and home.
        for other in all_pages:
            if other.slug != page.slug:
                assert f'href="/{other.slug}"' in html
        assert 'href="/"' in html


def test_pages_embed_the_live_checker(tmp_path) -> None:
    build(out_dir=tmp_path)
    for page in pages():
        html = (tmp_path / page.slug).read_text(encoding="utf-8")
        assert "/check?url=" in html  # the working checker widget


def test_sitemap_lists_every_page(tmp_path) -> None:
    build(out_dir=tmp_path)
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    for page in pages():
        assert page.slug in sitemap
