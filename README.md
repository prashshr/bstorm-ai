# AI Ensemble

Multi-model discussion and consensus system. Compare and synthesize answers from multiple AI providers in structured rounds with automated web research (RAG).

Also available as a **self-contained Android APK** — see [Android Build](docs/android-build.md).

## Quick Start

```bash
# Prerequisites: Python 3.12, API keys from providers
cp .env.example .env          # Configure your secrets
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080  # Start API
```

## Documentation

| Document | For | What it covers |
|----------|-----|---------------|
| [User Guide](docs/user-guide.md) | Everyone | How Ensemble works with diagrams, step-by-step walkthrough |
| [Architecture](docs/architecture.md) | Developers | Full technical reference: code, data flow, security, deployment |
| [Production Plan](docs/production-plan.md) | Ops/DevOps | Production readiness, scaling, deployment checklist |
| [Android Build](docs/android-build.md) | Mobile users | Build, install, and debug the Capacitor Android APK |
| [Release Notes](docs/release-notes.md) | Everyone | Version history: features, fixes, known limitations |

## Directory Structure

```
ai-ensemble/
├── backend/                  # FastAPI backend (Python 3.12)
│   ├── app/                  # Application code
│   │   ├── api/              # API routes (auth, providers, discussions, proxy)
│   │   ├── core/             # Config, crypto, security, rate limiting
│   │   ├── db/               # Database session
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic (providers, RAG, domain knowledge)
│   ├── migrations/           # Alembic database migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/                 # Svelte SPA + Capacitor Android app
│   ├── src/                  # Svelte components and stores
│   ├── android/              # Native Android project (Capacitor)
│   ├── capacitor.config.ts   # Capacitor configuration
│   └── package.json
├── deploy/
│   ├── compose/
│   │   └── docker-compose.yml     # Docker Compose (dev/staging)
│   └── k8s/                       # Kubernetes manifests (prod)
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── ingress.yaml
│       ├── web-deployment.yaml
│       ├── web-service.yaml
│       ├── searxng-deployment.yaml
│       ├── configmap.yaml
│       ├── cert.yaml
│       └── apply.sh
├── docs/
│   ├── architecture.md            # Full architecture documentation
│   ├── production-plan.md         # Production readiness plan
│   └── android-build.md           # Android APK build instructions
├── testing/
│   ├── backend/
│   │   ├── unit/                  # Unit tests
│   │   ├── integration/           # Integration tests
│   │   ├── e2e/                   # Playwright browser tests
│   │   ├── conftest.py            # Shared fixtures
│   │   └── pyproject.toml         # Pytest configuration
│   ├── scripts/
│   │   └── run-tests.py           # Test runner & report generator
│   └── README.md                  # Testing guide
├── scripts/
│   ├── deploy-prod.sh             # Production deployment
│   └── run-dev.sh                 # Local development
├── .github/
│   ├── agents/                    # AI agent configurations
│   └── workflows/                 # GitHub Actions
├── .env.example                   # Environment variable template
├── .gitignore
├── AGENTS.md                      # AI coding agent instructions
├── GIT_GUIDELINES.md              # Git conventions
└── README.md
```

## Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Contribution and Release Workflow

This repository follows a consistent semver and GitHub label workflow:

- Release tags use annotated semver tags: `vMAJOR.MINOR.PATCH`
- GitHub issues and PRs should use the standard label groups below:
  - `type:*` (`bug`, `feature`, `docs`, `refactor`, `chore`)
  - `area:*` (`backend`, `frontend`, `infra`, `docs`, `security`)
  - `priority:*` (`P0`–`P3`)
  - `status:*` (`blocked`, `needs-info`, `ready`)
  - `release:*` (`major`, `minor`, `patch`)
- Tagging and release notes must match the same version semantics used in `GIT_GUIDELINES.md`.

The issue and PR templates under `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE/` enforce that convention for collaborative work.

## Docker Compose

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

## Kubernetes (Production)

```bash
# Build and push both images first — apply.sh does NOT build them, it pulls
# from GHCR. The backend image builds from ./backend; the web image must be
# built from the repo root because its Dockerfile references frontend/ and deploy/.
docker build -t ghcr.io/prashshr/ai-ensemble:v5.7.2 ./backend
docker build -f frontend/Dockerfile -t ghcr.io/prashshr/ai-ensemble-web:v5.7.2 .
docker push ghcr.io/prashshr/ai-ensemble:v5.7.2
docker push ghcr.io/prashshr/ai-ensemble-web:v5.7.2

# Then apply. On a single-node k3s cluster the images can be imported locally
# instead of pushed: docker save <img> | k3s ctr images import -
./deploy/k8s/apply.sh
```

`deploy/k8s/deployment.yaml` and `web-deployment.yaml` carry the image tags;
keep the API and web tags in step.

## Testing

```bash
# Run all backend tests
python testing/scripts/run-tests.py

# With coverage
python testing/scripts/run-tests.py --coverage

# View latest test report
python testing/scripts/run-tests.py --view
```

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Register new user |
| `/api/auth/login` | POST | No | Login, get bearer token |
| `/api/providers` | GET/POST | Bearer | List/save provider credentials |
| `/api/providers/{provider}/models` | GET | Bearer | Discover models |
| `/api/discussions` | GET/POST | Bearer | List/create discussions |
| `/api/discussions/{id}/messages` | GET | Bearer | List messages in discussion |
| `/api/discussions/messages` | POST | Bearer | Add message to discussion |
| `/api/proxy/chat` | POST | Bearer | Proxy chat to provider |
| `/health` | GET | No | Health check |

## Key Features

- **Multi-provider**: OpenAI, Anthropic, Gemini, OpenRouter, Perplexity, Vertex, any OpenAI-compatible endpoint
- **RAG Pipeline**: 3-tier web search (Tavily → self-hosted SearXNG → DuckDuckGo fallback)
- **Domain-aware search**: Topic-based site: filtering for 17 categories
- **Encrypted storage**: Provider keys and RAG context encrypted at rest with per-user encryption keys (UEK)
- **Manual model entry**: Type model names for proxy-only endpoints (e.g. Tailscale Aperture)
- **Android APK**: Self-contained Capacitor app with native HTTP, dark theme, and Tailscale support
- **K3s deployment**: Production on Kubernetes with GHCR images, Let's Encrypt TLS, and Traefik ingress

## Changelog (recent)

Full history in [Release Notes](docs/release-notes.md).

| Version | Changes |
|---------|---------|
| **v5.7.2** | Refresh tokens rejected as bearer tokens; unresolvable sessions fail closed with 401; prompt text removed from logs; SQLite foreign-key cascades enforced (deleting a user no longer orphans data); Alembic migrates the real `DATABASE_URL`; theme toggle and settings gear removed from the header's top-left (both remain reachable); hermetic unit tests |
| **v5.7.1** | Targeted search-query extraction, crypto domain knowledge |
| **v5.7.0** | Consensus topology; turn-intent analysis; deliberation rounds |
| **v5.6.0** | Perplexity provider; OAuth vault for Codex / Copilot / OpenRouter |
| **v5.5.0** | Folders; contribution weighting; agent personas |
| **v5.4.0** | Vertex AI support (project / region / ADC) |
| **v5.3.0** | TypeSafe System One integration; model thinking suppression |
| **v5.2.0** | Speed/smoothness improvements; subscription logins (ChatGPT, Gemini) |
