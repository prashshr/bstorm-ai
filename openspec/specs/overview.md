# Specification: High-Level System Overview

# Purpose
AI-Ensemble is an enterprise-grade multi-provider AI discussion and consensus platform. It allows users to prompt multiple Large Language Models (LLMs) simultaneously, observe their parallel streaming responses, and synthesize an automated consensus summary across model outputs. The platform guarantees user data privacy through zero-knowledge envelope encryption and integrates an automated Retrieval-Augmented Generation (RAG) pipeline for real-time web search.

# Responsibilities
- Provide a unified web and mobile interface for multi-model AI interactions.
- Orchestrate parallel, staggered SSE streaming requests to diverse AI providers (OpenAI, Anthropic, Gemini, Vertex AI, Perplexity, DeepSeek, Groq, Ollama, Requesty, Mammouth).
- Perform zero-knowledge envelope encryption (AES-256-Fernet + PBKDF2) for prompts, responses, provider credentials, and search history at rest.
- Execute real-time web context retrieval (Tavily, SearXNG, DuckDuckGo) with automated domain classification.
- Support cross-platform native execution on Android devices via Capacitor 8.

# Architecture
AI-Ensemble is structured as a client-server web and native app architecture:
- **Frontend Layer**: Svelte 5 + Vite reactive single-page application (SPA) with class-based Svelte Runes stores.
- **Backend Layer**: Asynchronous FastAPI (Python 3.12) REST & SSE web API server.
- **Data Layer**: Relational database (SQLite/PostgreSQL) managed by SQLAlchemy 2.0 ORM and Alembic migrations.
- **Provider Subsystem**: Extensible client factory normalizing diverse upstream provider REST/SSE contracts.
- **Native Wrapper**: Capacitor 8 Android wrapper featuring native secure storage and hardware insets integration.

# Data Flow
```
User Prompt -> Svelte 5 Store -> API Client (fetch/SSE) -> FastAPI Router 
  -> JWT & UEK Auth -> Encrypted DB Lookup -> Upstream AI Provider (SSE) 
  -> Client Stream Reader -> Svelte 5 Reactive UI -> Encrypted DB Persistence
```

# Internal Components
- `AppContainer.svelte`: Main UI shell orchestrating top header, collapsible sessions sidebar, main content area, and provider drawer.
- `discussion.svelte.ts`: Svelte 5 Runes store managing ensemble execution, SSE consumption, and consensus state.
- `FastAPI App (main.py)`: Central API entrypoint, rate limiter, CORS middleware, and lifecycle manager.
- `crypto.py`: Envelope encryption engine deriving User Encryption Keys (UEK) and managing Fernet cipher instances.
- `retrieval.py`: Multi-engine asynchronous web search aggregator and Trafilatura article extractor.

# Public Interfaces
- Web Frontend UI: Hosted at `https://ai-ensemble.samkhya.cloud`.
- REST API: Endpoints prefix `/api/v1` and `/api` (Auth, Providers, Discussions, Folders, Proxy, Admin).
- Android Native Application: Package `cloud.aiensemble.app`.

# Dependencies
- **Internal**: `backend/app/`, `frontend/src/`, `deploy/k8s/`, `testing/`.
- **External**: Upstream AI APIs (OpenAI, Anthropic, Google AI Studio, Vertex AI, Perplexity, Tavily).
- **Third-party Libraries**: Svelte 5, Vite, FastAPI, SQLAlchemy, Alembic, Cryptography (Fernet), Trafilatura, Capacitor 8.

# Configuration
- Environment File: `.env` (managed via Pydantic `BaseSettings` in `config.py`).
- Essential Variables: `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `DATABASE_URL`, `TAVILY_API_KEY`, `SEARXNG_URL`.

# Current Behaviour
The application is fully operational in production on Kubernetes (k3s). Users log in, select active AI models, enter prompts in a bottom-docked composer, and view side-by-side model answers with automated consensus summaries.

# Constraints
- Zero-knowledge design requires user plaintext password during login/registration to derive the UEK.
- Maximum concurrent model streams per client turn is capped at 3 with 500ms stagger delay to prevent rate limit spikes.

# Future Considerations
- Support for local WebGPU model inference directly inside the browser.
- Enterprise SSO (SAML/OIDC) integration alongside UEK encryption.

# Related Specs
- [Architecture Spec](architecture.md)
- [Frontend Spec](frontend.md)
- [Backend Spec](backend.md)
- [Android Spec](android.md)
