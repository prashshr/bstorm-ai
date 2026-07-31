# Specification: Deployment

## Purpose
Specifies Docker containerization for backend (`python:3.12-slim`) and frontend (`nginx:1.27-alpine`), GHCR image registry publishing, Docker Compose, and Kubernetes (k3s) manifests under namespace `ai-ensemble`.

## Requirements

### Requirement: Non-Root Container Execution
The backend container SHALL execute as non-root user `appuser` (UID 1000) with disabled privilege escalation.

#### Scenario: Backend container launches in Kubernetes
- **GIVEN** `deployment.yaml` deployed to k3s
- **WHEN** pod creates container
- **THEN** process runs as UID 1000 without root privileges

### Requirement: Production Image Versioning
Production container images SHALL be tagged with semantic version tags (e.g. `ghcr.io/prashshr/ai-ensemble-web:v4.2.0`) and pushed to GHCR.

#### Scenario: Running deployment pipeline
- **GIVEN** a new release tag `v4.2.0`
- **WHEN** images are built and pushed
- **THEN** Kubernetes deployments reference exact version tags
