# Release Notes

## v5.2.0 — Speed/smoothness + subscription login (ChatGPT, Gemini)

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.2.0`,
`ghcr.io/prashshr/ai-ensemble-web:v5.2.0`. API version `5.2.0`.
Frontend verified: `svelte-check` 0 errors, Vitest 41/41 passing.

### Added

- Connect with ChatGPT (right provider panel): Codex device-code login —
  connect shows a browser link + one-time code, polls until approved, stores
  per-user UEK-encrypted tokens. No API key; usage bills to the ChatGPT plan.
  Provider key `codex` with models `gpt-5.6-sol/terra/luna`, `gpt-5.5`,
  `gpt-5.3-codex`. Requires device-code auth enabled in ChatGPT
  (Settings → Security). Multi-user safe: each user connects their own account.
- Connect with Gemini (right provider panel): Google OAuth popup login for the
  Gemini Developer API (Bearer auth, no API key). Server needs
  `GOOGLE_OAUTH_CLIENT_ID/SECRET` plus redirect
  `{BACKEND_PUBLIC_URL}/api/providers/oauth/google/callback` registered in
  Google Cloud Console; otherwise Connect returns a clean "not configured" error.
- Per-user OAuth token vault (`provider_oauth_tokens` + Alembic migration),
  automatic refresh with 60s skew and one 401-retry, status/disconnect endpoints.

### Changed (speed & smoothness, Phase 1+2)

- True streaming for Anthropic, Gemini/Vertex, Perplexity (was buffered full
  responses); shared HTTP connection pool; per-provider concurrency caps;
  single 429/502/503 retry with backoff.
- Frontend `timeout` setting now enforced per model (`timeout` status + retry);
  backend accepts and applies `timeout` per request.
- Streaming render throttled (plain text while streaming, markdown on completion),
  batched store updates, scroll jank fixed, throttled persistence.
- RAG: parallel extraction (4-way), 5s per-URL timeout, 8000-char cap, max 6
  sources, 30-min query cache; prompt budgets (12k RAG / 2k per prior answer).
- Fixed actor-stream credential bug (wrong unpack order + salt-as-UEK).

### Known limitations

- Backend test suite cannot run in this checkout (missing `fastapi` in local envs);
  verified via `compileall`, targeted mock suites (40+11 pass), frontend checks.
- In-memory OAuth pending store: single-replica only (documented in code);
  use sticky sessions if scaled.
- Grok subscription login not included (BYOK `xai` unchanged).

## v5.1.0 — Model health & vision reliability

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.1.0`,
`ghcr.io/prashshr/ai-ensemble-web:v5.1.0`. API version `5.1.0`.
Frontend verified: `svelte-check` 0 errors, Vitest 41/41 passing.

### Added

- Favorite models drawer (star any model, foldable bottom section in provider panel).
- Unified user settings modal (theme, response/summary defaults, timeout).
- Multi-format document parsing (`.xlsx`, `.docx`, `.pptx`, `.ipynb`, `.pdf`, `.csv`, …).
- "Only OK models" toggle per provider (provider Settings + model selector toolbar,
  persisted per provider) to hide failing/untested model noise.
- Hybrid Vision Bridge: vision models get native images, text-only models get a
  structured markdown transcription from a bridge vision model.
- Model selector: health-`OK` models sort to the top; batch/contributor endpoints
  filtered from discovery; search filter; exact upstream error on `KO` hover.

### Fixed

- Image transcriptions keyed by content fingerprint instead of filename, cleared on
  `reset`/`start`/`load` (stale screenshot reuse eliminated).
- Expanded vision-model recognition (`claude`, `gpt-4o/5`, `gemini`, `qwen-vl/3`,
  `mimo`, `kimi`).
- OpenRouter: `HTTP-Referer`/`X-Title` headers, 600/min proxy limit, reasoning-delta
  stream extraction (`reasoning_content`/`reasoning`).
- Right-drawer left-edge drag resizer with persisted width.
- Compact mode: dual-anchored format directives (top + bottom of prompt) with strict
  150–250 word mandate and compact follow-up turn framing.

### Known limitations (planned next)

- Response latency / timeouts: streaming is OpenAI-compatible-only (Anthropic, Gemini,
  Vertex, Perplexity buffer full responses); frontend `timeout` setting is stored but
  not enforced; no shared HTTP connection pool; RAG pipeline blocks first token.
- Provider auth is BYOK API-key only; no subscription (ChatGPT/Google/Grok) login yet.
