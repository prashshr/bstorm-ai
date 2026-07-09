#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

MANIFEST_DIR="deploy/k8s"

echo "Deploying ai-ensemble to Kubernetes..."

if [ ! -f "./.env" ]; then
  echo "ERROR: .env file not found at $(pwd)/.env"
  echo "Please create .env file with your secrets."
  echo "You can use .env.example as a template:"
  echo "  cp .env.example .env"
  exit 1
fi

echo "Applying manifests in order..."

echo "1. Creating namespace..."
kubectl apply -f $MANIFEST_DIR/namespace.yaml

echo "2. Creating secrets from .env file..."
if ! bash $MANIFEST_DIR/create-secret.sh; then
  echo "ERROR: Failed to create secrets from .env file"
  exit 1
fi

echo "3. Creating config..."
kubectl apply -f $MANIFEST_DIR/configmap.yaml

echo "4. Deploying SearXNG (self-hosted search)..."
kubectl apply -f $MANIFEST_DIR/searxng-settings-configmap.yaml
kubectl apply -f $MANIFEST_DIR/searxng-deployment.yaml

echo "5. Creating GHCR pull secret..."
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace=ai-ensemble \
  --docker-server=ghcr.io \
  --docker-username="prashshr" \
  --docker-password="${GHCR_PAT:-}" \
  --dry-run=client -o yaml | kubectl apply -f - || echo "WARNING: GHCR pull secret not configured - set GHCR_PAT in environment"

echo "6. Creating api deployment..."
kubectl apply -f $MANIFEST_DIR/deployment.yaml

echo "7. Creating api service..."
kubectl apply -f $MANIFEST_DIR/service.yaml

echo "8. Creating web deployment..."
kubectl apply -f $MANIFEST_DIR/web-deployment.yaml

echo "9. Creating web service..."
kubectl apply -f $MANIFEST_DIR/web-service.yaml

echo "10. Creating certificate..."
kubectl apply -f $MANIFEST_DIR/cert.yaml || echo "WARNING: cert apply failed (cert-manager may not be installed) - continuing..."

echo "11. Creating ingress..."
kubectl apply -f $MANIFEST_DIR/ingress.yaml

echo ""
echo "Deployment complete"
echo ""
echo "Check status:"
echo "  kubectl get pods -n ai-ensemble"
echo "  kubectl get ingress -n ai-ensemble"
echo "  kubectl logs -n ai-ensemble deployment/ai-ensemble"
