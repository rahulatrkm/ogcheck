"""OGCheck static SEO page generator — pure standard library, no deps.

Renders a small set of genuinely-helpful landing pages targeting the exact terms
people search *when their link preview is already broken* ("og:image not showing
on twitter", "check open graph tags", ...). Each page carries real advice plus a
live checker widget and a call to action, so it earns the visit and converts.

Run: ``python -m ogcheck.seo`` → writes HTML into ``web/`` and a ``sitemap.xml``.

Distribution, not code, is what makes a bootstrapped product earn — these pages
are the free, evergreen top of that funnel.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass, field
from pathlib import Path

# The public base URL, used for canonical links + sitemap. Override in
# deployment with OGCHECK_SITE_URL so search engines see the real domain.
SITE_URL = os.environ.get("OGCHECK_SITE_URL", "https://ogcheck.dev").rstrip("/")
_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@dataclass(frozen=True)
class Page:
    """One SEO landing page."""

    slug: str  # output filename, e.g. "og-image-not-showing.html"
    title: str  # <title> and H1
    description: str  # meta description
    intro: str  # opening paragraph (HTML allowed)
    sections: list[tuple[str, str]] = field(default_factory=list)  # (heading, html body)
    keywords: str = ""


def _related_links(pages: list[Page], current: Page) -> str:
    items = [
        f'<li><a href="/{p.slug}">{html.escape(p.title)}</a></li>'
        for p in pages
        if p.slug != current.slug
    ]
    return "<ul>" + "".join(items) + "</ul>"


def _render(page: Page, pages: list[Page]) -> str:
    canonical = f"{SITE_URL}/{page.slug}"
    sections_html = "".join(
        f"<h2>{html.escape(h)}</h2>\n{body}\n" for h, body in page.sections
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(page.title)} · OGCheck</title>
  <meta name="description" content="{html.escape(page.description)}" />
  <meta name="keywords" content="{html.escape(page.keywords)}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:title" content="{html.escape(page.title)}" />
  <meta property="og:description" content="{html.escape(page.description)}" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{SITE_URL}/preview.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
            color:#0f172a; background:#f8fafc; line-height:1.65; }}
    .wrap {{ max-width:720px; margin:0 auto; padding:40px 20px 64px; }}
    h1 {{ font-size:2rem; line-height:1.2; }}
    h2 {{ margin-top:32px; font-size:1.3rem; }}
    a {{ color:#2563eb; }}
    code {{ background:#eef2ff; padding:2px 6px; border-radius:6px; font-size:.9em; }}
    pre {{ background:#0f172a; color:#e2e8f0; padding:14px; border-radius:10px; overflow:auto; font-size:.85rem; }}
    .try {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin:28px 0; }}
    .row {{ display:flex; gap:8px; }}
    input {{ flex:1; padding:11px 13px; border:1px solid #cbd5e1; border-radius:10px; font-size:1rem; }}
    button {{ background:#2563eb; color:#fff; border:0; border-radius:10px; padding:11px 18px; font-weight:600; cursor:pointer; }}
    #out {{ display:none; margin-top:12px; }}
    nav.crumb {{ font-size:.85rem; color:#64748b; margin-bottom:16px; }}
    .related {{ margin-top:44px; border-top:1px solid #e2e8f0; padding-top:20px; }}
    footer {{ color:#64748b; font-size:.85rem; margin-top:40px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <nav class="crumb"><a href="/">OGCheck</a> · guide</nav>
    <h1>{html.escape(page.title)}</h1>
    <p>{page.intro}</p>

    <div class="try">
      <strong>Check your page now — free, no signup:</strong>
      <form id="f" class="row" style="margin-top:10px">
        <input id="u" type="url" placeholder="https://your-site.com/page" required />
        <button type="submit">Check</button>
      </form>
      <pre id="out"></pre>
    </div>

    {sections_html}

    <div class="related">
      <h2>Related guides</h2>
      {_related_links(pages, page)}
      <p><a href="/">← Back to OGCheck</a></p>
    </div>

    <footer>OGCheck — a free Open Graph / social-preview validator. Built by an autonomous enterprise.</footer>
  </div>
  <script>
    const f=document.getElementById('f'),o=document.getElementById('out');
    f.addEventListener('submit',async e=>{{e.preventDefault();o.style.display='block';o.textContent='Checking…';
      try{{const r=await fetch('/check?url='+encodeURIComponent(document.getElementById('u').value));
        o.textContent=JSON.stringify(await r.json(),null,2);}}catch(x){{o.textContent='Error: '+x;}}}});
  </script>
</body>
</html>
"""


def pages() -> list[Page]:
    """The SEO landing pages. Genuinely helpful content that earns the click."""
    return [
        Page(
            slug="og-image-not-showing.html",
            title="og:image not showing on Facebook, Twitter/X or LinkedIn — how to fix it",
            description=(
                "Your og:image isn't showing in link previews? The usual causes are a "
                "404 image, a relative URL, wrong dimensions, or a cached old preview. "
                "Check yours free and fix it in minutes."
            ),
            keywords="og:image not showing, open graph image not working, link preview broken",
            intro=(
                "You added an <code>og:image</code>, but the link preview is blank or wrong on "
                "Facebook, X/Twitter, LinkedIn, WhatsApp, or Slack. In almost every case it's one "
                "of five specific things — and the most common is that the image URL simply "
                "<strong>doesn't return HTTP 200</strong>. Here's how to find and fix it."
            ),
            sections=[
                (
                    "1. The image URL 404s (most common)",
                    "<p>Paste your page into the checker above. If it reports "
                    "<code>image_broken</code> or <code>image_unreachable</code>, the URL in your "
                    "<code>og:image</code> tag doesn't load. Open the exact image URL in a private "
                    "browser tab — if it fails there, the crawler fails too.</p>",
                ),
                (
                    "2. You used a relative URL",
                    "<p>Open Graph requires an <strong>absolute</strong> URL. "
                    "<code>&lt;meta property=\"og:image\" content=\"/img/card.png\"&gt;</code> is "
                    "wrong; it must be <code>https://your-site.com/img/card.png</code>.</p>",
                ),
                (
                    "3. The platform cached an old preview",
                    "<p>Facebook, LinkedIn and X aggressively cache. After fixing the tag, re-scrape "
                    "with the platform's debugger (Facebook Sharing Debugger, LinkedIn Post "
                    "Inspector) to bust the cache.</p>",
                ),
                (
                    "4. Wrong dimensions or file type",
                    "<p>Use a PNG or JPG at <strong>1200×630</strong>. SVGs and tiny images are often "
                    "ignored. Keep it under ~5&nbsp;MB.</p>",
                ),
                (
                    "5. Blocked crawlers",
                    "<p>If <code>robots.txt</code> or auth blocks the crawler, it can't fetch the "
                    "image. Make the page and image publicly reachable.</p>",
                ),
                (
                    "Catch it automatically",
                    "<p>Add OGCheck to CI so a broken preview <strong>fails your build</strong> "
                    "before it ships:</p><pre>python -m ogcheck https://your-site.com/page</pre>",
                ),
            ],
        ),
        Page(
            slug="check-open-graph-tags.html",
            title="How to check your Open Graph tags (free validator)",
            description=(
                "A free way to check your Open Graph and Twitter Card tags — and confirm your "
                "og:image actually loads. No signup. Use it as a CLI or CI check."
            ),
            keywords="check open graph tags, open graph validator, og tags checker",
            intro=(
                "Open Graph tags control how your links look when shared. This free validator parses "
                "your <code>og:*</code> and <code>twitter:*</code> tags, scores them, and — unlike most "
                "checkers — <strong>verifies the image actually returns 200</strong>."
            ),
            sections=[
                (
                    "The tags that matter",
                    "<p><code>og:title</code>, <code>og:description</code>, <code>og:image</code>, "
                    "<code>og:url</code>, <code>og:type</code>, plus <code>twitter:card</code> for X. "
                    "Missing <code>og:title</code> or <code>og:image</code> breaks the preview.</p>",
                ),
                (
                    "Check it in your terminal or CI",
                    "<pre>python -m ogcheck https://your-site.com</pre>"
                    "<p>It exits non-zero on a broken preview, so it doubles as a CI gate.</p>",
                ),
            ],
        ),
        Page(
            slug="social-preview-validator.html",
            title="Social preview validator — test how your link will look",
            description=(
                "Test how your link will appear on X/Twitter, LinkedIn, Facebook, Slack and "
                "WhatsApp. Free social preview validator that also checks your og:image loads."
            ),
            keywords="social preview validator, link preview test, twitter card validator",
            intro=(
                "Before you share a link, test how it renders. This free validator inspects your "
                "social-preview tags across platforms and flags the exact problems — including the "
                "one most tools miss: <strong>an og:image that doesn't load</strong>."
            ),
            sections=[
                (
                    "Why previews differ by platform",
                    "<p>X uses <code>twitter:card</code>; Facebook/LinkedIn/Slack use Open Graph. If "
                    "Twitter tags are absent, X falls back to OG — but a summary card, not a large "
                    "image. Set <code>twitter:card = summary_large_image</code> for the big preview.</p>",
                ),
                (
                    "Monitor it, don't just check once",
                    "<p>Previews break silently when an image is moved or a CDN changes. Add the check "
                    "to CI (or Pro monitoring) so you find out immediately, not weeks later when "
                    "traffic drops.</p>",
                ),
            ],
        ),
    ]


def build(out_dir: Path | None = None) -> list[Path]:
    """Render all SEO pages + sitemap.xml + robots.txt. Returns written paths."""
    out = out_dir or _WEB_DIR
    out.mkdir(parents=True, exist_ok=True)
    all_pages = pages()
    written: list[Path] = []

    for page in all_pages:
        path = out / page.slug
        path.write_text(_render(page, all_pages), encoding="utf-8")
        written.append(path)

    # sitemap.xml — helps search engines find every page.
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/{p.slug}" for p in all_pages]
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>\n"
    )
    sm = out / "sitemap.xml"
    sm.write_text(sitemap, encoding="utf-8")
    written.append(sm)

    robots = out / "robots.txt"
    robots.write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    written.append(robots)

    return written


if __name__ == "__main__":  # pragma: no cover
    paths = build()
    for p in paths:
        print(f"wrote {p.relative_to(_WEB_DIR.parent)}")


__all__ = ["SITE_URL", "Page", "build", "pages"]
