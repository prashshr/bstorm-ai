# Specification: Model Selection & Discovery

# Purpose
The Model Selection subsystem specifies model discovery, regional Smart Discovery (Vertex AI), capability classification (vision vs text-only), model searching/filtering, and selection state management.

# Responsibilities
- Query provider `/models` endpoints to dynamically discover available model IDs.
- Execute GCP Vertex AI Smart Discovery across prioritized regions (`global`, `us-east5`, `europe-west1`, `asia-southeast1`).
- Classify model capabilities (e.g. vision support via `VISION_RE` vs text-only via `TEXT_ONLY_RE`).
- Test vision capability using canvas-generated CAPTCHA verification images.
- Manage selected models state in `models.svelte.ts` store.

# Architecture

```mermaid
graph TD
    UserUI[ModelSelector.svelte] -->|Select Provider| Store[models.svelte.ts]
    Store -->|GET /api/providers/{key}/models| API[FastAPI Provider Models Route]
    
    API --> Factory[Provider Client Factory]
    Factory -->|Standard Provider| StdClient[OpenAI / Anthropic / Gemini Client]
    Factory -->|Vertex Provider| VertexClient[VertexClient]
    
    StdClient -->|GET /models| Upstream[Upstream Provider API]
    VertexClient -->|Smart Regional Discovery| GCP[GCP Vertex Catalog Probing]
    
    Upstream & GCP --> API
    API -->|Model Array| Store
    Store --> VisionCheck[Vision Model Classifier]
```

# Model Capability Regex Patterns (`helpers.ts`)
- **Vision Models (`VISION_RE`)**: `/vision|gpt-4o|claude-3|gemini-1\.5|gemini-2|llava|pixtral|qwen-vl/i`
- **Text-Only Models (`TEXT_ONLY_RE`)**: `/deepseek|llama|mistral|gemma|qwen(?!.*vl)|coder|instruct-only/i`

# Data Flow
1. User opens provider settings or drawer in UI.
2. `models.discover(providerKey)` issues `GET /api/providers/{key}/models`.
3. Backend returns model ID array.
4. User clicks a model chip to toggle its inclusion in `models.selected` array (`models.toggle(key)`).

# Internal Components
- `models.svelte.ts`: Svelte 5 Runes store keeping `all` discovered models, `selected` models, and `verified` vision capabilities.
- `ModelSelector.svelte`: Searchable model selection component.
- `VertexClient`: Implementation executing multi-region probe across candidate models in `VERTEX_CATALOG`.

# Public Interfaces
- Endpoint: `GET /api/providers/{provider_key}/models`
- Store Methods: `models.discover(key)`, `models.toggle(key)`, `models.selectAll()`, `models.clear()`.

# Dependencies
- `models.svelte.ts`, `helpers.ts`, `vertex.py`.

# Configuration
- Vertex Regional Probe List: `["global", "us-east5", "europe-west1", "asia-southeast1"]`.

# Current Behaviour
Selected model keys are formatted as `providerKey::modelId` (e.g. `openrouter::openai/gpt-4o`). The selection is preserved across turns in an active discussion.

# Constraints
- DeepSeek models are text-only; attaching images displays an inline vision warning banner in `ChatInput.svelte`.

# Future Considerations
- Automatic benchmark ratings (MMLU, HumanEval) displayed next to model names in the selector.

# Related Specs
- [Providers Spec](providers.md)
- [Routing Spec](routing.md)
- [Prompt Composer Spec](prompt-composer.md)
