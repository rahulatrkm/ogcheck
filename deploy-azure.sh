#!/usr/bin/env bash
# Deploy OGCheck to Azure Container Apps (scale-to-zero, lowest cost).
#
# Owner-run: uses your authenticated `az` session. Creates a small, cheap
# Container App that serves the OGCheck API + landing pages publicly.
#
# Usage: ./deploy-azure.sh [resource-group] [location]

set -euo pipefail

RG="${1:-ogcheck-rg}"
LOCATION="${2:-centralindia}"
NAME="ogcheck"
ENV_NAME="ogcheck-env"

# Resolve az (PATH, AZ override, or the isolated venv this repo's setup created).
if [[ -n "${AZ:-}" ]]; then :; elif command -v az >/dev/null 2>&1; then AZ="az";
elif [[ -x "${HOME}/az-cli-venv/bin/az" ]]; then AZ="${HOME}/az-cli-venv/bin/az";
else echo "az not found" >&2; exit 1; fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Preflight"
"$AZ" account show >/dev/null || { echo "run: $AZ login" >&2; exit 1; }
SUB="$("$AZ" account show --query name -o tsv)"
echo "  subscription: ${SUB}"
"$AZ" extension add --name containerapp --upgrade --only-show-errors >/dev/null 2>&1 || true
"$AZ" provider register --namespace Microsoft.App --wait >/dev/null 2>&1 || true
"$AZ" provider register --namespace Microsoft.OperationalInsights --wait >/dev/null 2>&1 || true
"$AZ" provider register --namespace Microsoft.ContainerRegistry --wait >/dev/null 2>&1 || true

echo "==> Resource group ${RG} (${LOCATION})"
"$AZ" group create --name "${RG}" --location "${LOCATION}" --output none

echo "==> Container Apps environment"
"$AZ" containerapp env create --name "${ENV_NAME}" --resource-group "${RG}" \
  --location "${LOCATION}" --output none 2>/dev/null || true

echo "==> Deploying OGCheck (builds the image from source, scale-to-zero)"
# `containerapp up` builds from the local Dockerfile and deploys in one step.
"$AZ" containerapp up \
  --name "${NAME}" \
  --resource-group "${RG}" \
  --environment "${ENV_NAME}" \
  --location "${LOCATION}" \
  --source "${here}" \
  --ingress external \
  --target-port 8000

# Ensure scale-to-zero (min 0) so it costs ~nothing when idle.
"$AZ" containerapp update --name "${NAME}" --resource-group "${RG}" \
  --min-replicas 0 --max-replicas 2 --output none 2>/dev/null || true

FQDN="$("$AZ" containerapp show --name "${NAME}" --resource-group "${RG}" \
  --query properties.configuration.ingress.fqdn -o tsv)"

cat <<EOF

==> OGCheck is live:

  https://${FQDN}/            landing page
  https://${FQDN}/healthz     health
  https://${FQDN}/check?url=https://example.com

SEO pages:
  https://${FQDN}/og-image-not-showing.html
  https://${FQDN}/check-open-graph-tags.html
  https://${FQDN}/social-preview-validator.html

Scale-to-zero is on: it costs ~nothing when idle, wakes on the first request.
EOF
