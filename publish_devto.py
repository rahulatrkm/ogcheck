"""Publish the OGCheck launch article to dev.to via its official API.

This is the same legitimate pattern as using the authenticated `gh` CLI: the
OWNER supplies their own dev.to API key (their identity, their account), and this
script does the mechanical work of publishing. It uses dev.to's official,
sanctioned Articles API — not scraping or automated account creation.

Get a key (owner, one-time): https://dev.to/settings/extensions -> "DEV Community
API Keys" -> Generate. Then:

    DEVTO_API_KEY=<key> python publish_devto.py

Pass --publish to go live immediately; omit it to create a draft you can review.
Pure standard library — no dependencies.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

LIVE_URL = "https://ogcheck.onrender.com"
REPO_URL = "https://github.com/rahulatrkm/ogcheck"

# --- Article 1: the launch/social-preview piece (already published) ---------
BODY_MARKDOWN = f"""\
## The silent bug that quietly kills your click-through

You add `<meta property="og:image" content="...">`, the preview looks fine when
you test it, you ship. Weeks later the image gets moved, the CDN path changes, or
it was a relative URL all along — and now every share is a blank card. Your
click-through quietly drops and **nothing alerts you.**

## Catch it in one request (or in CI)

I built [OGCheck]({LIVE_URL}) to catch exactly this. It parses your Open Graph +
Twitter Card tags, scores them, and — the key part most validators skip —
**actually requests the `og:image` to confirm it returns HTTP 200.**

```bash
python -m ogcheck https://your-site.com/blog/post
# exits non-zero if og:image 404s or required tags are missing -> perfect for CI
```

There's a JSON API and a GitHub Action too:

```yaml
- uses: rahulatrkm/ogcheck@v1
  with:
    url: https://your-site.com
```

## The 5 things that actually break previews

1. The image URL 404s (most common)
2. A relative URL instead of an absolute one
3. A cached old preview on the platform (re-scrape to bust it)
4. Wrong dimensions or file type (use PNG/JPG at 1200×630)
5. Crawlers blocked by robots.txt or auth

## It's a small "site health" suite now

Same free API also checks the other things that silently break how your site
shows up:

- `GET /check?url=…` — social preview (Open Graph + og:image loads)
- `GET /robots?url=…` — robots.txt (catches an accidental site-wide `Disallow: /`)
- `GET /sitemap?url=…` — sitemap.xml (valid XML, reachable, lists URLs)

It's free, zero-dependency (pure Python stdlib), and open source:
[{REPO_URL}]({REPO_URL})

If you monitor a lot of pages, I'm thinking about a paid "watch these URLs and
alert me when a preview breaks" tier — would that be useful? Honest feedback
very welcome, especially on false positives.
"""

# --- Article 2: robots.txt (targets a different, high-intent search term) ----
BODY_ROBOTS = f"""\
## One line can hide your whole site from Google

`Disallow: /` in your `robots.txt` tells every crawler to ignore your entire
site. It's shockingly common — usually left over from a staging config that got
copied to production. And nothing tells you: your pages just quietly stop
ranking.

I kept getting bitten by `robots.txt` and `sitemap.xml` issues, so I added free
checks for them to [OGCheck]({LIVE_URL}).

## Check your robots.txt in one request

```bash
curl "{LIVE_URL}/robots?url=https://your-site.com"
```

It confirms the file is **reachable**, **parseable**, flags a **site-wide block**,
and tells you whether it points at your **sitemap**.

## The robots.txt mistakes that quietly cost you traffic

1. **`Disallow: /`** — blocks everything. The classic staging-to-prod accident.
2. **Missing file** — crawlers assume everything is allowed, which may expose
   pages you didn't mean to (and you lose the chance to point at your sitemap).
3. **No `Sitemap:` line** — search engines crawl your site less efficiently.
4. **Blocking your CSS/JS** — Google renders pages; blocking assets can hurt how
   it sees them.

## While you're at it, check your sitemap too

A broken or empty `sitemap.xml` hurts crawl efficiency the same quiet way:

```bash
curl "{LIVE_URL}/sitemap?url=https://your-site.com"
```

Both checks are free, zero-dependency (pure Python stdlib), and open source:
[{REPO_URL}]({REPO_URL}). There's also a social-preview check
(`/check?url=…`) that confirms your `og:image` actually loads.

Feedback welcome — what else silently breaks your site's visibility that a
one-request check could catch?
"""


ARTICLES = {
    "preview": {
        "article": {
            "title": "Your blog's link preview is probably broken — here's a 1-line CI check",
            "published": False,
            "tags": ["webdev", "seo", "python", "showdev"],
            "canonical_url": REPO_URL,
            "description": (
                "og:image 404s, relative URLs, moved CDNs — silent click-through killers. "
                "A free, zero-dependency validator that confirms your preview image actually loads."
            ),
            "body_markdown": BODY_MARKDOWN,
        }
    },
    "robots": {
        "article": {
            "title": "The robots.txt mistake that hides your whole site from Google",
            "published": False,
            "tags": ["seo", "webdev", "python", "beginners"],
            "canonical_url": f"{LIVE_URL}/robots-txt-checker.html",
            "description": (
                "A stray 'Disallow: /' can hide your entire site from search engines and "
                "nothing tells you. A free one-request check for robots.txt and sitemap.xml."
            ),
            "body_markdown": BODY_ROBOTS,
        }
    },
    "sitemap": {
        "article": {
            "title": "Is your sitemap.xml quietly broken? A 1-line way to check",
            "published": False,
            "tags": ["seo", "webdev", "python", "showdev"],
            "canonical_url": f"{LIVE_URL}/sitemap-validator.html",
            "description": (
                "An invalid or empty sitemap.xml hurts how search engines crawl your site — "
                "and nothing warns you. A free, one-request validator (pure stdlib, open source)."
            ),
            "body_markdown": f"""\
## The sitemap you set up once and never checked again

A `sitemap.xml` helps search engines discover and crawl your pages efficiently.
But a single stray character makes the whole file invalid XML — and crawlers just
silently skip it. Or it points at an old path after a migration. Or it's empty.
**Nothing tells you.** You just get crawled less thoroughly.

I added a free sitemap check to [OGCheck]({LIVE_URL}) (alongside its Open Graph
and robots.txt checks).

## Check it in one request

```bash
curl "{LIVE_URL}/sitemap?url=https://your-site.com"
```

It confirms your sitemap is **reachable** (not a 404/500), is **valid XML**, and
actually **lists URLs** rather than being empty — and tells you how many.

## The sitemap problems that quietly cost you crawl budget

1. **Invalid XML** — one unescaped `&` or stray tag breaks the whole file for
   crawlers.
2. **Empty sitemap** — generated once, never repopulated after a CMS change.
3. **Unreachable** — a 404 or 500 after a migration or a misconfigured route.
4. **Not referenced in robots.txt** — search engines have to guess it's there.

## While you're at it

The same free API also checks your `robots.txt` (`/robots?url=…`) and your social
preview / `og:image` (`/check?url=…`). It's zero-dependency (pure Python stdlib),
open source: [{REPO_URL}]({REPO_URL}).

What else silently breaks your site's visibility that a one-request check could
catch? Genuinely curious — feedback welcome.
""",
        }
    },
}

# Backwards-compat alias (the launch article).
ARTICLE = ARTICLES["preview"]


def _find_existing(api_key: str, title: str) -> dict | None:
    """Return the user's existing article with this title (draft or live), if any.

    dev.to rejects a second article with the same title within 5 minutes, so on a
    re-run we find the existing one and update it instead of erroring.
    """
    for state in ("unpublished", "published"):
        req = urllib.request.Request(
            f"https://dev.to/api/articles/me/{state}?per_page=30",
            headers={"api-key": api_key, "User-Agent": "ogcheck-publisher/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            for art in json.loads(response.read().decode("utf-8")):
                if art.get("title") == title:
                    return art
    return None


def publish(api_key: str, *, go_live: bool, which: str = "preview") -> dict:
    """Create the article, or update the existing one (idempotent re-runs)."""
    article = ARTICLES[which]
    article["article"]["published"] = go_live
    title = article["article"]["title"]

    existing = _find_existing(api_key, title)
    if existing is not None:
        # Update in place (e.g. flip a draft to published).
        data = json.dumps(article).encode("utf-8")
        req = urllib.request.Request(
            f"https://dev.to/api/articles/{existing['id']}",
            data=data,
            method="PUT",
            headers={
                "Content-Type": "application/json",
                "api-key": api_key,
                "User-Agent": "ogcheck-publisher/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    data = json.dumps(article).encode("utf-8")
    request = urllib.request.Request(
        "https://dev.to/api/articles",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
            "User-Agent": "ogcheck-publisher/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    key = os.environ.get("DEVTO_API_KEY")
    if not key:
        print("Set DEVTO_API_KEY (get one at https://dev.to/settings/extensions).", file=sys.stderr)
        return 1
    go_live = "--publish" in sys.argv
    which = "preview"
    if "--article" in sys.argv:
        which = sys.argv[sys.argv.index("--article") + 1]
    if which not in ARTICLES:
        print(f"unknown article '{which}'; choose from: {list(ARTICLES)}", file=sys.stderr)
        return 1
    try:
        result = publish(key, go_live=go_live, which=which)
    except urllib.error.HTTPError as exc:
        print(f"dev.to API error {exc.code}: {exc.read().decode()}", file=sys.stderr)
        return 2
    url = result.get("url", "(no url)")
    state = "PUBLISHED" if go_live else "DRAFT created"
    print(f"{state}: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
