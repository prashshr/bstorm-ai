# AI Ensemble — Production Plan

## Overview

This document covers the production readiness, deployment, and operations of the AI Ensemble system running on **K3s Kubernetes** at `https://ai-ensemble.samkhya.cloud`.

### Current Deployment Architecture

```
Internet → Traefik Ingress (TLS) → Services → Pods
                                        │
                                   ┌─────┴─────┐
                                   │ Backend    │ ← → SQLite (hostPath)
                                   │ (FastAPI)  │ ← → Provider APIs
                                   └─────┬─────┘
                                         │
                                   ┌─────┴─────┐
                                   │ SearXNG    │ (self-hosted search engine)
                                   └───────────┘
```

### Key Stack

| Layer | Technology |
|-------|-----------|
| **Container Runtime** | K3s (lightweight Kubernetes) |
| **Ingress** | Traefik with cert-manager (Let's Encrypt) |
| **Backend** | FastAPI (Python 3.12), SQLite |
| **Frontend** | Nginx serving static `frontend/index.html` |
| **Search (RAG)** | Tavily API → Self-hosted SearXNG → DuckDuckGo |
| **Registry** | GHCR (`ghcr.io/prashshr/ai-ensemble`) |
| **Auth** | JWT bearer tokens, bcrypt password hashing |
| **Encryption** | Fernet (per-user UEK for provider keys + RAG context) |

---

## 1. Deployment

### 1.1 Kubernetes Manifests

All manifests live in `deploy/k8s/`:

| Manifest | Purpose |
|----------|---------|
| `namespace.yaml` | `ai-ensemble` namespace |
| `deployment.yaml` | Backend API (1 replica, port 8080) |
| `service.yaml` | Backend ClusterIP service |
| `web-deployment.yaml` | Nginx serving frontend from `frontend/` |
| `web-service.yaml` | Frontend ClusterIP service |
| `searxng-deployment.yaml` | Self-hosted SearXNG (1 replica, port 8080) |
| `configmap.yaml` | Non-sensitive env vars (DB URL, CORS, SearXNG URL) |
| `cert.yaml` | Let's Encrypt TLS certificate |
| `ingress.yaml` | Traefik ingress: routes `/api`, `/health`, `/` |
| `apply.sh` | Orchestrated deployment script |
| `create-secret.sh` | Creates K8s Secret from `.env` |

### 1.2 Deploy

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env with strong secrets and TAVILY_API_KEY

# 2. Push latest image to GHCR
cd backend && docker build -t ghcr.io/prashshr/ai-ensemble:latest .
docker push ghcr.io/prashshr/ai-ensemble:latest

# 3. Deploy to K3s
cd deploy/k8s && bash apply.sh

# 4. Verify
kubectl get pods -n ai-ensemble
kubectl get ingress -n ai-ensemble
kubectl logs -n ai-ensemble deployment/ai-ensemble
```

### 1.3 Image Management

- **Repository:** `ghcr.io/prashshr/ai-ensemble`
- **Tags:** `latest` (always the current stable), `YYYYMMDD-HHMM` (dated builds)
- **Pull policy:** `Always` — ensures fresh images on each pod restart
- **Pull secret:** `ghcr-pull-secret` (docker-registry type) for GHCR authentication

### 1.4 Docker Compose (Alternative for dev/staging)

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

Access: `http://localhost:8088` (Caddy on port 8088 proxies to backend + serves frontend).

---

## 2. Security

### 2.1 Network Exposure

| Port | Protocol | Purpose | Restrict to |
|------|----------|---------|-------------|
| 443 | HTTPS | Application + API | Public (Traefik ingress) |
| 80 | HTTP | Let's Encrypt ACME challenge | Public (redirects to 443) |
| 22 | SSH | Admin access | Admin IPs only |
| All others | — | Blocked by firewall | Deny |

**K3s API (6443):** Bind to private network only, restrict with firewall.

### 2.2 Authentication

- **JWT bearer tokens** issued on login, expire after 24 hours
- **Passwords** hashed with bcrypt (passlib)
- **Rate limiting:** 10 registrations/minute per IP, 60 requests/minute for chat
- **Data isolation:** All queries filtered by `user_id` — cross-user access returns 404

### 2.3 Encryption

| What | How | Key |
|------|-----|-----|
| Provider API keys | Fernet symmetric encryption | UEK (User Encryption Key, per-user) or server master key |
| RAG context | Fernet symmetric encryption | UEK (per-user) |
| JWT tokens | HS256 signing | Server `JWT_SECRET` |
| TLS | Let's Encrypt (cert-manager) | Auto-renewed, 90-day validity |

### 2.4 Headers (set by Traefik ingress)

```yaml
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## 3. RAG Pipeline

The 3-tier search engine runs inside the cluster:

```
User Question
    │
    ├─ Tier 1: Tavily API ──── Requires TAVILY_API_KEY
    ├─ Tier 2: Self-hosted SearXNG ──── Pod: searxng-svc:8080
    └─ Tier 3: DuckDuckGo (HTML scrape) ──── Public fallback
```

All 3 run in parallel. Results are deduplicated and fed to `trafilatura` for content extraction. The extracted content is encrypted and stored in the discussion's `retrieved_context_encrypted` field.

**Domain-aware enrichment:** Queries are classified into 17 topics (shopping, finance, tech, etc.) and `site:` filters are appended to improve result quality.

---

## 4. Testing & Quality

### 4.1 Test Suite

```bash
python testing/scripts/run-tests.py
```

| Layer | Tests | Framework |
|-------|-------|-----------|
| **Unit** | 4 modules (43 tests) | pytest |
| **Integration** | 3 modules (27 tests) | pytest + TestClient |
| **E2E** | 19 tests | Playwright (Chromium) |
| **Total** | **89 tests** | — |

### 4.2 Reports

Each test run generates a version-tracked report at `testing/reports/test-report_{VERSION}_{YYYYMMDD}_{HHMM}.md` with:
- Executive summary (pass rate, duration)
- Functional area coverage table
- Per-module detailed results
- Failed test root-cause analysis
- Raw pytest output

### 4.3 Release Verification

Before tagging a release:
1. Run `python testing/scripts/run-tests.py --coverage`
2. Verify 100% pass rate (0 failures, 0 errors)
3. Run `python testing/scripts/run-tests.py --infra` to verify K3s pods are healthy
4. Tag with semver: `git tag -a vX.Y.Z -m "message"`

---

## 5. Monitoring & Operations

### 5.1 Health Checks

| Endpoint | What it verifies |
|----------|-----------------|
| `GET /health` | Backend app is running (returns `{"status": "ok"}`) |
| K3s liveness probe | HTTP GET `/health`, initial delay 20s |
| K3s readiness probe | HTTP GET `/health`, initial delay 10s |

### 5.2 Logs

```bash
# Backend logs (includes RAG pipeline debug output)
kubectl logs -n ai-ensemble deployment/ai-ensemble | grep "\[RAG\]"

# All backend logs
kubectl logs -n ai-ensemble deployment/ai-ensemble -f

# SearXNG logs
kubectl logs -n ai-ensemble deployment/searxng -f

# Web/nginx logs
kubectl logs -n ai-ensemble deployment/ai-ensemble-web -f
```

### 5.3 Disk Management

The SQLite database is stored on a `hostPath` volume at `/arbeit/ai-welt/projects/ai-ensemble/data/`. Monitor disk usage:

```bash
df -h /
du -sh /arbeit/ai-welt/projects/ai-ensemble/data/
```

K3s evicts pods when disk usage exceeds thresholds — keep at least 15% free.

### 5.4 Backup

```bash
# Database
cp /arbeit/ai-welt/projects/ai-ensemble/data/ai_ensemble.db /backup/ai_ensemble-$(date +%Y%m%d).db

# K3s manifests (drift recovery)
kubectl get all -n ai-ensemble -o yaml > /backup/ai-ensemble-manifests-$(date +%Y%m%d).yaml
```

---

## 6. Scaling

### 6.1 Current Limits

| Resource | Current | Bottleneck |
|----------|---------|------------|
| Backend replicas | 1 | SQLite (single-writer) |
| SearXNG replicas | 1 | Sufficient for local search |
| RAM per pod | 512Mi-1Gi | Under 50% utilization |
| CPU per pod | 500m-1000m | Under 30% utilization |

### 6.2 Future Scaling

- **PostgreSQL migration:** Replace SQLite for concurrent reader support
- **Horizontal scaling:** Add backend replicas with shared PostgreSQL
- **Separate RAG workers:** Move content extraction to background workers for faster discussion creation
- **Redis caching:** Cache frequent search queries to reduce API costs
- **CDN:** Serve frontend assets via CDN for global users

---

## 7. Release Process

### 7.1 Semantic Versioning

```
vMAJOR.MINOR.PATCH

MAJOR = Breaking changes (API contract, DB schema, auth)
MINOR = New features (backward compatible)
PATCH = Bug fixes, security, docs
```

Current: `v1.0.0` — Stable, tested, production-ready.

### 7.2 Branch Strategy

| Branch | From | Merges to | Purpose |
|--------|------|-----------|---------|
| `main` | — | — | Production releases. Must pass all tests. |
| `develop` | `main` | `main` | Feature integration. Feature branches merge here first. |
| `feature/*` | `develop` | `develop` | Individual features. Naming: `feature/rag-improvements` |

### 7.3 Release Checklist

- [ ] All 89 tests pass (0 failures)
- [ ] No known security vulnerabilities
- [ ] GHCR image pushed with `latest` + dated tag
- [ ] K3s pods healthy: `Running` with `1/1` ready
- [ ] Ingress returns 200 for `/health` and `/`
- [ ] Tagged with semver: `git tag -a vX.Y.Z`
- [ ] GitHub Release created with changelog
- [ ] Test report generated and saved

---

## 8. Incident Response

| Symptom | Likely Cause | Action |
|---------|-------------|--------|
| `no available server` | Backend pod crash | Check `kubectl logs`, restart deployment |
| `ImagePullBackOff` | GHCR auth failure / bad image | Check `ghcr-pull-secret`, verify image exists |
| `DiskPressure` on node | /dev/sda1 > 85% | Clean up Docker cache, old images, temp files |
| RAG returns null | All 3 search engines failed | Check `kubectl logs | grep [RAG]`, verify Tavily key |
| 401 on proxy chat | Expired JWT token | Re-login from frontend |
| Rate limit errors | Too many requests | Wait 1 minute, check `limiter.enabled` |