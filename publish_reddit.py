"""Publish the OGCheck launch post to Reddit via the official OAuth API.

Same legitimate pattern as the dev.to publisher and the `gh` CLI: the OWNER
creates a Reddit "script" app on their own account and supplies its credentials;
this script does the mechanical submit through Reddit's sanctioned API. It is not
scraping, and it is not automated account creation.

Owner one-time setup (2 min):
  1. Log in to Reddit, go to https://www.reddit.com/prefs/apps
  2. "create another app..." -> type: **script** -> name: ogcheck ->
     redirect uri: http://localhost:8080 -> create.
  3. Note the client id (under the app name) and the secret.

Then run (all four env vars are yours):
  REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... \
  REDDIT_USERNAME=... REDDIT_PASSWORD=... \
  python publish_reddit.py [--subreddit test] [--submit]

Defaults to r/test (a sandbox) so you can verify before hitting r/webdev, and to
a dry run unless --submit is passed. Pure standard library.

Etiquette note baked in: subreddits like r/webdev have self-promotion rules and
new-account/karma filters. Prefer a genuine text post over a bare link, engage in
the comments, and don't spam. This posts ONE honest post.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

LIVE_URL = "https://ogcheck.onrender.com"
REPO_URL = "https://github.com/rahulatrkm/ogcheck"
USER_AGENT = "python:ogcheck-publisher:1.0 (by /u/{username})"

TITLE = "I built a free tool that fails your CI if your og:image is broken"

# A genuine text (self) post reads better and survives subreddit rules better
# than a bare link. The URL is in the body.
BODY = f"""\
Classic bug: you add an `og:image`, ship it, and months later notice a post got
half the clicks — because the image 404s and nothing ever told you.

So I made **OGCheck**: it parses your Open Graph / Twitter tags and — the part
most validators skip — actually checks that your `og:image` returns HTTP 200.
It's a JSON API, a one-line CLI, and a GitHub Action you can drop in CI so a
broken preview fails the build.

- Live (free, no signup): {LIVE_URL}
- CLI: `python -m ogcheck https://your-site.com`
- Open source (MIT): {REPO_URL}

It's pure Python stdlib, zero dependencies. It also checks robots.txt and
sitemap.xml now (`/robots?url=`, `/sitemap?url=`).

Would love feedback — especially what you'd want it to catch that it doesn't yet.
"""


def _token(cid: str, secret: str, user: str, pw: str) -> str:
    auth = urllib.parse.urlencode(
        {"grant_type": "password", "username": user, "password": pw}
    ).encode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=auth,
        method="POST",
        headers={"User-Agent": USER_AGENT.format(username=user)},
    )
    # HTTP Basic auth with the app's client id + secret.
    import base64

    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req.add_header("Authorization", f"Basic {basic}")
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode())
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"no access token: {payload}")
    return token


def submit(token: str, user: str, subreddit: str) -> dict:
    data = urllib.parse.urlencode(
        {
            "sr": subreddit,
            "kind": "self",  # a text post
            "title": TITLE,
            "text": BODY,
            "api_type": "json",
            "resubmit": "true",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth.reddit.com/api/submit",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT.format(username=user),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def main() -> int:
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user = os.environ.get("REDDIT_USERNAME")
    pw = os.environ.get("REDDIT_PASSWORD")
    if not all([cid, secret, user, pw]):
        print(
            "Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, "
            "REDDIT_PASSWORD (create a 'script' app at "
            "https://www.reddit.com/prefs/apps).",
            file=sys.stderr,
        )
        return 1

    # Parse args: --subreddit <name> (default: test), --submit to go live.
    subreddit = "test"
    if "--subreddit" in sys.argv:
        subreddit = sys.argv[sys.argv.index("--subreddit") + 1]
    go_live = "--submit" in sys.argv

    if not go_live:
        print(f"DRY RUN — would post to r/{subreddit}:\n\n# {TITLE}\n\n{BODY}")
        print("Re-run with --submit to actually post.")
        return 0

    try:
        token = _token(cid, secret, user, pw)  # type: ignore[arg-type]
        result = submit(token, user, subreddit)  # type: ignore[arg-type]
    except urllib.error.HTTPError as exc:
        print(f"Reddit API error {exc.code}: {exc.read().decode()}", file=sys.stderr)
        return 2

    errors = result.get("json", {}).get("errors") or []
    if errors:
        print(f"Reddit rejected the post: {errors}", file=sys.stderr)
        return 3
    url = result.get("json", {}).get("data", {}).get("url", "(submitted)")
    print(f"POSTED to r/{subreddit}: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
