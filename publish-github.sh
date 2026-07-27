#!/usr/bin/env bash
# Publish OGCheck as a standalone public GitHub repo (the strongest, no-gate
# distribution channel for a developer tool).
#
# HUMAN NEEDED: this uses the GitHub CLI (`gh`) authenticated as YOU. Creating
# the repo requires your identity — a machine can't do it legitimately.
#
# Prereqs:
#   1. Install GitHub CLI:  brew install gh   (or: https://cli.github.com)
#   2. Log in once:         gh auth login
#
# Usage: ./publish-github.sh [repo-name]

set -euo pipefail

REPO="${1:-ogcheck}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI ('gh') not found. Install it: https://cli.github.com" >&2
  echo "Then run: gh auth login" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged in to GitHub. Run: gh auth login" >&2
  exit 1
fi

# Stage this product as its own git repo in a temp export (keeps it separate
# from the parent monorepo history).
tmp="$(mktemp -d)"
cp -R "${here}/." "${tmp}/"
cd "${tmp}"
rm -rf .git __pycache__ **/__pycache__ .pytest_cache .ruff_cache
git init -q && git add -A
git -c user.name="${GIT_AUTHOR_NAME:-owner}" -c user.email="${GIT_AUTHOR_EMAIL:-owner@localhost}" \
  commit -q -m "OGCheck — validate your Open Graph / social preview (and that og:image loads)"

echo "==> Creating public repo '${REPO}' and pushing…"
gh repo create "${REPO}" --public --source=. --push \
  --description "Validate your Open Graph / social-preview tags and confirm og:image actually loads. API + CLI + GitHub Action."

URL="$(gh repo view "${REPO}" --json url -q .url)"
echo
echo "==> Published: ${URL}"
echo "Next (optional): tag a release so the Action is usable —"
echo "  gh release create v1 --title v1 --notes 'First release'"
echo "Then it can be used anywhere as: uses: <you>/${REPO}@v1"
