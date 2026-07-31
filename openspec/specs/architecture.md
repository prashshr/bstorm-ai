# Specification: End-to-End System Architecture

# Purpose
This document specifies the end-to-end technical architecture, component topologies, runtime execution flows, data models, and security boundaries of AI-Ensemble.

# Responsibilities
- Define component relationships between Web/Android clients, FastAPI backend, databases, and AI providers.
- Document request lifecycles for authentication, proxy chat streaming, RAG enrichment, and consensus generation.
- Specify zero-knowledge envelope encryption protocols and key management workflows.
- Detail deployment topologies across Docker Compose and Kubernetes (k3s).

# Architecture

```mermaid
graph TD
    subgraph Clients ["Client Applications"]
        Web[Svelte 5 Web SPA]
        Android[Capacitor 8 Android App]
    end

    subgraph Network ["Ingress / Reverse Proxy"]
        Traefik[Traefik Ingress / Nginx]
    end

    subgraph Backend ["FastAPI Backend (Python 3.12)"]
        Router[APIRouter Aggregator]
        AuthCore[Auth & Crypto Core - Fernet]
        RAGCore[RAG Pipeline & Classifier]
        ProviderFactory[Provider Client Factory]
    end

    subgraph Data ["Data Persistence"]
        DB[(SQLite / PostgreSQL)]
        SessionStore[(Mobile UEK Session Store)]
    end

    subgraph External ["External AI Providers & Search"]
        OpenAI[OpenAI / OpenRouter]
        Anthropic[Anthropic Claude]
        Gemini[Google Gemini / Vertex AI]
        Perplexity[Perplexity Sonar]
        Tavily[Tavily Search API]
        SearXNG[Self-hosted SearXNG]
    end

    Web & Android -->|HTTPS / SSE| Traefik
    Traefik -->|Proxy /api/*| Router
    Router --> AuthCore
    Router --> RAGCore
    Router --> ProviderFactory
    AuthCore --> DB & SessionStore
    RAGCore --> Tavily & SearXNG
    ProviderFactory --> OpenAI & Anthropic & Gemini & Perplexity
```

# Data Flow

### AI Chat Request & SSE Streaming Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Svelte 5 Chat UI
    participant API as FastAPI Proxy (/api/proxy/chat/stream)
    participant Auth as Crypto Core (crypto.py)
    participant RAG as RAG Pipeline (retrieval.py)
    participant Factory as Provider Factory
    participant AI as Upstream Provider API

    User->>UI: Enter prompt & click Send
    UI->>API: POST /api/proxy/chat/stream (JWT + Encrypted payload)
    API->>Auth: Validate JWT & Decrypt User Key (UEK)
    API->>Auth: Decrypt Provider Credentials
    
    opt RAG Mode Enabled
        API->>RAG: Execute Web Search (Tavily / SearXNG)
        RAG-->>API: Extracted & Sanitized Web Context
    end

    API->>Factory: Get ProviderClient instance
    API->>AI: Outbound HTTPS SSE / REST Request
    
    loop Streaming Deltas
        AI-->>API: SSE Stream Chunk
        API-->>UI: Transmit SSE Event (data: {"type": "delta", "content": "..."})
        UI-->>User: Update Model Card in Real-Time
    end

    API-->>UI: Transmit SSE Done (data: {"type": "done", "content": "..."})
    API->>Auth: Encrypt Prompt & Model Answers with UEK
    API->>DB: Persist Discussion Turn
```

# Internal Components
- **FastAPI Core (`backend/app/main.py`)**: Web application instance, CORS middleware, exception handlers, and rate limiters.
- **Crypto Engine (`backend/app/core/crypto.py`)**: PBKDF2 key derivation (600K iterations) and AES-256-Fernet cipher management.
- **Session Store (`backend/app/core/sessions.py`)**: In-memory and DB-backed mapping of mobile session IDs (`sid`) to decrypted UEKs.
- **Provider Clients (`backend/app/services/providers/`)**: Concrete implementations for OpenAI, Anthropic, Gemini, Vertex, and Perplexity.
- **Svelte Store (`frontend/src/lib/stores/discussion.svelte.ts`)**: Class-based reactive state store managing turn rounds, SSE events, and model selections.

# Public Interfaces
- REST API Base: `/api`
- Key Routes: `/api/auth/*`, `/api/providers/*`, `/api/discussions/*`, `/api/folders/*`, `/api/proxy/*`, `/api/admin/*`.

# Dependencies
- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, Cryptography (Fernet), Trafilatura.
- Node.js 22, Svelte 5, Vite 6, TypeScript 5, Capacitor 8.

# Configuration
- Managed via `backend/app/core/config.py` using `pydantic-settings`.
- Required settings: `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`.

# Current Behaviour
The backend runs asynchronously under Uvicorn. Upon receiving a chat request, credentials and prompts are decrypted on the fly using the user's UEK, forwarded to the upstream LLM via SSE streams, and re-encrypted before being committed to the database.

# Constraints
- High-concurrency SSE streaming requires asynchronous HTTP clients (`httpx`).
- Network requests to upstream providers are subject to user-configured timeouts (default 120s).

# Future Considerations
- Horizontal scaling with distributed Redis session stores and WebSockets for bi-directional streaming.

# Related Specs
- [Overview Spec](overview.md)
- [Backend Spec](backend.md)
- [Frontend Spec](frontend.md)
- [Security Spec](security.md)
