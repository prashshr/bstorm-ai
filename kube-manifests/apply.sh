#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

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
kubectl apply -f kube-manifests/namespace.yaml

echo "2. Creating secrets from .env file..."
if ! bash kube-manifests/create-secret.sh; then
  echo "ERROR: Failed to create secrets from .env file"
  exit 1
fi

echo "3. Creating config..."
kubectl apply -f kube-manifests/configmap.yaml

echo "4. Creating api deployment..."
kubectl apply -f kube-manifests/deployment.yaml

echo "5. Creating api service..."
kubectl apply -f kube-manifests/service.yaml

echo "6. Creating web deployment..."
kubectl apply -f kube-manifests/web-deployment.yaml

echo "7. Creating web service..."
kubectl apply -f kube-manifests/web-service.yaml

echo "8. Creating certificate..."
kubectl apply -f kube-manifests/cert.yaml || echo "WARNING: cert apply failed (cert-manager may not be installed) - continuing..."

echo "9. Creating ingress..."
kubectl apply -f kube-manifests/ingress.yaml

echo ""
echo "Deployment complete"
echo ""
echo "Check status:"
echo "  kubectl get pods -n ai-ensemble"
echo "  kubectl get ingress -n ai-ensemble"
echo "  kubectl logs -n ai-ensemble deployment/ai-ensemble"
