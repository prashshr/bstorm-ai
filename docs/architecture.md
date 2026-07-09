# AI Ensemble — Architecture Document

> **Version:** 0.7.0  
> **Last Updated:** 2026-07-09  
> **Source of Truth:** This document defines the authoritative architecture of the AI Ensemble project. Every component, data flow, security boundary, and deployment detail is recorded here. **Any LLM, AI coding agent, or developer working on this project MUST read this document first and follow all rules, conventions, and architectural decisions defined herein.** Keep this in sync with all code changes — updating this file is a mandatory part of every feature or fix.

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
| **Web Search (RAG)** | Tavily API (primary) → Self-hosted SearXNG (secondary) → DuckDuckGo HTML (fallback) |
| **Content Extraction** | trafilatura |
| **Frontend** | Vanilla HTML/CSS/JS, single-page app |
| **Markdown Rendering** | marked.js (CDN) |
| **Reverse Proxy** | Caddy 2 (Docker Compose) / Traefik (k3s) |
| **Containerization** | Docker, k3s (Kubernetes) |
| **Container Registry** | GHCR (ghcr.io/prashshr/ai-ensemble) |
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
  - `tavily_api_key`: optional, for Tavily web search
  - `searxng_url`: default `"http://searxng-svc:8080"`

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
| **Discussion** | `discussions` | `id` (PK), `user_id` (FK→users), `title`, `question`, `status`, `state_json`, `retrieved_context_encrypted`, `created_at` | `messages` relationship (cascade delete) |
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
- `ChatRequest`: `provider`, `model`, `prompt`, `endpoint` (optional), `max_tokens` (default 1000), `temperature` (default 0.7), `discussion_id` (optional), `include_rag_context` (default false)
- `ChatResponse`: `provider`, `model`, `output`

**Discussion (`backend/app/schemas/discussion.py`):**
- `DiscussionCreateRequest`: `question` (min 1), `title` (optional), `use_rag` (default false), `deep_research` (default false)
- `MessageCreateRequest`: `discussion_id`, `round_number` (default 1), `model`, `role` (default "assistant"), `content`
- `DiscussionResponse`: `id`, `title`, `question`, `status`, `state_json`, `retrieved_context` (optional), `created_at`
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

### 3.8 RAG / Web Search Service

**File:** `backend/app/services/retrieval.py`

The RAG pipeline provides web-retrieved context that is injected into LLM prompts as **supplementary information** — models are never restricted to only using RAG data. They may use their own training data, built-in browsing capabilities, or any other knowledge sources.

**3-Tier Search Architecture (in priority order):**

| Tier | Engine | Auth Required | Quality | Notes |
|------|--------|---------------|---------|-------|
| 1 | **Tavily API** | `TAVILY_API_KEY` | Highest | Purpose-built for AI RAG, returns clean parsed content. Free tier: 1,000 queries/month. |
| 2 | **Self-hosted SearXNG** | None (in-cluster) | High | Deployed as a pod in the same K3s namespace. No rate limits, full control over engines. |
| 3 | **DuckDuckGo HTML** | None | Medium | Public fallback. Scrapes HTML search results. No API key needed. |

**Pipeline flow:**

```
get_retrieved_context(user_prompt)
  │
  ├─ Tier 1: _search_tavily(query)
  │   POST https://api.tavily.com/search
  │   Returns: 5 results with title, url, content
  │   On failure → Tier 2
  │
  ├─ Tier 2: _search_searxng(query)
  │   GET http://searxng-svc:8080/search?format=json
  │   Returns: up to 39 results with title, url, content
  │   On failure → Tier 3
  │
  ├─ Tier 3: _search_duckduckgo(query)
  │   GET https://html.duckduckgo.com/html/
  │   Parses HTML with lxml, extracts real URLs from redirect wrappers
  │   Returns: up to 10 results
  │
  └─ extract_content_from_urls(urls)
       Uses trafilatura.fetch_url + trafilatura.extract (offloaded to thread pool via asyncio.to_thread)
       Returns: concatenated text content from up to 10 URLs

**Key design decisions:**
- **10 results per query**: Tavily configured for 10 results; the pipeline extracts content from all 10 URLs for comprehensive coverage
- **Multiple queries**: If the user prompt can be split into multiple search queries, each generates up to 10 results (deduplicated)
- **Additive context**: Retrieved context is prefixed with `"[Web Research Context]\n...\n\n[User Question]\n"` — models are NOT restricted to RAG data
- **Async-safe extraction**: `trafilatura` calls are wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- **URL deduplication**: Each tier tracks `unique_urls` to avoid duplicate content
- **Graceful degradation**: If all 3 tiers fail, `get_retrieved_context` returns `None` and the discussion proceeds without web context
- **Debug logging**: All pipeline steps log to `ai_ensemble.rag` logger at INFO/DEBUG level with `[RAG]` prefix

**RAG context injection in proxy chat:**
When `ChatRequest.include_rag_context` is `true` and `discussion_id` is provided, the proxy endpoint (`backend/app/api/routes/proxy.py`) fetches the discussion's `retrieved_context_encrypted`, decrypts it, and prepends it to the user's prompt:

```
[Web Research Context]
{retrieved_context}

---

[User Question]
{original_prompt}
```

---

## 4. Frontend Architecture

### 4.1 File Layout & Serving

**In k3s deployment:** `frontend/index.html` is served by nginx from `/usr/share/nginx/html/`
**In Docker Compose:** `frontend/` directory is served by Caddy from `/srv/`

The frontend is a **single-page application** containing all CSS, HTML, and JavaScript in one file.

| File | Purpose |
|------|---------|
| `frontend/index.html` | Main SPA served in production (approx. 3300 lines after layout enhancements) |
| `frontend/ai-ensemble-v5.html` | Standalone template prototype in sync with main entrypoint |

#### Advanced Multi-Column Dashboard Layout
The dashboard layout is designed to maximize screen real estate and mimic a high-performance IDE/control center:
1. **Providers Sidebar (Far Left):** Expandable column (`.left-panel`) housing active API endpoints and credentials status with real-time connectivity status dots.
2. **Sliding Models Column (Middle Left):** A collapsible panel (`.models-panel`) that dynamically slides outward upon selecting a provider, rendering a checklist of discoverable models.
3. **Main Workspace (Center/Right):** Includes:
   - **Segmented Main Tabs (Top Center):** Horizontal tab control switching cleanly between *New Discussion*, *Current Discussion*, and *History*.
   - **Collapsible Settings Card:** A toggleable header block that folds away all model configurations (Rounds, Timeouts, Tokens, Consensus model) to keep the viewport clean.
   - **Interactive Expandable Debate Cards:** Within each round, model response cards (`.model-card`) render in a responsive side-by-side grid. Clicking on any card toggles the `.expanded` state, stretching the card across the full width of the container via `grid-column: 1 / -1 !important` for structured readability.
   - **Summary Consensus Panel:** A dedicated block at the bottom capturing the consensus synthesis and export capabilities (Markdown/JSON/Clipboard).

### 4.2 Auth Flow

The frontend implements a secure, **independent centered login interface** that completely separates credential entry from the main application view:

**Unauthenticated State:**
- The entire app workspace container (`#appContainer`) is hidden (`display: none;`).
- An independent centered credential card container (`#loginPage`) is rendered at the body root, offering a fully focused login/registration gate.
- No application sidebars, headers, tabs, or settings are exposed to unauthenticated users.

**Authenticated State:**
- Upon successful login/registration, `sessionStorage` stores the JWT token and current username.
- `updateAuthUi()` toggles visibility: `#loginPage` is hidden, `#appContainer` displays, and a persistent **header-right section** displays the authenticated username alongside an instant **Logout** button.
- Re-securing the page is immediate: clicking logout clears `sessionStorage` and swaps visibility back, immediately returning to the login gate.

**Auth mechanics:**
- Plain usernames are normalized to `username@local.ai-ensemble` for backend `EmailStr` validation.
- JWT token is stored in browser `sessionStorage` (restricted to current session lifecycle and automatically cleared on browser/tab exit).
- All authenticated API calls use the `authFetch()` helper which adds the `Authorization: Bearer <token>` header.
- Logout clears `sessionStorage` and immediately swaps views.

**Key auth functions:****Key auth functions:**

| Function | Purpose |
|----------|---------|
| `authFetch(url, options)` | Wrapper around fetch that adds JWT Bearer header |
| `requireAuth(action)` | Checks token, shows login prompt if missing |
| `overlayLogin()` | Login from the full-screen overlay |
| `overlayRegister()` | Register from the full-screen overlay |
| `handleLogin()` | Login from the inline auth panel |
| `handleRegister()` | Register from the inline auth panel |
| `handleLogout()` | Clears sessionStorage, resets UI, shows overlay |
| `setAuth(token, email)` | Stores token, hides overlay, loads provider config |
| `loadAuth()` | Checks sessionStorage on page load, shows/hides overlay |

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

**Manifests** in `deploy/k8s/`:

 | Manifest | Resource | Details |
|----------|----------|---------|
| `namespace.yaml` | Namespace | `ai-ensemble` |
| `configmap.yaml` | ConfigMap | Non-sensitive env vars (JWT_ALGORITHM, DB URL, CORS, SEARXNG_URL) |
| `secret.yaml.example` | Template | Template for k8s Secret |
| `searxng-settings-configmap.yaml` | ConfigMap | SearXNG internal configuration (JSON API enabled, rate limiting disabled) |
| `searxng-deployment.yaml` | Deployment+Service | Self-hosted SearXNG: 1 replica, port 8080, custom settings.yml via ConfigMap |
| `deployment.yaml` | Deployment | API backend: 1 replica, port 8080, GHCR image, hostPath volume for data |
| `service.yaml` | Service | ClusterIP on port 8080 |
| `web-deployment.yaml` | Deployment | nginx: 1 replica, port 80, hostPath for web files |
| `web-service.yaml` | Service | ClusterIP on port 80 |
| `cert.yaml` | Certificate | Let's Encrypt TLS cert for `ai-ensemble.samkhya.cloud` |
| `ingress.yaml` | Ingress | Traefik ingress: `/api` → backend, `/health` → backend, `/` → web, TLS |
| `apply.sh` | Script | Orchestrates `kubectl apply` in correct order |
| `create-secret.sh` | Script | Reads `.env`, creates k8s Secret |

**Backend deployment spec:**
- Image: `ghcr.io/prashshr/ai-ensemble:latest` (pushed to GitHub Container Registry)
- Image pull policy: `Always`
- Image pull secret: `ghcr-pull-secret` (docker-registry type for GHCR auth)
- Liveness probe: HTTP `/health`, 20s initial delay
- Readiness probe: HTTP `/health`, 10s initial delay
- Resources: request 200m CPU / 384Mi RAM, limit 1000m CPU / 1Gi RAM
- Env from ConfigMap + Secret (includes `TAVILY_API_KEY` for web search)
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
- Contains `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, and `TAVILY_API_KEY`
- Applied before deployments via `apply.sh`
- A separate `ghcr-pull-secret` (docker-registry type) is created manually for GHCR image pulls

**In Docker Compose:**
- Environment variables passed directly to `api` service
- `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY` from shell environment

**Important:** Never commit `.env` files. The `.gitignore` excludes `.env` and `.env.*`.

---

## 6. Security Model

| Concern | Implementation |
|---------|---------------|
| **Password storage** | bcrypt via passlib, never plaintext |
| **API key storage** | Fernet-encrypted per user in DB using the user-specific User Encryption Key (UEK), never in localStorage. Unreadable with direct DB access. |
| **Discussion & History storage** | Discussion titles, questions, state JSON, message contents, and search queries are all Fernet-encrypted using the user-specific UEK. Genuinely private and unreadable by anyone without the user's actual password. |
| **User Encryption Key (UEK)** | A random 32-byte master key generated per-user, encrypted using a Password-Derived Key (PDK) via PBKDF2-HMAC-SHA256 from the user's login password + salt, and stored in the database. Decrypted *only* on successful login. |
| **Auth tokens** | JWT containing the decrypted UEK as a claim, stored in sessionStorage (cleared on tab close). Sent on each API request, populating transient request-lifetime context. |
| **Per-user isolation** | All DB queries filter by `user_id` from JWT; decryption is provably isolated per user as it requires the user-specific UEK. |
| **CORS** | Restricted to known origins (`samkhya.cloud` + `localhost:3000`) |
| **HTTPS** | Enforced by Caddy auto-TLS / Let's Encrypt cert-manager |
| **Encryption key** | `CREDENTIAL_ENCRYPTION_KEY` is retained only as a fallback key for unmigrated legacy users. |
| **JWT secret** | `JWT_SECRET` must be changed per deployment |
| **API key in transit** | Never sent to frontend after save (only `has_key: true`) |
| **Token expiry** | Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` |
| **Rate limiting** | slowapi with per-IP limits: auth 10–20/min, providers 30–60/min, proxy 60/min, discussions 30–60/min, admin 30/min; Redis backend optional (in-memory fallback) |

### 6.1 Accepted Tradeoffs & Background Tasks

By design, user data (API keys, discussions, messages, and history) is completely protected under a mechanism derived solely from the user's active login credentials. Consequently, **background tasks, offline services, or automated jobs cannot decrypt or act on a user's secure data while that user is logged out.**
- If a background job or system action cannot unlock a user's data due to missing transient key context (UEK), it **must fail safe and skip that action gracefully** — it must never fall back to a weaker or shared server key.
- This limitation is accepted by design to maintain genuine, zero-knowledge, and direct-DB-proof privacy.

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

### 7.4 Detailed Query & Context Initiation Flow

The query context is dynamically built and augmented at each stage of the lifecycle to support multi-model, multi-round discussion, live web search capabilities, and precise formatting compliance.

```
                  ┌─────────────────────────────────┐
                  │      User Writes Question       │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │ Stage 1: Round 1 (Init Context) │
                  │  - Prepend activeDateStr        │
                  │  - Add Temporal Grounding /     │
                  │    Web-Search Mandates          │
                  │  - Add File Attachments         │
                  │  - Add System instructions      │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │ Stage 2: Rounds 2-N (Refine)    │
                  │  - safe-fetch previous responses│
                  │    via getRoundResponse()       │
                  │  - Append Chronological Log     │
                  │  - Add Round-Specific Directive │
                  └────────────────┬────────────────┘
                                   │
                ┌──┴──────────────────────────────┐
                ▼                                 ▼
   ┌──────────────────────────┐      ┌──────────────────────────┐
   │Stage 3: Consensus (Done) │      │Stage 4: Stopped/Manual   │
   │  - Aggregate responses   │      │  - Abort active tasks    │
   │  - Prepend Date Context  │      │  - Compile post-mortem   │
   │  - Inject Custom Summary │      │    chronological summary │
   │    Instructions or       │      │  - Append final token    │
   │    Format Template       │      │    usage statistics      │
   └──────────────────────────┘      └──────────────────────────┘
```

#### Detailed Stage Augmentations:

1. **Stage 1: Round 1 Initialization (No Prior Context)**
   * **Temporal Grounding Injection**: A dynamic system notice containing the current date (e.g. `Monday, July 6, 2026`) is prepended to the message:
     ```
     [SYSTEM NOTICE: Today's date is <activeDateStr>. Treat today as the absolute present moment for your temporal grounding. If you have search, browsing, or real-time web-access capabilities, you must actively perform live internet search queries to retrieve and incorporate the latest, up-to-the-minute information...]
     ```
   * **File Attachments Prepending**: Base64/text representations of all uploaded files are added directly:
     ```
     [Attached files: <name1>, <name2>]\n\n
     ```
   * **Custom System Instructions**: User-defined formatting rules (`instructions`) are appended to the first round:
     ```
     \n\n## Instructions / Response Format:\n<instructions>
     ```

2. **Stage 2: Rounds 2 to N (Refinement Phase)**
   * **Chronological Context Assembly**: To prevent context drift, preceding answers are combined into a standardized, unified format.
   * **Prefix-Insensitive Safe Retrieval**: Uses the self-healing `getRoundResponse(roundData, modelId)` helper to look up both legacy prefix-less database keys and normalized prefixed keys, completely resolving key mismatches.
   * **Round Log Generation**:
     ```
     # Original Question
     "<question>"

     ## Instructions
     <instructions>

     ## Round 1 Responses
     ### provider::model_name
     <response_text>
     ...
     ```
   * **Refinement Directive Append**:
     ```
     \n## Round <num> Instructions\nReview all previous responses above and provide your refined analysis building upon what has been discussed. Focus on areas where you can add value or offer a different perspective.
     ```

3. **Stage 3: Consensus Synthesis**
   * **Response Aggregation**: Gathers completed round answers from all models across all rounds using `getRoundResponse()`.
   * **Consensus Temporal Notice**:
     ```
     [System Notice: Today's date is <activeDateStr>. Please synthesize a balanced consensus from all perspectives as of today's date.]
     ```
   * **Custom Instructions & Template Injections**:
     * **If Custom Summary Instructions Specified**: Appends `\n\n## Custom Consensus Format Instructions:\n<instructions>`.
     * **Else (Default Templates)**:
       * **Compact**: Injects strict limits (1-sentence verdict, 40-point weighted score table, list of priority agreements, 3 priority recommendations).
       * **Elaborate**: Injects detail mandates (2-3 sentence verdict, alignment/friction matrix, deprioritized points log, full scoring tables).

4. **Stage 4: Stopped & Manually Closed Discussions**
   * **Instant Task Abort**: Inbound calls are canceled using `consensusAbortController.abort()`.
   * **Post-Mortem Summarization**:
     * Converts the partial query data instantly into a structured markdown overview.
     * Safely reads available responses using `getRoundResponse()`, falling back to `⏭ Skipped` or `*No response*` for incomplete tasks.
     * Appends aggregated performance and token consumption metrics (`stats`).

### 7.5 The Layman's Guide: Behind the Scenes of a Discussion

Imagine you are running a committee meeting with several expert advisors (the AI models), but instead of speaking, they communicate by writing and stacking notes. Here is exactly what happens from the moment you type a question to the final synthesis:

#### 📝 Phase 1: Passing the Initial Question (Round 1)
When you write your question and click start, the application acts as the meeting facilitator:
1. **The Clock Check**: Before handing your question to the experts, the facilitator slips a high-priority post-it note on top of it: *"Today is Monday, July 6, 2026. Do not guess; if you can look things up, search the live web for the latest info as of today."*
2. **The Document Handout**: If you uploaded files or documents, the facilitator translates them into text and staples them to your question.
3. **The First Call**: Each expert advisor reads this "starter package" independently and writes down their initial position statement on their own sheet of paper.

#### 🥞 Phase 2: Stacking and Passing Notes (Rounds 2 to N)
If you set the discussion to run for multiple rounds, the experts do not work in isolation anymore. They are forced to listen to each other:
1. **Gathering Notes**: At the end of Round 1, the facilitator collects all of the written sheets from every advisor.
2. **Stapling the Context Stack**: The facilitator staples all of these sheets together, right underneath your original question.
3. **Passing the Stack**: For Round 2, this entire stacked chronological booklet is handed to each expert.
4. **The Refinement Mandate**: The facilitator adds a header directive on top of the booklet: *"Read what your peers wrote in the previous round, refine your thoughts, and write a follow-up sheet that builds constructively upon the group discussion."*
5. **Repeating**: This process repeats for subsequent rounds, stacking new sheets on top of old sheets, creating a rich collaborative dialogue.

#### 🎓 Phase 3: Reaching the Consensus (The Synthesizer)
Once all rounds of discussion are complete, the facilitator gathers the entire booklet of stacked notes and hands it over to your designated **Consensus Model** (the Editor-in-Chief):
1. **The Editor's Task**: The Editor is given a synthesis directive along with the current date: *"Review this entire collaborative transcript, extract where the experts agree, highlight where they disagree, and write a balanced summary."*
2. **Formatting**:
   * If you typed **Custom Summary Instructions** into the box, the Editor follows your custom guidelines.
   * Otherwise, the Editor formats the output using your selected template:
     * **Compact**: A quick, 1-sentence verdict, a weighted points table, and 3 bulleted recommendations.
     * **Elaborate**: A deeply detailed executive overview, alignment-versus-friction matrices, and a comprehensive breakdown.

#### 🛑 What If You Click "Stop"? (The "Pencils Down" Guard)
If you decide to interrupt or end the discussion early:
1. **Pencils Down**: The facilitator instantly calls out *"Pencils down!"* and cancels all active connections, stopping any slow-running APIs.
2. **Salvaging the Notes**: Instead of binning the work, the facilitator neatly organizes whatever response sheets were already completed up to that second.
3. **The Briefing**: It bundles those completed sheets into a partial transcript, adds a `⏭ Skipped` badge for pending ones, tallies up the "words" (tokens) used so far, and shows you the partial results.

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

### ⚠️ Mandatory Rule: ARCHITECTURE.md Is the Source of Truth

**Every AI coding agent, LLM, or developer working on this project MUST:**

1. **Read this entire document first** before making any changes.
2. **Follow all architectural decisions, conventions, security rules, and data flow patterns** defined here — never deviate without explicit discussion.
3. **Update this document as part of every code change** — if you modify code behavior, add features, change deployment, or alter security boundaries, update the relevant section(s) in this file.
4. **Bump the version** in the header (see [Versioning & Changelog](#11-versioning--changelog)) for every meaningful change.
5. **Tag the git commit** with the new version after committing.

This file is co-authored by the entire development lifecycle — human and AI alike. Treat it as the single source of authority. When in doubt, the answer is here.

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
# Build backend image and push to GHCR
docker build -t ghcr.io/prashshr/ai-ensemble:latest ./backend
docker push ghcr.io/prashshr/ai-ensemble:latest

# Deploy
cd deploy/k8s
kubectl create ns ai-ensemble --dry-run=client -o yaml | kubectl apply -f -
bash create-secret.sh
kubectl apply -f configmap.yaml
kubectl apply -f searxng-settings-configmap.yaml
kubectl apply -f searxng-deployment.yaml
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
- [x] Rate limiting (slowapi, per-IP, all routes)
- [ ] Audit logging (not implemented)
- [ ] CSP headers (partial — Caddy adds HSTS etc.)
- [ ] Input sanitization (not implemented)
- [ ] Regular DB backups (not configured)
- [ ] Resource monitoring (not configured)
- [ ] CI/CD pipeline (not configured)

---

## 11. Versioning & Changelog

Version format: `v<major>.<minor>.<patch>-<YYYYMMDD>` (e.g., `v0.1.0-20260625`)

### v0.6.0 (2026-07-08)

- **Security: Password-Derived Master Encryption Key (UEK)** — Replaced the shared server-wide key (`CREDENTIAL_ENCRYPTION_KEY`) for encrypting provider credentials, discussions, message content, and search histories with a secure user-specific encryption key (UEK) derived from each user's login credentials.
- **Security: Complete Zero-Knowledge DB Storage** — Encrypted all user-specific sensitive data: provider API keys, discussion titles, discussion questions, discussion state JSON, message contents, and search queries using the user's master key (`uek`).
- **Security: Safe Revocation & Transient UEK Session Lifetime** — Configured user-specific UEK decryption to occur solely upon active login. The decrypted UEK is embedded as an extra claim inside the JWT and is held strictly in transient request lifecycles, ensuring logout/browser tab closure completely revokes access to the data with zero cookie or local storage footprint.
- **Security: Invisible Auto-Migration & Graceful Background Handling** — Enabled seamless, gradual data transition where legacy users' plaintext history and legacy keys are automatically and silently re-encrypted using their newly derived master key on their next successful login. Integrated graceful handling of missing master keys so that any background tasks or unauthorized admin pathways fail/skip gracefully without silent fallback to weaker modes.

### v0.7.0 (2026-07-09)

- **Feature: 3-Tier RAG (Web Search) Pipeline** — Implemented a comprehensive RAG system with three search tiers: Tavily API (primary, purpose-built for AI), self-hosted SearXNG (secondary, deployed in-cluster), and DuckDuckGo HTML (tertiary fallback). Each tier falls through gracefully on failure.
- **Feature: Tavily Web Search Integration** — Added Tavily API as the primary search engine, returning up to 10 rich results with content per query. Configured via `TAVILY_API_KEY` environment variable. Free tier: 1,000 queries/month.
- **Feature: Self-hosted SearXNG** — Deployed SearXNG as a pod in the K3s cluster (searxng/searxng:latest), configured with JSON API enabled, rate limiting disabled, and custom settings.yml via ConfigMap. Accessible internally at `http://searxng-svc:8080`.
- **Feature: RAG Context Injection in Proxy Chat** — Added `discussion_id` and `include_rag_context` fields to `ChatRequest`. When enabled, the proxy endpoint fetches the discussion's encrypted RAG context, decrypts it, and prepends it to the LLM prompt as supplementary context — models remain free to use their own training data and capabilities.
- **Feature: UI RAG Status Indicator** — Added a green/red dot indicator next to the question display showing whether RAG context was retrieved and how many KB of context is available.
- **Infrastructure: GHCR Image Publishing** — Docker images are now built, tagged, and pushed to `ghcr.io/prashshr/ai-ensemble:latest` with `imagePullPolicy: Always`. Added `ghcr-pull-secret` for GHCR authentication in K3s.
- **Infrastructure: Database Schema Migration** — Added `retrieved_context_encrypted` TEXT column to the `discussions` table for storing encrypted RAG context.
- **Debugging: RAG Pipeline Logging** — Added comprehensive debug logging to the `ai_ensemble.rag` logger at INFO/DEBUG level, with clear `[RAG]` prefix on all pipeline steps. Logs show which search engine fired, how many results, extraction progress, and final context size.
- **Improvement: Async-safe Content Extraction** — Wrapped `trafilatura.fetch_url` and `trafilatura.extract` in `asyncio.to_thread()` to prevent event loop blocking during HTML content extraction.

### v0.5.5 (2026-07-07)

- **Documentation: The Layman's Guide to AI Ensemble** — Integrated a highly comprehensive and engaging "Layman's Guide: Behind the Scenes of a Discussion" under Section 7.5 to explain multi-round context building, information stacking, and consensus synthesis using a simple "Committee Meeting" analogy.
- **Documentation: Chronological Query & Context Flow** — Detailed the step-by-step query construction, temporal grounding (calendar context injection), and prompt templates for all discussion stages (Stage 1 to 4) under Section 7.4.
- **Backend/Frontend: Historical Discussion Restoration Fixes** — Resolved a critical UI issue where legacy, prefix-less database keys (`modelId`) failed to match modern composite keys (`provider::modelId`), implementing prefix-insensitive safe retrieval (`getRoundResponse()`) to successfully restore complete round details for historical discussions.
- **Frontend: Health Check Execution Control** — Corrected provider selection behaviors to render the loading/refresh icon and initiate background model health checks *only* upon explicit saving or manual refresh triggers, optimizing client-side performance and rate compliance.

### v0.5.4 (2026-07-06)

- **Infrastructure: Ingress Cleanup & Traefik Restoration** — Purged invalid Traefik timeout annotations from `/deploy/k8s/ingress.yaml` which were unrecognized by the ingress provider, instantly restoring full ingress routing and resolving the 404 Page Not Found block.
- **Backend: Patient HTTPX Timeout Tuning** — Kept the increased client-side HTTPX timeouts (120s/150s) on the backend as the primary and highly stable remedy, ensuring the proxy waits gracefully for deep multi-agent reasoning tasks while Traefik handles streaming/long-polling with no default timeout limits.

### v0.5.3 (2026-07-06)

- **Infrastructure: Traefik Ingress Timeout Expansion** — Configured Ingress annotations `traefik.ingress.kubernetes.io/router.timeout: 180s` and `traefik.ingress.kubernetes.io/service.response-timeout: 180s` on `/arbeit/ai-welt/projects/ai-ensemble/deploy/k8s/ingress.yaml` to ensure the gateway connection remains open for complex multi-agent queries.
- **Backend: Patient Client Timeout Scaling** — Upgraded HTTPX client timeouts in all backend provider clients (`perplexity.py`, `anthropic.py`, `gemini.py`, `openai_compatible.py`, and `vertex.py`) from 60 seconds to 120/150 seconds to gracefully wait for web search and deep-reasoning completions, completely resolving Cloudflare/Traefik 502 prematurely closed connection blocks.

### v0.5.2 (2026-07-06)

- **Backend: Perplexity Agent API Payload Schema Correction** — Resolved a critical schema incompatibility where Perplexity's `/v1/agent` path expects `"input"` and `"max_output_tokens"` rather than OpenAI's standard `"messages"` array. Rewrote backend request generation to construct the correct schema for Agent API models, and implemented a custom response tree traversal to successfully parse the nested output text array blocks (e.g., `data["output"][0]["content"][X]["text"]`), completely fixing 502/400 Bad Request errors.
- **UI: Dynamic "Reset Provider" Button** — Added a dedicated, red-tinted **"🗑️ Reset Provider"** action button in the Step 1 Setup Configuration panel. Clicking this triggers a secure `DELETE /api/providers/{provider}` backend request, clearing credentials, wiping input fields, resetting local state, and converting the provider card status back to `gray-dot` in real-time.

### v0.5.1 (2026-07-06)

- **Backend: Perplexity Agent API vs Sonar Dual-Route Engine** — Refactored the custom `PerplexityClient` to dynamically detect and segment model queries. Standard native Sonar models are routed to `/chat/completions`, while newly supported third-party models under Perplexity's Agent API (e.g. `google/gemini-3.5-flash`, `openai/gpt-5.5`, and `anthropic/claude-sonnet-5` that contain a `/` namespace) are routed to the specialized `/v1/agent` path, completely resolving Cloudflare 502/404 routing blocks for external models.
- **Backend: Dynamic Model Unioning for Perplexity** — Upgraded `PerplexityClient.list_models` to attempt to dynamically poll available models via `GET /v1/models` and merge them with standard Sonar models, guaranteeing access to the most up-to-date and comprehensive model list.

### v0.5.0 (2026-07-05)

- **Backend: Custom Perplexity AI Client** — Developed a dedicated `PerplexityClient` that bypasses standard `/models` listing constraints by automatically serving a curated list of active Perplexity models (`sonar`, `sonar-pro`, `sonar-reasoning`, etc.) and enforcing chat routing directly to the `/chat/completions` endpoint for reliable factual search querying.
- **Backend: Custom Google Vertex AI Client** — Built a dedicated `VertexClient` that allows enterprise GCP Gemini API usage, accepting standard authorization tokens/bearer keys and dynamically structuring queries to the location-specific GCP publisher API path.
- **Frontend: Project & Region Selectors for Google Vertex** — Configured the Add Provider modal to dynamically render **Google Cloud Project ID** and **GCP Region** text fields when Vertex is selected, auto-computing the full publisher-specific endpoint URL in real time.
- **UI: Neutral Discussion Summary Box** — Segregated manual stop-and-summarize results out of the vibrant colored consensus box into an independent, neutral/uncolored container (`#discussionSummarySection`) with neutral borders and no box-shadows, leaving the colored consensus card reserved exclusively for successful automated multi-model syntheses.
- **Feature: Dynamic Multi-Provider Routing** — Re-engineered `selectedModels` to utilize unique composite keys (`provider::modelId`), decoupling the model state from the active global provider. Each individual model query is dynamically dispatched to its native provider credentials and endpoint, preventing routing errors like Perplexity trying to serve OpenRouter/OpenAI models.
- **UI: Redesigned Step-by-Step Linear Setup Flow** — Permanently retired the complex Left Sidebar panel. Restructured the entire Setup Workspace into a clean, intuitive, top-to-bottom vertical progression wizard: **Step 1** (Select Provider from a beautiful interactive grid with active/inactive status indicator dots, accompanied by collapsible configuration inputs to edit or add a provider), **Step 2** (Select Models checklist, displayed exclusively only after its active provider has been successfully configured and discovered), and **Step 3** (Write question, select settings, and start debate), maximizing centered screen spacing on both desktop and mobile layouts.
- **UI: Dedicated Active Ensemble (Selected Models) Step Card** — Segregated the selected cross-provider models list entirely out of the expandable checklist panel, elevating it to an independent, standalone card (Step 2.5: Active Ensemble). This section dynamically displays as soon as at least one model is selected, showing each chosen model clearly labeled with its specific **Provider Name** and **Model Name** (e.g. `[OPENROUTER · gemini-2.5-pro]`, `[PERPLEXITY · sonar-reasoning]`) with click-to-remove capability.
- **Frontend: Dual Options to Save Permanent Providers** — Implemented two methods for users to persist provider credentials: a premium "+ Add Provider" modal for setup selection and a direct "💾 Save Provider" action button inside the collapsible Setup "API Configuration" panel.

### v0.4.0 (2026-07-05)

- **Feature: Independent Centered Login Page** — Replaced the unaligned overlays and duplicate embedded tabs with a perfectly centered fullscreen login card (`#loginPage`) with robust fixed positioning and shadows.
- **Improvement: Top Header Session Panel** — Standardized a top-right account block displaying the active username and an elegant `Logout` button directly next to the theme toggle.
- **UI Polish: Dynamic Full-Width Sidebar Collapse** — Programmed tab navigation to append `.full-width` to the main layout on non-setup tabs (*History* and *Current Discussion*), automatically hiding the Providers/Models sidebar columns when they aren't needed to maximize screen spacing.
- **UI Polish: Participating Models Row** — Added a responsive row of elegant pill badges displaying all selected models at the top of active or loaded discussions, directly above the round timeline.
- **UI Polish: Collapsible Discovered Models Grid** — Wrapped the massive 75-model selection block in a beautifully styled collapsible accordion card (`#modelSelection`) with a clean interactive header toggle, allowing users to instantly fold/collapse the grid to reclaim vertical screen space.
- **UI Polish: Collapsible Discovered Models Grid** — Wrapped the massive 75-model selection block in a beautifully styled collapsible accordion card (`#modelSelection`) with a clean interactive header toggle, allowing users to instantly fold/collapse the grid to reclaim vertical screen space.
- **UI Polish: Click-to-Expand Response Cards** — Configured response cards inside the debate timeline to toggle `.expanded` on click, expanding cards across the full grid row (`grid-column: 1 / -1 !important`) and setting response heights to full height (`max-height: none !important`), completely eliminating internal scrolling and text truncation while keeping default grid alignment on collapse.
- **UX: Home Navigation Trigger** — Implemented a prominent **"Start New Discussion"** (home button) at the bottom of completed debates that clears state, resets forms, and routes users smoothly back to the setup workspace.
- **UX: Strictly Dark/Light Themes** — Restricted theme cycling and options strictly to standard **Dark Mode** (vibrant orange accent) and **Light Mode** for a unified design experience.
- **UI: Simplified Icon-Only Theme Toggle** — Removed the text labels from the theme toggle button, replacing it with a clean, circular icon button displaying strictly the sun (`☀️`) or moon (`🌙`) symbol for an ultra-premium, minimalist look.
- **UI: Symmetrical Tri-Column Header Layout** — Restructured the header layer into a fully symmetrical, three-column layout: Username and Logout on the far-left corner, the "AI - Ensemble" branding enlarged and centered (clicking triggers a return to the main dashboard/home screen), and the minimalist theme toggle on the far-right corner.
- **UI: Ultra-Sleek Header Status Bar** — Replaced the bulky bordered user display block with an elegant, borderless inline text string showing strictly the plain username (automatically stripping the internal `@local.ai-ensemble` domain suffix), separated from an elegant link-style hoverable **Logout** button by a clean vertical divider line.
- **Logic Fix: Round 1 Prompt Format Passing** — Resolved a critical core bug where custom instructions and Response Format selections were omitted from prompts sent in Round 1 (now perfectly appended to model prompts in Round 1 as well as Round 2+ context blocks).
- **Bug Fix: Round-Specific Card Actions** — Standardized DOM action panel selectors with unique round suffixes (`actions-${safeId}-R${roundNum}`). This completely resolves duplicate HTML IDs across rounds that previously broke card action bars (Expand/Full Screen) on any round after Round 1.
- **UI: Restored Card Actions in History** — Enabled completed cards loaded from historical sessions or completed states to render and execute active **Expand** and **Full Screen** action bars across all rounds.
- **Logic: Live Daily Calendar Date Context** — Configured the active browser-computed date (e.g. `Sunday, July 5, 2026` in Europe/Berlin timezone) to be prepended as a compulsory system-level context notice to all individual model queries and final consensus prompts, prompting models to leverage current real-world search/data parameters as of today.
- **UI: Consolidated Consensus Panel** — Completely purged a dead, duplicate `#summaryPanel` ("Summary") from the DOM structure, leaving exactly one single, active, live synthesis container: the premium, robust **"Ensemble Consensus"** block containing the full weighted scoring card, agreement timelines, and export tools.
- **Feature: Dynamic Stored Providers System** — Integrated a multi-provider state engine that fetches saved user credentials from the backend database on page load and renders active platforms dynamically in the Left Sidebar with color-coded connectivity dots (Green for configured, Gray for inactive), allowing instant model discovery on click with **zero key re-entry required**.
- **Improvement: Native Prefilled Platforms & Web Auth Redirects** — Refactored the "+ Add Provider" action into an interactive modal supporting native prefilled configurations for **OpenRouter, OpenAI, Perplexity, Google Vertex, Mammouth AI, and Requesty AI**, automatically prefilling endpoints and displaying direct secure redirection links so users can log in via their official webpage redirected authentication, instantly copy their generated key, and paste it back securely.
- **Security Clarification:** Updated front-end messaging to correctly emphasize that all API keys and custom configurations are saved securely and encrypted on the backend database (no keys are stored in the browser's local cache).
- **Deployment: HTTPS-Only Traefik Enforcement** — Modified the Kubernetes Ingress resource to enforce the Traefik `websecure` entrypoint, routing all user traffic strictly via secure SSL/TLS.
- **Deployment Refactoring:** Cleaned up manual ConfigMap overrides and restored native HostPath volume mounts so Nginx serves the direct web source from the filesystem.

### v0.3.0 (2026-06-30)

- **Bug Fix: Login/Register buttons non-functional** — Duplicate `let selectedModels` declaration in the multi-provider override block caused a `SyntaxError` that killed the entire `<script>` element; all `onclick` handlers (`overlayLogin`, `overlayRegister`) were undefined. Consolidated all multi-provider state variables and constants to the top of the script; removed the entire override block.
- **Bug Fix: `currentRound_num` vs `currentRoundNum` inconsistency** — `proceedToNextRound`, `showRoundStatus`, and `resumeDiscussion` used `currentRound_num` while the rest of the code used `currentRoundNum`; standardized on `currentRoundNum`.
- **Bug Fix: SQLite schema drift** — `init_db()` now attempts `ALTER TABLE discussions ADD COLUMN state_json TEXT DEFAULT ''` with rollback on success, fixing existing databases missing the column.
- **Bug Fix: Composite ID consistency in `queryModel()`** — Card `data-model`, action element IDs, `discussionData.rounds` keys, and timing keys now all use the composite `provider::modelId` format consistently.
- **Improvement: Response card provider attribution** — `renderRound()` now shows `ProviderName · ModelName` in card headers for restored discussions (was showing only the model ID).
- **UI Polish: Provider panel collapse** — Replaced abrupt `display` toggle with CSS width/padding/opacity transition via `.collapsed` class.
- **UI Polish: Password requirements** — Hidden by default; shown only on password field focus via `showPasswordReqs()`.
- **UI Polish: Add Provider cancel** — Wired via `.btn-add-provider` class selector instead of fragile `previousElementSibling`.
- **UI Polish: Provider card overflow** — Added `min-width: 0`, `text-overflow: ellipsis`, and `.provider-model-list` containment for long hostnames/model names.
- **Feature: Rate limiting** — slowapi 0.1.9 with per-IP limits across all routes (auth 10–20/min, providers 30–60/min, proxy 60/min, discussions 30–60/min, admin 30/min); shared `Limiter` instance in `app/core/limiter.py` to avoid circular imports; Redis backend optional.
- **Improvement: Error boundaries** — `queryModel()` and `generateConsensus()` now wrap JSON parsing in `try/catch` with meaningful error messages instead of raw exceptions.
- **Architecture: Multi-provider state consolidation** — `PROVIDER_DISPLAY_NAMES`, `PROVIDER_DEFAULTS`, `configuredProviders`, `providerModelCache`, `modelToProvider`, `providerPanelOpen`, `providerPanelPinned`, `panelResizing` all declared once at the top of the script; duplicate function definitions (`discoverModels`, `loadUserProviderConfig`) removed.

### v0.2.3 (2026-06-26)

- **Bug Fix: Perplexity/OpenAI-compat proxy 500 errors** — Backend proxy now catches `httpx.HTTPStatusError` and `RequestError` to return meaningful error responses; auto-retries without `/v1` suffix on 404 for providers like Perplexity
- **Feature: Endpoint normalization** — New `backend/app/services/providers/endpoints.py` with canonical endpoint mapping for major providers (OpenAI, OpenRouter, Perplexity, Groq, Together, Mistral, DeepSeek, xAI, Fireworks, Cohere); endpoint auto-normalized on both save and proxy routes
- **Bug Fix: "body stream already read"** — Frontend error handler now reads `response.text()` once and parses JSON with `JSON.parse()` instead of calling `response.json()` then falling back to `response.text()`
- **Feature: Admin user endpoints** — New `GET /api/admin/users` and `DELETE /api/admin/users/{id}` for user management
- **UI Redesign: Login overlay** — Separated "Sign In" and "Create New Account" with clear sections; password complexity rules displayed
- **Improvement: Provider discussion field** — Added discussion section ID input on provider config for multi-turn conversations
- **Build: Docker images pushed to GHCR** — `ghcr.io/prashshr/ai-ensemble-backend:latest` and `:v0.2.3`
- **Deployment: k8s rollout** — Backend and web deployments updated and rolled out successfully

### v0.2.2 (2026-06-25)

- **Bug Fix: Login persistence** — `setAuth()` no longer resets `queryHistory` on login; calls `loadUserDiscussions()` to fetch backend discussions
- **Bug Fix: Provider credential retention** — `loadUserProviderConfig()` now auto-discovers models on login if endpoint + key exist (silent mode)
- **Bug Fix: History not saved to DB** — Added `loadUserDiscussions()`, `saveDiscussionToBackend()`, `createDiscussionOnBackend()`; `saveState()` now persists to both localStorage and backend
- **Feature: User management** — New `GET /api/admin/users` and `DELETE /api/admin/users/{id}` endpoints; admin tab in frontend with user table + delete capability
- **Bug Fix: Cross-user data isolation** — `availableModels`, `storedEndpoint`, `storedApiKey` now cleared on user switch; localStorage keys (`councilHistory`, `councilState`) scoped per-user via `getHistoryKey()`/`getStateKey()`
- **Improvement: User visibility** — Added `👤 user@email` badge below theme toggle showing logged-in user
- **UI Polish: Theme toggle** — Shows only ☀️/🌙 symbols (no text); added `title` tooltip
- **UI Polish: Header layout** — Theme toggle moved to top-left, logout stays top-right; added `padding-top` to prevent overlap with heading
- **Database reset** — Fresh SQLite database (all users start clean)
- Backend: `state_json` column on Discussion model; `DiscussionUpdateRequest` schema; full discussion CRUD (PUT, GET by ID, DELETE)

### v0.2.1 (2026-06-25)

- Strengthened "Source of Truth" mandate: explicit instruction that every AI agent/developer must read ARCHITECTURE.md first and update it with every change
- Removed inline auth panel from setup tab (login now exclusively via full-screen overlay)
- Added persistent logout button in header area for switching users
- Removed default credential hint from login overlay
- Updated footer text to "Built for discussions with multiple AI models."

### v0.2.0 (2026-06-25)

- Full-screen login overlay with auth gate (blocks app access until authenticated)
- Login overlay supports Enter key submission
- Default admin auto-seeded: `admin@local.ai-ensemble` / `arhatadmin`
- Error/info display within overlay modal
- Architecture document updated to v0.2.0

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