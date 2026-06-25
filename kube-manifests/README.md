# Kubernetes Manifests - ai-ensemble

This directory follows the same deployment pattern as other apps in this environment (namespace, create-secret, configmap, deployment, service, cert, ingress, apply script).

## Files

- namespace.yaml
- create-secret.sh
- configmap.yaml
- deployment.yaml
- service.yaml
- web-deployment.yaml
- web-service.yaml
- cert.yaml
- ingress.yaml
- apply.sh

## Prerequisites

1. k3s cluster reachable by kubectl
2. Traefik ingress controller available
3. cert-manager with ClusterIssuer letsencrypt-prod
4. .env file in project root with:
   - JWT_SECRET
   - CREDENTIAL_ENCRYPTION_KEY

## Deploy

From project root:

```bash
bash kube-manifests/apply.sh
```

## Verify

```bash
kubectl get pods -n ai-ensemble
kubectl get ingress -n ai-ensemble
kubectl describe certificate ai-ensemble-cert -n ai-ensemble
kubectl logs -n ai-ensemble deployment/ai-ensemble
```

Expected public endpoint:

- https://ai-ensemble.samkhya.cloud
