# OGCheck — ready-to-post launch copy

Everything below is written to be **posted by you** (the owner) on your own
accounts. Just copy, paste, and hit submit. Post to **one or two channels first**,
see if anyone engages, then do the rest — don't blast everywhere at once.

**Live URL:** https://ogcheck-app.azurewebsites.net
**Repo:** https://github.com/rahulatrkm/ogcheck (public) · Action: `uses: rahulatrkm/ogcheck@v1`

> Tone rules: be a maker sharing a free useful thing, not a salesperson. Answer
> every comment. Never fake engagement. If it flops, that's data — not failure.

---

## ⚡ ONE-CLICK LAUNCH — where human intervention is needed

The machine has done everything up to here (built, deployed, priced, payment
wired, SEO, copy). These are the irreducible **human steps** — each needs *your*
verified identity, which platforms and law require. The links are **pre-filled**:
you click, glance, and submit.

**Ordered by what works for a new account TODAY** (Hacker News gates Show HN
behind account karma — do it later, after warming up; see the note at the end).

> 🧑 **HUMAN NEEDED — 1. Publish the GitHub repo + Action** (best move; no gate,
> evergreen). Push this repo public, tag `v1`, and it's a usable Action:
> `uses: <you>/ogcheck@v1`. Optionally list on the GitHub Marketplace. This is
> the strongest, most durable channel for a developer tool.

> 🧑 **HUMAN NEEDED — 2. Publish a dev.to article** (no karma gate, indexes on
> Google, permanent): https://dev.to/new — paste section 3 below. Set a canonical
> URL to your repo/site and tags: `webdev, seo, python, showdev`.

> 🧑 **HUMAN NEEDED — 3. Post to Reddit r/webdev.** Pre-filled title + URL:
> https://www.reddit.com/r/webdev/submit?title=I%20built%20a%20free%20tool%20that%20fails%20your%20CI%20if%20your%20og%3Aimage%20is%20broken&url=https%3A%2F%2Fogcheck-app.azurewebsites.net
> (Very new Reddit accounts may hit a karma filter; if so, comment a bit first.)

> 🧑 **HUMAN NEEDED — 4. Indie Hackers:** https://www.indiehackers.com/new-post — paste section 4 below.

> 🧑 **HUMAN NEEDED — 5. Tweet it (X).** Pre-filled tweet:
> https://twitter.com/intent/tweet?text=Your%20link%20preview%20is%20probably%20broken%20and%20nothing%20told%20you.%20og%3Aimage%20404s%2C%20relative%20URLs%2C%20moved%20CDNs.%20OGCheck%20checks%20it%20%28and%20that%20the%20image%20actually%20loads%29%20in%20one%20request.%20Free%3A%20https%3A%2F%2Fogcheck-app.azurewebsites.net

> ⏳ **LATER — Hacker News (Show HN).** HN restricts Show HN for brand-new
> accounts (this is normal anti-spam, not a rejection). Warm up first: over 1–2
> weeks, leave a few genuine comments on threads you find interesting to build a
> little karma, then post the Show HN (pre-filled link):
> https://news.ycombinator.com/submitlink?u=https%3A%2F%2Fogcheck-app.azurewebsites.net&t=Show%20HN%3A%20OGCheck%20%E2%80%93%20validate%20your%20link%20preview%20%28and%20check%20og%3Aimage%20loads%29%20in%20CI
> Read https://news.ycombinator.com/showhn.html first. HN is a high-value
> audience worth earning — don't burn it with a premature post.

**Why these need you:** creating/using accounts on these platforms requires a
verified human identity; automated posting violates their terms and would get
the product banned. This is the honest boundary — the machine does 95%, you do
the accountable click.

---

## 1. Reddit — r/webdev

**Title:** I built a free tool that fails your CI if your `og:image` is broken

**Body:**
> Classic bug: you add an `og:image`, ship it, and months later notice a post got
> half the clicks — because the image 404s and nothing ever told you.
>
> So I made **OGCheck**: it parses your Open Graph / Twitter tags and — the part
> most validators skip — actually **HEAD/GET-checks that your `og:image` returns
> 200**. It's a JSON API, a one-line CLI, and a GitHub Action you can drop in CI
> so a broken preview fails the build.
>
> Live (free, no signup): https://ogcheck-app.azurewebsites.net
> CLI: `python -m ogcheck https://your-site.com`
>
> It's pure Python stdlib, zero dependencies. Would love feedback — especially
> what you'd want it to catch that it doesn't yet.

*(r/webdev requires genuine engagement — reply to every comment, don't just drop and leave.)*

---

## 2. Hacker News — Show HN

**Title:** Show HN: OGCheck – validate your link preview (and check og:image loads) in CI

**URL field:** https://ogcheck-app.azurewebsites.net

**First comment (post immediately after submitting):**
> Author here. Every social-preview *generator* exists, but I kept getting bitten
> by the opposite problem: a preview that's silently broken because the `og:image`
> URL 404s, is relative, or got moved by a CDN — and nothing tells you until
> traffic drops.
>
> OGCheck is the boring validator: fetch the page, parse OG/Twitter tags, and
> confirm the image actually returns 200. It's a stdlib-only Python service (no
> deps), also a CLI that exits non-zero on failure, so you can wire it into CI.
>
> It's free and I'm not sure there's a business here — the honest goal is to find
> out if the "monitor my previews" pain is worth paying for. Feedback welcome,
> especially on false positives.

---

## 3. dev.to (article)

**Title:** Your blog's link preview is probably broken — here's a 1-line CI check

**Tags:** webdev, seo, python, showdev

**Body:**
> ## The silent bug
> You add `<meta property="og:image" content="...">`, the preview looks fine when
> you test it, you ship. Weeks later the image gets moved, the CDN path changes,
> or it was a relative URL all along — and now every share is a blank card. Your
> click-through quietly drops and **nothing alerts you.**
>
> ## Catch it in CI
> I built [OGCheck](https://ogcheck-app.azurewebsites.net) to fail the build when
> that happens:
>
> ```bash
> python -m ogcheck https://your-site.com/blog/post
> # exits non-zero if og:image 404s or required tags are missing
> ```
>
> It parses your Open Graph + Twitter Card tags, scores them, and — the key part —
> **actually requests the `og:image` to confirm it returns 200.** There's a JSON
> API and a GitHub Action too.
>
> ## The 5 things that break previews
> 1. The image URL 404s (most common)
> 2. A relative URL instead of absolute
> 3. A cached old preview on the platform
> 4. Wrong dimensions / file type
> 5. Crawlers blocked by robots.txt or auth
>
> It's free, zero-dependency, open source. If you monitor a lot of pages I'm
> thinking about a paid "watch these URLs and alert me" tier — would that be
> useful? Honest feedback appreciated.

---

## 4. Indie Hackers

**Title:** Show IH: OGCheck — a free validator that checks your og:image actually loads

**Body:**
> Shipped a small thing to scratch my own itch: a validator that confirms your
> social-preview `og:image` actually returns 200 (not just that the tag exists).
> API + CLI + GitHub Action, free, no signup: https://ogcheck-app.azurewebsites.net
>
> The bet: *generating* OG images is crowded, but *monitoring* them for silent
> breakage isn't. Not sure there's revenue in it yet — testing whether the pain is
> real. Would love to hear if you've been bitten by a broken preview.

---

## 5. X / LinkedIn (short)

> Your link preview is probably broken and nothing told you.
>
> og:image 404s, relative URLs, moved CDNs — silent click-through killers.
>
> OGCheck checks your preview (and that the image actually loads) in one request.
> Free, no signup: https://ogcheck-app.azurewebsites.net

---

## 6. GitHub — publish the Action (evergreen, free reach)

1. Push this repo public.
2. On GitHub → the repo → **Releases** → tag `v1` → the `action.yml` makes it a
   usable Action: `uses: <you>/ogcheck@v1`.
3. Optionally list it on the **GitHub Marketplace** ("Actions" category) — free,
   permanent discovery by exactly the CI-minded audience.

---

## After posting — measure honestly (see [LAUNCH.md](LAUNCH.md))

- App Service logs show request volume: `az webapp log tail -n ogcheck-app -g ogcheck-rg`.
- Track: unique `/check` calls, GitHub stars/Action installs, any payment to the wallet.
- **Kill criteria:** < 50 real users / 0 paid after ~6–8 weeks → pivot or retire.
  That's normal for a first product, not failure.
