# Release Notes

## v5.7.2 — Auth/session hardening, data integrity & header cleanup

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.7.2`,
`ghcr.io/prashshr/ai-ensemble-web:v5.7.2`. API version `5.7.2`.
Patch release — backward compatible, no schema change, no breaking API change.

### Security

- **Refresh tokens can no longer be used as bearer access tokens.**
  `get_current_user` accepted any signed JWT, so a refresh token (30-day
  lifetime) authorised ordinary protected endpoints. The dependency now
  rejects tokens whose `type` claim is `refresh`. Access tokens do not carry a
  `type` claim, so existing web and mobile sessions continue to work
  unchanged. This is the single most important fix in the release: it shrinks
  a stolen refresh token's usable window from 30 days to the access-token
  lifetime.
- **Sessions now fail closed.** When a client presents a session id that no
  longer resolves, the API returned 200 and silently encrypted new records
  under the server key instead of the user's key. It now returns
  `401 Session expired; please sign in again`.
- **User prompt text is no longer written to logs.** The RAG pipeline logged
  the first 80 characters of the query and the full extracted query list.
  Because pod logs are aggregated outside the application's access controls,
  this leaked prompt content. Counts, timings and engine attribution are
  retained for diagnostics.

### Data integrity

- **Deleting a user now cascades.** SQLite ignores foreign keys unless they
  are enabled per connection, so the `ondelete="CASCADE"` declarations in the
  models were inert. Deleting a user left orphaned discussions, messages,
  provider credentials, refresh tokens and session rows behind. Foreign keys
  are now enabled on every SQLite connection created by the application
  engine. All four existing databases were audited before the change and
  contained zero orphan rows, so enforcement introduces no failures.
- **Alembic migrates the database the app actually uses.** `alembic/env.py`
  read the static URL from `alembic.ini` and ignored `DATABASE_URL`, so
  `alembic upgrade head` could migrate a stray local file rather than the
  deployed database. It now resolves the effective application setting. The
  migration assets also ship inside the backend image.
  Note: the migration chain `ALTER`s tables without creating them, so a fresh
  database still needs `init_db()` (application startup) before `upgrade head`.

### Stability

- **`actor_runtime` is importable again.** An invalid method signature made
  the whole package fail to compile, which broke repository-wide syntax
  validation. The active app did not import it, so there was no runtime
  outage, but the package was unusable.

### Frontend

- **Removed the theme toggle and settings gear from the header's top-left.**
  Both remain reachable: the settings gear sits in the left-pane footer, and
  theme selection lives under Settings → Appearance, which additionally
  offers high-contrast and accent palette options that the old two-state
  toggle could not reach.

### Tests

- Unit tests are hermetic. They previously called the live TypeSafe service
  whenever `TYPESAFE_API_KEY` happened to be set in the environment, which
  made the suite non-deterministic; four RAG tests and three consensus tests
  were affected.
- The RAG network boundary is stubbed so retrieval-dependent tests are fast
  and deterministic while `get_retrieved_context` still runs end to end
  (query extraction, candidate ranking and context formatting are real).
- A bare `pytest` from the repository root now collects the suite. It
  previously reported 52 false async failures because `asyncio_mode` lived
  only in the nested test config.

### Verification

- Backend: 131 passed, 0 failed — identical results with and without
  `TYPESAFE_API_KEY` set in the environment.
- Frontend: `svelte-check` 0 errors (20 pre-existing warnings, unchanged),
  Vitest 95/95, production build succeeds.
- Live Kubernetes deployment verified: health, auth, mobile `sid` sessions,
  discussions, messages (content decrypts), folders, personas, OAuth status,
  user settings and rate limiting all exercised; browser check of the header,
  sidebar and theme picker with no console errors.

## v5.3.0 — TypeSafe System One Integration, Model Thinking Suppression & Stability

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.3.0`,
`ghcr.io/prashshr/ai-ensemble-web:v5.3.0`. API version `5.3.0`.
Frontend verified: `svelte-check` 0 errors, Vitest 47/47 passing.
Backend verified: Pytest 98/98 passing.

### Added

- **TypeSafe System One (Jev) Integration**:
  - `app/services/typesafe_service.py` provides typed System One evaluation (`evaluate_system_one`, `should_search_web`).
  - Speculative triage: fast ~50ms evaluation before query execution to determine if real-time web search or RAG augmentation is genuinely necessary, drastically cutting latency and token consumption.
  - Unit test suite (`testing/backend/unit/test_typesafe.py`) validating noul scoring, decision paths, and fallback mechanisms.
- **Model Thinking Separation & Configurable Display**:
  - `parseModelThinking` in `frontend/src/lib/utils/thinking.ts` parses and separates in-band thinking tags (`<think>`, `<thought>`, `<reasoning>`, `<thinking>`) and upstream reasoning deltas from final answers.
  - Models only display clean final responses by default, preventing noisy thought dumping during generation.
  - Added live pulsing `Thinking…` status badge during active reasoning phase.
  - Added "Show Model Thinking" toggle in both the chatbox Advanced Configuration drawer and User Settings modal.
  - Collapsible `<details class="thinking-block">` when thinking display is enabled.
  - Consensus models similarly sanitized so internal thoughts never pollute synthesis.

### Fixed & Improved

- **Chatbox Advanced Settings Collapse**:
  - Added click-outside and Escape key dismiss handlers via reactive `$effect` in `ChatInput.svelte`, allowing intuitive collapse when clicking outside the panel.
- **Favorite Models Persistence**:
  - Model favorites selection stabilized against login/session resets, maintaining local state with server reconciliation.
- **Provider Panel Layering & Access**:
  - Resolved panel toggling and z-index layering issues on the main chat screen so clicking "Providers" reliably opens the drawer without page refresh.

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
