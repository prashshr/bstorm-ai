#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="ai-ensemble"
SECRET_NAME="ai-ensemble-secrets"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found in $(pwd)"
  echo "Create it from .env.example first: cp .env.example .env"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [ -z "${JWT_SECRET:-}" ]; then
  echo "ERROR: JWT_SECRET is required in .env"
  exit 1
fi

if [ -z "${CREDENTIAL_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: CREDENTIAL_ENCRYPTION_KEY is required in .env"
  exit 1
fi

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NAMESPACE" delete secret "$SECRET_NAME" --ignore-not-found
kubectl -n "$NAMESPACE" create secret generic "$SECRET_NAME" \
  --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=CREDENTIAL_ENCRYPTION_KEY="$CREDENTIAL_ENCRYPTION_KEY"

echo "Secret $SECRET_NAME updated in namespace $NAMESPACE"
