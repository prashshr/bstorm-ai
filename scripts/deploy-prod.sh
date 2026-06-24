#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/.env.example" "$ENV_FILE"
  echo "Created .env from .env.example"
fi

source "$ENV_FILE"

if [[ -z "${JWT_SECRET:-}" || "$JWT_SECRET" == "replace-with-long-random-secret" ]]; then
  echo "JWT_SECRET is not set. Update .env before deploying."
  exit 1
fi

if [[ -z "${CREDENTIAL_ENCRYPTION_KEY:-}" || "$CREDENTIAL_ENCRYPTION_KEY" == "replace-with-32-byte-minimum-key" ]]; then
  echo "CREDENTIAL_ENCRYPTION_KEY is not set. Update .env before deploying."
  exit 1
fi

cd "$ROOT_DIR"
docker compose pull web || true
docker compose build api
docker compose up -d

echo "Deployment started."
echo "Check status: docker compose ps"
echo "Check logs:   docker compose logs -f web api"

echo "IMPORTANT DNS/FIREWALL CHECKS"
echo "1) A/AAAA record for ai-ensemble.samkhya.cloud points to this server"
echo "2) Ports 80 and 443 are open publicly"
echo "3) No other service is occupying ports 80/443"

echo "API health URL (after DNS propagates): https://ai-ensemble.samkhya.cloud/health"
echo "App URL: https://ai-ensemble.samkhya.cloud"
