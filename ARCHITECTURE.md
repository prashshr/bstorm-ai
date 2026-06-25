# AI Ensemble — Architecture Document

> **Version:** 0.1.0  
> **Last Updated:** 2026-06-25  
> **Source of Truth:** This document defines the authoritative architecture of the AI Ensemble project. Every component, data flow, security boundary, and deployment detail is recorded here. Keep this in sync with all code changes.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Backend Architecture](#3-backend-architecture)
   - 3.1 [Application Entry & Configuration](#31-application-entry--configuration)
   - 3.2 [Database Layer](#32-database-layer)
   - 3.3 [Models (SQLAlchemy ORM)](#33-models-sqlalchemy-orm)
   - 3.4 [Schemas (Pydantic)](#34-schemas-pydantic)
   - 3.5 [Auth & Security](#35-auth--security)
   - 3.6 [API Routes](#36-api-routes)
   - 3.7 [Provider Service Layer](#37-provider-service-layer)
4. [Frontend Architecture](#4-frontend-architecture)
   - 4.1 [File Layout & Serving](#41-file-layout--serving)
   - 4.2 [Auth Flow](#42-auth-flow)
   - 4.3 [Discussion Lifecycle](#43-discussion-lifecycle)
   - 4.4 [State Management](#44-state-management)
   - 4.5 [Key Frontend Functions](#45-key-frontend-functions)
5. [Deployment Architecture](#5-deployment-architecture)
   - 5.1 [Kubernetes (k3s) Deployment](#51-kubernetes-k3s-deployment)
   - 5.2 [Docker Compose Deployment](#52-docker-compose-deployment)
   - 5.3 [Ingress & TLS](#53-ingress--tls)
   - 5.4 [Secrets Management](#54-secrets-management)
6. [Security Model](#6-security-model)
7. [Data Flow Diagrams](#7-data-flow-diagrams)
8. [API Reference](#8-api-reference)
9. [Development Guide](#9-development-guide)
10. [Production Readiness](#10-production-readiness)
11. [Versioning & Changelog](#11-versioning--changelog)

---

## 1. Project Overview

**AI Ensemble** is a multi-model AI discussion platform that lets users query multiple LLMs simultaneously on the same prompt, compare responses, and generate synthesized consensuses. It provides strong per-user isolation: each user has their own provider credentials (API keys), discussion history, message history, and search history — all stored server-side with encrypted API keys.

### Core Use Case

1. User authenticates (register/login)
2. User configures an LLM provider (endpoint + API key) — stored encrypted per user
3. User discovers available models from the provider
4. User selects 2-5 models, writes a question
5. System queries all selected models (per round, configurable rounds)
6. System generates a consensus summary from all model responses
7. Results are exported as Markdown or JSON

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI (Python 3.12) |
| **ORM** | SQLAlchemy 2.0 |
| **Database** | SQLite (default), PostgreSQL-ready |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **Encryption** | Fernet (symmetric via `cryptography`) |
| **HTTP Client** | httpx (async) |
| **Frontend** | Vanilla HTML/CSS/JS, single-page app |
| **Markdown Rendering** | marked.js (CDN) |
| **Reverse Proxy** | Caddy 2 (Docker Compose) / Traefik (k3s) |
| **Containerization** | Docker, k3s (Kubernetes) |
| **TLS** | Let's Encrypt via cert-manager |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Internet (HTTPS)                      │
│                  ai-ensemble.samkhya.cloud                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                Reverse Proxy (Caddy / Traefik)            │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │   /api/*     │    │         /*                    │   │
│  │   /health    │    │   Static files from /web      │   │
│  └──────┬───────┘    └──────────────────────────────┘   │
└─────────┼───────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8080)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Auth    │  │Provider  │  │Discussion│  │ Proxy  │ │
│  │  Routes  │  │ Routes   │  │ Routes   │  │ Route  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │              │             │             │       │
│       └──────────────┴─────────────┴─────────────┘       │
│                         │                                 │
│                         ▼                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │              SQLite / PostgreSQL DB                  │  │
│  │  users | provider_credentials | discussions |      │  │
│  │  messages | search_history                          │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Backend Architecture

### 3.1 Application Entry & Configuration

**File:** `backend/app/main.py`

- Creates FastAPI app with title `"AI Ensemble API"`, version `"0.1.0"`
- Adds CORS middleware with origins from `settings.cors_origins`
- Runs `init_db()` on startup event
- Exposes `GET /health` endpoint returning `{"status": "ok"}`
- Mounts API router at `/api` prefix

**File:** `backend/app/core/config.py`

- Uses `pydantic-settings` with `.env` file support
- Key settings:
  - `database_url`: default `sqlite:///./data/ai_ensemble.db`
  - `cors_origins`: default `["https://ai-ensemble.samkhya.cloud", "http://127.0.0.1:3000"]`
  - `jwt_secret`: default `"change-me-in-production"`
  - `jwt_algorithm`: `HS256`
  - `access_token_expire_minutes`: 1440 (24 hours)
  - `credential_encryption_key`: default `"change-me-32-byte-key-change-me-32"`

### 3.2 Database Layer

**File:** `backend/app/db/session.py`

- Creates SQLAlchemy `engine` with `check_same_thread=False` for SQLite
- Defines `SessionLocal` sessionmaker
- Provides `get_db()` generator for FastAPI dependency injection
- Provides `init_db()` which:
  1. Calls `Base.metadata.create_all(bind=engine)` to create tables
  2. Seeds default admin user `admin@local.ai-ensemble` / `arhatadmin` if not exists

### 3.3 Models (SQLAlchemy ORM)

**File:** `backend/app/models/models.py`

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| **User** | `users` | `id` (PK), `email` (unique, indexed), `password_hash`, `created_at` | — |
| **ProviderCredential** | `provider_credentials` | `id` (PK), `user_id` (FK→users), `provider`, `endpoint`, `api_key_encrypted`, `created_at` | Unique constraint on `(user_id, provider)` |
| **Discussion** | `discussions` | `id` (PK), `user_id` (FK→users), `title`, `question`, `status`, `created_at` | `messages` relationship (cascade delete) |
| **Message** | `messages` | `id` (PK), `discussion_id` (FK→discussions), `user_id` (FK→users), `round_number`, `model`, `role`, `content`, `created_at` | `discussion` back_populates |
| **SearchHistory** | `search_history` | `id` (PK), `user_id` (FK→users), `query`, `created_at` | — |

All user-owned data uses `user_id` foreign keys with `ondelete="CASCADE"` to ensure clean user deletion.

### 3.4 Schemas (Pydantic)

**Auth (`backend/app/schemas/auth.py`):**
- `RegisterRequest`: `email` (EmailStr), `password` (min 8, max 128)
- `LoginRequest`: `email` (EmailStr), `password`
- `TokenResponse`: `access_token`, `token_type` (default `"bearer"`)

**Provider (`backend/app/schemas/provider.py`):**
- `UpsertProviderCredentialRequest`: `provider` (min 2), `api_key` (min 1), `endpoint` (optional)
- `ProviderCredentialResponse`: `provider`, `endpoint`, `has_key` (bool)

**Provider Proxy (`backend/app/schemas/provider_proxy.py`):**
- `ChatRequest`: `provider`, `model`, `prompt`, `endpoint` (optional), `max_tokens` (default 1000), `temperature` (default 0.7)
- `ChatResponse`: `provider`, `model`, `output`

**Discussion (`backend/app/schemas/discussion.py`):**
- `DiscussionCreateRequest`: `question` (min 1), `title` (optional)
- `MessageCreateRequest`: `discussion_id`, `round_number` (default 1), `model`, `role` (default "assistant"), `content`
- `DiscussionResponse`: `id`, `title`, `question`, `status`, `created_at`
- `MessageResponse`: `id`, `discussion_id`, `round_number`, `model`, `role`, `content`, `created_at`

### 3.5 Auth & Security

**Password Hashing (`backend/app/core/security.py`):**
- Uses `passlib.context.CryptContext` with bcrypt scheme
- `verify_password(plain, hashed)`: boolean comparison
- `get_password_hash(password)`: returns bcrypt hash string
- `create_access_token(subject)`: creates JWT with `sub` = user_id (string), expiry = configured minutes from now

**API Key Encryption (`backend/app/core/crypto.py`):**
- Uses `cryptography.fernet.Fernet` for symmetric encryption
- Key derived from `settings.credential_encryption_key` (padded/truncated to 32 bytes, base64-encoded)
- `encrypt_secret(value)`: returns encrypted string
- `decrypt_secret(value)`: returns decrypted plaintext

**Auth Dependency (`backend/app/api/deps.py`):**
- Uses `OAuth2PasswordBearer(tokenUrl="/api/auth/login")`
- `get_current_user`: decodes JWT, extracts `sub` as user_id, queries DB for User
- Returns 401 on invalid/missing token or nonexistent user

### 3.6 API Routes

**Router Mounting (`backend/app/api/router.py`):**

| Prefix | Router File | Tags |
|--------|-------------|------|
| `/api/auth` | `routes/auth.py` | auth |
| `/api/providers` | `routes/providers.py` | providers |
| `/api/discussions` | `routes/discussions.py` | discussions |
| `/api/proxy` | `routes/proxy.py` | proxy |

#### Auth Routes (`backend/app/api/routes/auth.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register` | Register new user, return JWT | No |
| POST | `/api/auth/login` | Login, return JWT | No |

- Register: checks for duplicate email (409 Conflict), creates User with hashed password, returns token
- Login: validates credentials (401 on failure), returns token

#### Provider Routes (`backend/app/api/routes/providers.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/providers` | Upsert provider credential | Yes |
| GET | `/api/providers` | List user's provider credentials (keys redacted) | Yes |
| GET | `/api/providers/{provider}/models` | Discover models from provider | Yes |

- POST: encrypts API key with Fernet before storing. Uses `ON CONFLICT` upsert pattern (deletes old then inserts new).
- GET (list): returns all credentials for current user with `has_key: true` but never sends the key value.
- GET (models): decrypts user's key, calls provider client's `list_models()`. Returns 502 on provider errors.

#### Discussion Routes (`backend/app/api/routes/discussions.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/discussions` | Create discussion + search history entry | Yes |
| GET | `/api/discussions` | List user's discussions (newest first) | Yes |
| GET | `/api/discussions/{id}/messages` | List messages in discussion (ownership-checked) | Yes |
| POST | `/api/discussions/messages` | Create message in discussion (ownership-checked) | Yes |

All discussion endpoints filter by `current_user.id` to enforce per-user isolation.

#### Proxy Routes (`backend/app/api/routes/proxy.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/proxy/chat` | Proxy chat to provider using user's stored key | Yes |

- Fetches user's encrypted credential for the specified provider
- Decrypts the API key
- Calls `client.chat()` via the provider service layer
- Returns `ChatResponse` with model output

### 3.7 Provider Service Layer

**Architecture: Abstract Base + Factory + Implementations**

```
ProviderClient (ABC)          ← base.py
    ├── OpenAICompatibleClient  ← openai_compatible.py
    ├── GeminiClient            ← gemini.py
    └── AnthropicClient         ← anthropic.py
```

**File:** `backend/app/services/providers/base.py`

- `ProviderClient` is an abstract base class with two abstract methods:
  - `list_models(endpoint, api_key) → list[str]`
  - `chat(endpoint, api_key, model, prompt, max_tokens, temperature) → str`

**File:** `backend/app/services/providers/factory.py`

- Maps provider names to implementations via `PROVIDER_ALIASES` dictionary:
  - `openai`, `openrouter`, `azure-openai`, `openai-compatible` → `OpenAICompatibleClient`
  - `anthropic` → `AnthropicClient`
  - `google`, `gemini` → `GeminiClient`
  - Unknown providers default to `OpenAICompatibleClient`

**OpenAICompatibleClient (`openai_compatible.py`):**
- `list_models`: GET `{endpoint}/models` with Bearer auth, extracts `data[].id`
- `chat`: POST `{endpoint}/chat/completions` with standard OpenAI payload, extracts `choices[0].message.content`
- Falls back to `https://api.openai.com/v1` if no endpoint provided

**GeminiClient (`gemini.py`):**
- `list_models`: GET `{endpoint}/v1beta/models?key={api_key}`, extracts model name from `name` field
- `chat`: POST `{endpoint}/v1beta/models/{model}:generateContent?key={api_key}` with Gemini payload
- Falls back to `https://generativelanguage.googleapis.com` if no endpoint

**AnthropicClient (`anthropic.py`):**
- `list_models`: returns `[]` (no stable API)
- `chat`: POST `{endpoint}/v1/messages` with Anthropic headers and payload, extracts `content[0].text`
- Falls back to `https://api.anthropic.com`

---

## 4. Frontend Architecture

### 4.1 File Layout & Serving

**In k3s deployment:** `web/index.html` is served by nginx from `/usr/share/nginx/html/`
**In Docker Compose:** `web/` directory is served by Caddy from `/srv/`

The frontend is a **single-page application** (~2436 lines) containing all CSS, HTML, and JavaScript in one file.

| File | Purpose |
|------|---------|
| `web/index.html` | Main SPA served in production (2436 lines) |
| `web/ai-ensemble-v5.html` | Standalone prototype (9 lines — redirected) |
| `web/index.html` (at root of web/) | Redirect to `/` via meta refresh |

### 4.2 Auth Flow

The frontend implements token-based auth with a UI panel for login/register:

1. **Login/Register API calls** use `POST /api/auth/login` and `POST /api/auth/register`
2. Plain usernames are normalized to `username@local.ai-ensemble` for backend `EmailStr` validation
3. JWT token is stored in `sessionStorage` (cleared on tab close)
4. All authenticated API calls use the `authFetch()` helper which adds `Authorization: Bearer <token>` header
5. `requireAuth()` gate checks for token presence before sensitive operations
6. Logout clears `sessionStorage` and resets the UI to setup state

**Key auth functions:**

| Function | Description |
|----------|-------------|
| `authFetch(url, options)` | Wrapper around fetch that adds JWT Bearer header |
| `requireAuth(action)` | Checks token, shows login prompt if missing |
| `handleLogin()` | Reads email/password, calls `/api/auth/login`, stores token |
| `handleRegister()` | Reads email/password, calls `/api/auth/register`, stores token |
| `handleLogout()` | Clears sessionStorage, resets UI |

### 4.3 Discussion Lifecycle

```
Setup → Auth → Provider Config → Discover Models → Select Models
    → Write Question → Configure Rounds → Run Discussion
    → View Responses → Generate Consensus → Export
```

**Detailed flow:**

1. **Setup Phase** (tab: "Setup") — User authenticates, configures provider endpoint + API key, discovers models, selects 2-5 models, writes question with optional attachments
2. **Discussion Phase** (tab: "Current") — Models are queried sequentially per round:
   - Each model gets a card showing connection status, response text, and stats
   - Retry/skip controls for failed models
   - Progress bar shows overall completion
   - Collapsible round timeline with expand/fullscreen response options
3. **Consensus Phase** — After all rounds, a consensus model synthesizes all responses
   - Configurable format: compact or elaborate
   - Shows final consensus text with warnings if truncated
4. **Export Phase** — Export as Markdown, JSON, or copy to clipboard

### 4.4 State Management

**In-memory state** (the `discussionData` object):

```javascript
discussionData = {
    id: null,                    // Backend discussion ID (if persisted)
    question: '',
    instructions: '',
    summaryFormat: 'elaborate',  // 'compact' | 'elaborate'
    models: [],                  // Array of selected model IDs
    endpoint: '',
    apiKey: '',                  // NEVER persisted to localStorage
    rounds: {                    // keyed by round number
        '1': {
            'gpt-4o': { text: '...', status: 'complete', stats: {...} },
            'claude-3': { text: '...', status: 'error' }
        }
    },
    consensus: '',
    stats: {
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalTokens: 0,
        avgDurationMs: 0,
        peakContext: { percent: 0, model: '', round: 0 },
        modelCount: 0
    },
    status: 'running',
    timestamp: Date.now()
}
```

**localStorage persistence:**
- `councilState` — Full `discussionData` for session restore
- `councilHistory` — Array of past discussions (used for history tab)
- API key is NEVER written to localStorage

### 4.5 Key Frontend Functions

| Function | Purpose |
|----------|---------|
| `authFetch()` | Authenticated fetch wrapper |
| `saveProviderCredential()` | POST to `/api/providers` with encrypted key |
| `loadUserProviderConfig()` | GET from `/api/providers` to populate saved config |
| `discoverModels()` | GET `/api/providers/{provider}/models` |
| `queryModel()` | POST `/api/proxy/chat` for a single model |
| `startDiscussion()` | Orchestrates all rounds |
| `generateConsensus()` | POST `/api/proxy/chat` for consensus |
| `retryModel()` / `skipModel()` | Per-model error recovery |
| `saveState()` / `restoreLastDiscussion()` | localStorage persistence |
| `exportMarkdown()` / `exportJSON()` | Export functions |
| `switchTab()` | Tab navigation |
| `renderHistory()` / `loadDiscussion()` | History management |
| `toggleTheme()` | Dark/light theme toggle |
| `toggleDebug()` | Debug log panel |
| `toggleExpand()` / `toggleFullscreen()` | Response view controls |

**File upload support:**
- Drag-and-drop or click to upload
- Accepted: `.txt`, `.pdf`, `.doc`, `.docx`, `.md`, `.csv`, `.json`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
- Max 10MB per file
- File content is read as text and prepended to the user's prompt

---

## 5. Deployment Architecture

### 5.1 Kubernetes (k3s) Deployment

**Namespace:** `ai-ensemble`

**Manifests** in `kube-manifests/`:

| Manifest | Resource | Details |
|----------|----------|---------|
| `namespace.yaml` | Namespace | `ai-ensemble` |
| `configmap.yaml` | ConfigMap | Non-sensitive env vars (JWT_ALGORITHM, DB URL, CORS) |
| `secret.yaml.example` | Template | Template for k8s Secret |
| `deployment.yaml` | Deployment | API backend: 1 replica, port 8080, hostPath volume for data |
| `service.yaml` | Service | ClusterIP on port 8080 |
| `web-deployment.yaml` | Deployment | nginx: 1 replica, port 80, hostPath for web files |
| `web-service.yaml` | Service | ClusterIP on port 80 |
| `cert.yaml` | Certificate | Let's Encrypt TLS cert for `ai-ensemble.samkhya.cloud` |
| `ingress.yaml` | Ingress | Traefik ingress: `/api` → backend, `/` → web, TLS |
| `apply.sh` | Script | Orchestrates `kubectl apply` in correct order |
| `create-secret.sh` | Script | Reads `.env`, creates k8s Secret |

**Backend deployment spec:**
- Image: `ai-ensemble:local` (built locally, loaded into k3s containerd)
- Liveness probe: HTTP `/health`, 20s initial delay
- Readiness probe: HTTP `/health`, 10s initial delay
- Resources: request 200m CPU / 384Mi RAM, limit 1000m CPU / 1Gi RAM
- Env from ConfigMap + Secret
- Volume: hostPath at `/arbeit/ai-welt/projects/ai-ensemble/data`

### 5.2 Docker Compose Deployment

**File:** `docker-compose.yml`

Two services:
1. **api**: Builds from `./backend/Dockerfile`, exposes port 8080, volume-mounts `./data:/data`
2. **web**: Uses `caddy:2.8` image, ports 8080:80 / 8444:443, serves `./web:/srv`, reverse proxies `/api/*` to api:8080

### 5.3 Ingress & TLS

**Caddy (Docker Compose):**
- Auto-TLS via Let's Encrypt
- Reverse proxies `/api/*` and `/health` to `api:8080`
- Serves static files from `/srv`
- Security headers: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy

**Traefik (k3s):**
- Ingress class: `traefik`
- TLS secret: `ai-ensemble-tls` (provisioned by cert-manager)
- Path routing: `/api` Prefix → backend ClusterIP:8080, `/` Prefix → web ClusterIP:80

### 5.4 Secrets Management

**In k3s:**
- Secret `ai-ensemble-secrets` created by `create-secret.sh` from `.env` file
- Contains `JWT_SECRET` and `CREDENTIAL_ENCRYPTION_KEY`
- Applied before deployments via `apply.sh`

**In Docker Compose:**
- Environment variables passed directly to `api` service
- `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY` from shell environment

**Important:** Never commit `.env` files. The `.gitignore` excludes `.env` and `.env.*`.

---

## 6. Security Model

| Concern | Implementation |
|---------|---------------|
| **Password storage** | bcrypt via passlib, never plaintext |
| **API key storage** | Fernet-encrypted per user in DB, never in localStorage |
| **Auth tokens** | JWT with 24h expiry, stored in sessionStorage (cleared on tab close) |
| **Per-user isolation** | All DB queries filter by `user_id` from JWT |
| **CORS** | Restricted to known origins (`samkhya.cloud` + `localhost:3000`) |
| **HTTPS** | Enforced by Caddy auto-TLS / Let's Encrypt cert-manager |
| **Encryption key** | `CREDENTIAL_ENCRYPTION_KEY` must be changed per deployment |
| **JWT secret** | `JWT_SECRET` must be changed per deployment |
| **API key in transit** | Never sent to frontend after save (only `has_key: true`) |
| **Token expiry** | Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` |

---

## 7. Data Flow Diagrams

### 7.1 Authentication Flow

```
Frontend                     Backend                     DB
   │                           │                         │
   │  POST /api/auth/register  │                         │
   │  {email, password}        │                         │
   │──────────────────────────►│                         │
   │                           │  Check duplicate email  │
   │                           │────────────────────────►│
   │                           │◄────────────────────────│
   │                           │  Hash password (bcrypt) │
   │                           │  Create user row        │
   │                           │────────────────────────►│
   │                           │◄────────────────────────│
   │  {access_token, bearer}   │  Create JWT (sub=user_id)│
   │◄──────────────────────────│                         │
   │  Store token in           │                         │
   │  sessionStorage           │                         │
```

### 7.2 Provider Credential Flow

```
Frontend                     Backend                     DB
   │                           │                         │
   │  POST /api/providers      │                         │
   │  {provider, api_key,      │                         │
   │   endpoint} + JWT         │                         │
   │──────────────────────────►│                         │
   │                           │  Verify JWT → user_id   │
   │                           │  Encrypt api_key        │
   │                           │  Upsert credential      │
   │                           │────────────────────────►│
   │  {provider, endpoint,     │◄────────────────────────│
   │   has_key: true}          │                         │
   │◄──────────────────────────│                         │
```

### 7.3 Chat Proxy Flow

```
Frontend                     Backend                     Provider API
   │                           │                         │
   │  POST /api/proxy/chat     │                         │
   │  {provider, model, prompt,│                         │
   │   ...} + JWT              │                         │
   │──────────────────────────►│                         │
   │                           │  Verify JWT → user_id   │
   │                           │  Fetch credential       │
   │                           │  Decrypt api_key        │
   │                           │  Call provider API      │
   │                           │────────────────────────►│
   │                           │◄────────────────────────│
   │  {provider, model,        │  Response text          │
   │   output: "..."}          │                         │
   │◄──────────────────────────│                         │
```

---

## 8. API Reference

### Authentication

| Endpoint | Method | Auth | Request Body | Response |
|----------|--------|------|-------------|----------|
| `/api/auth/register` | POST | No | `{email: EmailStr, password: str(8-128)}` | `{access_token, token_type}` |
| `/api/auth/login` | POST | No | `{email: EmailStr, password: str}` | `{access_token, token_type}` |

### Provider Credentials

| Endpoint | Method | Auth | Request Body | Response |
|----------|--------|------|-------------|----------|
| `/api/providers` | POST | JWT | `{provider, api_key, endpoint?}` | `{provider, endpoint, has_key}` |
| `/api/providers` | GET | JWT | — | `[{provider, endpoint, has_key}]` |
| `/api/providers/{provider}/models` | GET | JWT | — | `["model1", "model2", ...]` |

### Proxy

| Endpoint | Method | Auth | Request Body | Response |
|----------|--------|------|-------------|----------|
| `/api/proxy/chat` | POST | JWT | `{provider, model, prompt, endpoint?, max_tokens?, temperature?}` | `{provider, model, output}` |

### Discussions

| Endpoint | Method | Auth | Request Body | Response |
|----------|--------|------|-------------|----------|
| `/api/discussions` | POST | JWT | `{question, title?}` | `{id, title, question, status, created_at}` |
| `/api/discussions` | GET | JWT | — | `[{id, title, question, status, created_at}]` |
| `/api/discussions/{id}/messages` | GET | JWT | — | `[{id, discussion_id, round_number, model, role, content, created_at}]` |
| `/api/discussions/messages` | POST | JWT | `{discussion_id, round_number, model, role, content}` | `{id, discussion_id, round_number, model, role, content, created_at}` |

### Health

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/health` | GET | No | `{"status": "ok"}` |

---

## 9. Development Guide

### Local Development

```bash
# Start backend with hot reload
cd backend
uvicorn app.main:app --reload --port 8080

# Start frontend dev server
cd web
python3 -m http.server 3000
```

### Docker Build & Deploy (k3s)

```bash
# Build backend image
docker build -t ai-ensemble:local ./backend

# Load into k3s
ctr -n k8s.io images import /path/to/image.tar

# Or use the helper
docker save ai-ensemble:local | ctr -n k8s.io images import -

# Deploy
cd kube-manifests
kubectl create ns ai-ensemble --dry-run=client -o yaml | kubectl apply -f -
bash create-secret.sh
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f web-deployment.yaml
kubectl apply -f web-service.yaml
kubectl apply -f cert.yaml
kubectl apply -f ingress.yaml
```

### Docker Compose

```bash
cd ai-ensemble
export JWT_SECRET="..." CREDENTIAL_ENCRYPTION_KEY="..."
docker compose up -d --build
```

### Adding a New Provider

1. Create a new class in `backend/app/services/providers/` implementing `ProviderClient`
2. Add an alias in `PROVIDER_ALIASES` in `factory.py`
3. Register the new class in the `get_provider_client()` function

### Database Migrations

Currently using SQLAlchemy `create_all()` on startup. For schema changes:
1. Update the model in `models.py`
2. Delete the SQLite database file (data will be lost) or use Alembic (migrations not yet configured)

---

## 10. Production Readiness

See `PRODUCTION_PLAN.md` for full details. Key checklist:

- [x] Auth with per-user isolation
- [x] Encrypted API key storage
- [x] HTTPS with Let's Encrypt
- [ ] Rate limiting (not implemented)
- [ ] Audit logging (not implemented)
- [ ] CSP headers (partial — Caddy adds HSTS etc.)
- [ ] Input sanitization (not implemented)
- [ ] Regular DB backups (not configured)
- [ ] Resource monitoring (not configured)
- [ ] CI/CD pipeline (not configured)

---

## 11. Versioning & Changelog

Version format: `v<major>.<minor>.<patch>-<YYYYMMDD>` (e.g., `v0.1.0-20260625`)

### v0.1.0 (2026-06-25)

- Initial production-ready architecture
- FastAPI backend with JWT auth, bcrypt passwords, encrypted provider credentials
- Vanilla JS frontend with multi-model discussion, consensus generation, export
- k3s deployment with Let's Encrypt TLS
- Provider abstraction layer (OpenAI-compatible, Gemini, Anthropic)
- Per-user data isolation for discussions, messages, search history
- Default admin seeder: `admin@local.ai-ensemble` / `arhatadmin`

---

*This document is the authoritative source of truth for the AI Ensemble project architecture. Update it whenever the codebase changes.*