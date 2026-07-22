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

## Docker Compose

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

## Kubernetes (Production)

```bash
./deploy/k8s/apply.sh
```

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

| Version | Changes |
|---------|---------|
| **v3.3.0** | Manual model entry for proxy-only endpoints; CapacitorHttp CORS fix; Android APK improvements |
| **v3.2.1** | Custom provider unique keys; self-contained APK; dark theme refinements |
| **v3.2.0** | DB-backed mobile sessions; RAG timeout fix; multimodal attachments; Android dark theme |
