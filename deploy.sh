#!/usr/bin/env bash
# Redeploy Pathology DES Simulation Lab to Cloud Run.
# Usage (from repo root):
#   ./deploy.sh
# Optional overrides:
#   PROJECT_ID=... REGION=... SERVICE=... IMAGE=... ./deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PROJECT_ID="${PROJECT_ID:-marine-shell-490317-u9}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-pathology-simulation}"
AR_REPO="${AR_REPO:-pathology-simulation}"
IMAGE_NAME="${IMAGE_NAME:-sim-lab}"
TAG="${TAG:-latest}"
GCS_BUCKET="${GCS_BUCKET:-pathology-simulation}"
GCS_PROJECT="${GCS_PROJECT:-$PROJECT_ID}"
MEMORY="${MEMORY:-2Gi}"
CPU="${CPU:-2}"
TIMEOUT="${TIMEOUT:-3600}"
MAX_INSTANCES="${MAX_INSTANCES:-3}"
BUILD_TIMEOUT="${BUILD_TIMEOUT:-20m}"

IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}:${TAG}}"

echo "==> Project:  $PROJECT_ID"
echo "==> Region:   $REGION"
echo "==> Service:  $SERVICE"
echo "==> Image:    $IMAGE"
echo "==> Bucket:   $GCS_BUCKET"
echo

if ! command -v gcloud >/dev/null 2>&1; then
  echo "error: gcloud CLI not found" >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n1 || true)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "error: no active gcloud account — run: gcloud auth login" >&2
  exit 1
fi
echo "==> Authenticated as $ACTIVE_ACCOUNT"
echo

echo "==> Building and pushing image (Cloud Build)…"
gcloud builds submit \
  --tag "$IMAGE" \
  --project="$PROJECT_ID" \
  --timeout="$BUILD_TIMEOUT" \
  "$ROOT"

echo
echo "==> Deploying to Cloud Run…"
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --project="$PROJECT_ID" \
  --allow-unauthenticated \
  --set-env-vars="GCS_BUCKET=${GCS_BUCKET},GCS_PROJECT=${GCS_PROJECT}" \
  --memory="$MEMORY" \
  --cpu="$CPU" \
  --timeout="$TIMEOUT" \
  --max-instances="$MAX_INSTANCES" \
  --quiet

URL="$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format='value(status.url)')"

echo
echo "==> Deployed"
echo "    URL: $URL"
echo "    Health: ${URL}/api/health"
