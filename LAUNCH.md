# Launching OGCheck — the honest checklist

The code is the easy 20%. This is the 80% that decides whether it earns anything.
It is written to be executed by **you** (the owner), because it touches your
accounts and reputation — the one thing that can't be automated.

## Reality check first

- Most tools like this get **zero paying users.** That is the base rate, not a
  failure. The plan is to try cheaply and cut fast.
- We win only if we're the **simplest, fastest** option for one specific pain and
  we show up **where the audience already is.** Not "a validator for everyone."

## Step 1 — Deploy free (30 min)

- [ ] Push this repo to GitHub (public — the Action + open source is the reach).
- [ ] Render → New → Blueprint → point at `businesses/ogcheck/render.yaml`
      (free tier). Or `docker build` and run on any free container host.
- [ ] Confirm `https://<your-app>/healthz` returns `{"status":"ok"}`.
- [ ] (Optional) buy a cheap domain later; a `*.onrender.com` URL is fine to start.

## Step 2 — Make it findable (the real work)

- [ ] **GitHub:** publish the `action.yml` as a Marketplace Action
      ("OGCheck — fail CI on a broken social preview"). Free, evergreen reach.
- [ ] **SEO landing pages** (one each): "check open graph tags", "og:image not
      showing on facebook/twitter/linkedin", "social preview validator". These
      are the terms people search *when their preview is already broken.*
- [ ] **dev.to post:** "Your blog's link preview is probably broken — here's a
      1-line CI check." Link the tool.

## Step 3 — Post where the buyers are (your hands, 1 hr)

Post honestly, as a maker sharing a free tool — not spam:

- [ ] r/webdev — "I built a free CLI/Action that fails your build if your
      og:image 404s"
- [ ] r/juniordev, r/SEO, r/nextjs (framework-specific angle)
- [ ] Indie Hackers — "Show IH"
- [ ] Hacker News — "Show HN: OGCheck — validate your link preview in CI"
- [ ] Your own X/LinkedIn.

## Step 4 — Measure honestly (2 weeks)

Track: unique `/check` calls, GitHub Action installs, free signups, paid.

## Step 5 — Decide (the kill criteria)

- [ ] **< 50 free users / 0 paid after ~6–8 weeks → the demand isn't converting.**
      Do not keep polishing it. Either pivot the angle (monitoring-only, a
      specific framework) or retire it and try the next idea. This is exactly
      what the enterprise's survival + retirement logic is for.

## Payment

- Crypto (USDC on Base) is wired to the treasury wallet
  `0xC1B0137Fa043AdE3AB2c1f85EF4aE6687053D7E0`; arrivals are recognized
  on-chain automatically.
- Add Razorpay/Stripe **only once** there's real demand (don't build billing for
  users you don't have yet).
