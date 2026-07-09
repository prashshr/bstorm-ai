# Kubernetes Manifests — ai-ensemble

Deployment manifests for running AI Ensemble on K3s with Traefik ingress, Let's Encrypt TLS, and self-hosted SearXNG.

## Prerequisites

1. K3s cluster reachable by `kubectl`
2. Traefik ingress controller available
3. cert-manager with `ClusterIssuer letsencrypt-prod`
4. `.env` file in project root with:
   - `JWT_SECRET`
   - `CREDENTIAL_ENCRYPTION_KEY`
   - `TAVILY_API_KEY` (optional, for RAG)
5. GHCR pull secret: `kubectl create secret docker-registry ghcr-pull-secret ...` (or let `apply.sh` create it)

## Deploy

From project root:

```bash
bash deploy/k8s/apply.sh
```

## Verify

```bash
kubectl get pods -n ai-ensemble
kubectl get ingress -n ai-ensemble
kubectl describe certificate ai-ensemble-cert -n ai-ensemble
kubectl logs -n ai-ensemble deployment/ai-ensemble
```

Expected public endpoint: `https://ai-ensemble.samkhya.cloud`
