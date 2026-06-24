# AI Ensemble

AI Ensemble is a multi-model discussion UI for comparing and synthesizing answers from multiple AI providers.

## Current State

This project is currently a prototype front-end in `ai-ensemble-v5.html` served as static content.
It is not yet production-ready for public internet use.

## Repository Layout

- `ai-ensemble-v5.html` - main prototype app
- `scripts/run-dev.sh` - consolidated local dev server script
- `README.md` - primary project documentation
- `README_REVIEW.md`, `REVIEW_SUMMARY.md`, `PRODUCTION_READINESS_REVIEW.md`, `IMPROVEMENTS_CODE_GUIDE.md`, `ACTION_PLAN.md` - review and planning documents

## Local Development

Run a local HTTP server on `127.0.0.1:3000`:

```bash
./scripts/run-dev.sh
```

Open: `http://127.0.0.1:3000/`

## Production-Ready Architecture Plan

### 1. Reverse Proxy + TLS + Domain

Target domain: `https://ai-ensemble.samkhya.cloud`

Use a reverse proxy with automatic Let's Encrypt certificate management:

- Option A: Caddy (simplest automatic TLS)
- Option B: Nginx + certbot
- Option C: Traefik (if already using container/k8s stack)

Recommended ports and exposure:

- Expose only `80` and `443` publicly
- Bind application service to loopback/private network only (for example `127.0.0.1:8080`)
- Deny direct access to admin/debug routes

### 2. App Backend (required)

Move provider API calls from browser to backend.

Why:

- Avoid exposing provider API keys to browser/localStorage
- Enforce per-user authorization and quotas
- Add audit logs and abuse controls

Suggested stack:

- FastAPI or Flask backend
- SQLite/PostgreSQL for users, sessions, provider configs, discussion history
- Server-side encrypted storage for provider keys

### 3. Authentication and User Isolation

Implement local user accounts with password auth:

- Table: users
- Table: sessions (server-issued, HTTP-only secure cookies)
- Table: provider_keys (user-scoped, encrypted at rest)
- Table: discussions (user_id foreign key)
- Table: messages / rounds (user_id + discussion_id)

Security requirements:

- Password hashing with Argon2 or bcrypt
- CSRF protection for cookie-based auth
- Strict per-request authorization checks by `user_id`
- No raw provider keys returned to frontend

### 4. Provider Abstraction (multi-provider)

Create a provider adapter layer to support:

- OpenAI
- Anthropic
- Google Gemini
- OpenRouter
- Azure OpenAI
- Any OpenAI-compatible endpoint

Design notes:

- Unified request/response schema in backend
- Provider-specific adapters map to each API format
- Per-user default provider/model preferences
- Optional fallback chain and retry policy

### 5. Minimize Exposure

Do not expose:

- Debug endpoints
- Internal metrics unauthenticated
- Raw trace/log dumps
- Environment or config files

Hardening:

- Rate limiting by IP and user
- Request body limits
- Security headers (CSP, HSTS, X-Frame-Options, Referrer-Policy)
- Centralized structured logging

## Suggested Implementation Milestones

1. Backend foundation: auth, DB models, basic API
2. Move current frontend calls to backend endpoints
3. Add provider adapters and key vault/encryption
4. Add user history and search history endpoints
5. Deploy behind Caddy/Nginx with TLS for `ai-ensemble.samkhya.cloud`
6. Add tests (auth, data isolation, provider routing)

## Git Hygiene Rules Applied

The repository now ignores:

- `debugging/`
- `QUICK_REFERENCE.txt`
- `.reasonix/`
- local env/log/db/runtime files

If these files are already tracked, remove from git index while preserving local files:

```bash
git rm -r --cached debugging .reasonix QUICK_REFERENCE.txt
```

## Next Recommended Deliverables

- `backend/` service with auth + DB models
- `docker-compose.yml` for app + reverse proxy
- production deploy docs for DNS + TLS + firewall
- migration notes from prototype localStorage data to user-scoped DB

## Production Deployment (Live Domain + Let's Encrypt)

This repo now includes:

- FastAPI backend with local user auth (`/api/auth/register`, `/api/auth/login`)
- User-scoped SQLite persistence for users, provider keys, discussions, messages, and search history
- Caddy reverse proxy with automatic Let's Encrypt certificates for `ai-ensemble.samkhya.cloud`

### Prerequisites

1. DNS `A`/`AAAA` for `ai-ensemble.samkhya.cloud` points to this server
2. Ports `80` and `443` open inbound
3. Docker Engine + Docker Compose plugin installed
4. Nothing else bound to `80/443`

### Configure Secrets

Copy and edit env file:

```bash
cp .env.example .env
```

Set strong values in `.env`:

- `JWT_SECRET` (long random secret)
- `CREDENTIAL_ENCRYPTION_KEY` (32+ chars)

### Deploy

```bash
./scripts/deploy-prod.sh
```

### Verify

```bash
docker compose ps
docker compose logs -f web api
```

Expected endpoints:

- App: `https://ai-ensemble.samkhya.cloud`
- API health: `https://ai-ensemble.samkhya.cloud/health`

### Auth API (Local Login Enabled)

- Register: `POST /api/auth/register`
- Login: `POST /api/auth/login`

These issue bearer tokens for authenticated user-scoped API access.
