# Specification: AI Provider Credentials & Management

# Purpose
The Providers subsystem specifies how AI-Ensemble manages provider configurations, user-supplied API keys, custom endpoint overrides, labels, GCP project/region settings, ADC service account credentials, and connection testing.

# Responsibilities
- Store per-user encrypted provider credentials (`ProviderCredential` ORM model).
- Normalize raw provider key names and custom endpoint URLs via `endpoints.py`.
- Execute connection testing (`POST /api/providers/{key}/test`) without risking session invalidation.
- Support GCP Vertex AI Application Default Credentials (ADC) with user-level ADC JSON key overrides.
- Provide pre-configured provider presets (OpenRouter, OpenAI, Anthropic, Gemini, Vertex AI, Perplexity, DeepSeek, Groq, Ollama, Requesty, Mammouth).

# Architecture

```mermaid
graph TD
    UserUI[ProviderForm.svelte / ProviderPanel.svelte] -->|POST /api/providers| API[FastAPI Provider Route]
    API --> Crypto[crypto.py - Encrypt Key with UEK]
    Crypto --> DB[(ProviderCredential ORM Model)]

    UserUI -->|POST /api/providers/{key}/test| TestAPI[Test Route]
    TestAPI --> Factory[services/providers/factory.py]
    Factory --> Client[ProviderClient Instance]
    Client -->|List Models / Ping| ProviderAPI[Upstream Provider Endpoint]
```

# Supported Provider Presets (`PROVIDER_PRESETS`)

| Key | Display Label | Default Endpoint | Key Format / Requirement |
| :--- | :--- | :--- | :--- |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `sk-or-v1-...` |
| `openai` | OpenAI | `https://api.openai.com/v1` | `sk-...` |
| `anthropic` | Anthropic | `https://api.anthropic.com/v1` | `sk-ant-...` |
| `gemini` | Google Gemini | `https://generativelanguage.googleapis.com` | Google AI Studio API Key |
| `vertex` | GCP Vertex AI | GCP Regional Endpoint | GCP Project ID, Region, ADC JSON |
| `perplexity` | Perplexity | `https://api.perplexity.ai` | `pplx-...` |
| `deepseek` | DeepSeek | `https://api.deepseek.com/v1` | `sk-...` |
| `groq` | Groq | `https://api.groq.com/openai/v1` | `gsk_...` |
| `ollama` | Ollama (Local) | `http://localhost:11434/v1` | Key optional |

# Data Flow
1. User enters provider details in `ProviderForm.svelte`.
2. `api.upsertProvider()` posts payload to `POST /api/providers`.
3. Backend encrypts `api_key` and `adc_json` using the user's User Encryption Key (UEK) and saves the record in `provider_credentials` table.
4. Calling `testProvider()` instantiates `ProviderClient` and executes `list_models()`.

# Internal Components
- `app/api/routes/providers.py`: Provider CRUD and test endpoints.
- `app/models/models.py`: `ProviderCredential` SQLAlchemy model (`api_key_encrypted`, `adc_json_encrypted`).
- `app/services/providers/endpoints.py`: URL canonicalization rules (`normalize_endpoint_url()`).

# Public Interfaces
- REST Endpoints:
  - `GET /api/providers`
  - `POST /api/providers`
  - `DELETE /api/providers/{provider_key}`
  - `GET /api/providers/{provider_key}/models`
  - `POST /api/providers/{provider_key}/test`

# Dependencies
- `sqlalchemy`, `cryptography` (Fernet), `httpx`, `google-auth`.

# Configuration
- Endpoint Normalization Map: `PROVIDER_ENDPOINTS` in `endpoints.py`.

# Current Behaviour
Users can add, edit, test, or delete provider configurations. Saved API keys are encrypted at rest with the user's UEK.

# Constraints
- Upstream provider 401s during testing or chat calls return an error message without logging out the user's platform session.

# Future Considerations
- Usage quota monitoring and balance tracking per provider key.

# Related Specs
- [Backend Spec](backend.md)
- [Model Selection Spec](model-selection.md)
- [Routing Spec](routing.md)
