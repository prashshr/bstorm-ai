# Release Notes

## v5.8.0 — Access-token versioning, header centred on the page

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.8.0`,
`ghcr.io/prashshr/ai-ensemble-web:v5.8.0`. API version `5.8.0`.
Minor release — one new column, added automatically, backward compatible: no
manual migration and nobody is signed out by deploying.

### Security

- **A password change now invalidates access tokens that were already issued.**
  Access tokens are stateless JWTs, so v5.7.3 could revoke *refresh* tokens and
  server sessions but a stolen web access token kept working until it expired
  — up to the full access-token lifetime after the victim changed their
  password. That window is now closed:

  - Every access token carries a `token_ver` claim matching
    `users.token_version`; `get_current_user` rejects a mismatch with 401, so
    revocation is enforced on the next request rather than at expiry.
  - `change-password` bumps the version and returns a replacement
    `access_token` (and `token_version`) for the session that performed the
    change, so the user is not signed out of the dialog they just used. The
    frontend adopts it before making another call.
  - Login and refresh stamp the version that is current at the moment of
    issue. `create_access_token` takes the version as a **required** argument
    precisely because a forgotten stamp would sign a user out immediately
    after signing them in.
  - A mobile session's replacement token keeps its `sid`, so the device can
    still resolve its encryption key server-side.
  - Deploying signs nobody out: a token with no `token_ver` claim (every token
    minted before this release) is treated as version 1, which is where every
    existing user starts. Proven against a pre-deploy-shaped token in the live
    pod.
  - Unchanged, stated plainly: an ordinary **logout** still relies on refresh
    revocation — a plain access token from that session lives until it expires.
    Versioning is tied to credential changes, not to logout.

### Database

- New column `users.token_version INTEGER NOT NULL DEFAULT 1`. It is applied
  automatically at startup by `init_db()` for every backend (not just SQLite),
  and carried by Alembic revision `c3d4e5f6a7b8` for fresh installs. The
  ALTER was rehearsed against a copy of the live database first — 134 users,
  no NULLs, and a second run fails softly without breaking startup.

### Frontend

- **The header title is centred on the page.** It used to be offset by half
  the sidebar width to line up with the chat column, which slid the title
  102px to the right every time the sidebar opened. It is now pinned to the
  page centre (measured on production: exactly `viewport / 2` in every state,
  0px movement on expand and collapse). The trade-off is that with the sidebar
  open the title no longer sits above the chat column's centre — for a global
  app label that is the right call, and it is what ChatGPT and Claude do.

### Verification

- Backend **142** passed (11 new token-versioning tests), frontend **108**
  passed (3 new), `svelte-check` 0 errors / 20 pre-existing warnings,
  `compileall` clean, production build clean.
- Live deployment: schema verified in-pod (column present for all 134 users,
  zero NULLs, idempotent restart); a 28-check smoke suite covering both
  pre-change access tokens rejected immediately, the replacement accepted, and
  refresh/login stamped at version 2; 6 backward-compat checks including a
  pre-deploy token with no claim still authorising API calls; a 12-check
  browser run of the settings dialog (success message, session kept, stored
  token replaced, old token refused from the page's own origin, no console
  errors); and the header measured at page centre before and after expanding
  the sidebar.

## v5.7.4 — RAG DNS-rebinding fix, secret-safe migration helper

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.7.4`,
`ghcr.io/prashshr/ai-ensemble-web:v5.7.4`. API version `5.7.4`.
Patch release — backward compatible, no schema change, no breaking API change.

### Security

- **Closed the RAG DNS-rebinding (TOCTOU) gap.** The fetcher validated DNS
  *before* the request, but the HTTP client resolved the hostname again when
  connecting. A host that answered publicly during validation and privately at
  connect time could therefore still reach internal addresses. After the
  connection is established, the address actually connected to
  (`server_addr` on the real socket) is now checked too, before any body is
  read. TLS verification is untouched — no address pinning, no SNI rewriting —
  so public HTTPS retrieval behaves exactly as before.
  Verified in the deployed pod: with pre-validation forced to pass, a loopback
  target is still refused; with the check disabled, the same test leaks
  content.
- **`migrate.sh` no longer prints credentials.** It echoed the raw DSN, which
  would expose `user:password@host` in terminal scrollback and CI logs for a
  non-SQLite target. Credentials are now redacted for `user:pass@host`,
  `:password@host` and `user@host` forms, and a non-SQLite target states
  explicitly that the operator must take and verify their own external backup.

### Frontend

- **The transcript floor is now visible.** The 15,000-character minimum is a
  deliberate trade-off — a very large prompt must not starve the transcript to
  nothing — but when it applies the combined prompt can exceed the nominal
  70,000-character budget with nothing indicating it.
  `buildCompactedTranscript` now returns `floorApplied` and `budgetUsed`, and
  the prompt builder logs a warning when the floor applies. Tests assert both
  the bounded and the floored contracts.

### Verification

- Backend: 131 passed; `compileall` clean over `app/` and `alembic/`.
- Frontend: 105 passed, `svelte-check` 0 errors / 20 pre-existing warnings,
  production build clean.
- Live Kubernetes deployment: SSRF refusal of IMDS / RFC1918 / loopback /
  metadata hostnames, successful public retrieval, and the rebinding defence
  exercised with pre-validation forced to pass; plus the full 19-check smoke
  suite (auth, mobile sessions, registration without UEK, password-change
  revocation, discussions, message decryption, folders, personas, OAuth).

## v5.7.3 — RAG SSRF hardening, session revocation, frontend state repairs

Backend and web images: `ghcr.io/prashshr/ai-ensemble:v5.7.3`,
`ghcr.io/prashshr/ai-ensemble-web:v5.7.3`. API version `5.7.3`.
Patch release — backward compatible, no schema change, no breaking API change.

### Security

- **RAG page fetching is now SSRF-safe.** The fetcher followed redirects and
  read bodies in full, guarded only by a string hostname blocklist. A search
  result could therefore make the server request loopback, RFC1918, or cloud
  metadata endpoints (including AWS/GCP/Azure IMDS), and an oversized body was
  buffered whole into memory. Now: scheme allow-list, DNS resolution checked so
  private / loopback / link-local / reserved / IPv4-mapped addresses and
  metadata hostnames are refused, every redirect hop revalidated, and the body
  streamed under a documented 4 MB cap. Public web retrieval is unchanged —
  verified against live pages from inside the deployed pod.
- **Changing your password now signs out other sessions.** `change-password`
  updated the password and re-encrypted the UEK but left every refresh token
  and server-side session alive, so a stolen session survived the very action
  intended to end it. All other refresh tokens are revoked and their
  `session_store` rows dropped. The session making the request is preserved
  when it supplies its refresh token (new optional request field), so the user
  is not logged out of the dialog they just used. The response now reports how
  many other sessions were signed out.
  Limitation, stated plainly: a *stateless web access token* carries no session
  id, so it stays valid until it expires (up to the access-token lifetime) even
  after revocation. The attacker cannot renew it, which bounds the window.
  Shortening that requires token versioning.
- **Registration honours the client type.** `RegisterRequest` had no `client`
  field, so registration always returned a UEK-bearing access token — a mobile
  client registering therefore received the user encryption key on the device,
  breaking the mobile security model. It now accepts the same optional `client`
  field as login and honours `"mobile"`; omitting it keeps the legacy web
  behaviour exactly.

### Operations

- **`backend/scripts/migrate.sh`** — a deliberate, backup-taking migration
  helper. Verified fact: five of the twelve model tables (`agent_personas`,
  `messages`, `search_history`, `session_store`, `user_settings`) have no
  Alembic revision that creates them, and `init_db()` only patches five fixed
  historical columns — it does not add new ones (confirmed experimentally: a
  dropped column is not restored). So `alembic upgrade head` is **not** a
  complete upgrade path and is deliberately not run at startup. The script
  takes a consistent backup, applies revisions, verifies the expected tables,
  and prints the rollback command.
- Documented that `.env` resolves relative to the working directory, which is
  why the quick start places it at `backend/.env`.

### Frontend

- **Retrying a single model no longer wedges the app.** `retryModel` set the
  shared running flag and never cleared it, leaving the button stuck on "Stop"
  and blocking new discussions until a page reload. State is now tracked with a
  round flag plus a standalone-retry counter, so concurrent retries cannot race
  each other or an in-flight round. Three regression tests were added and
  verified to fail against the previous implementation.
- **Reloading a shared discussion link no longer duplicates it.** Deep-link
  recovery called `start()`, which resets state and creates a new discussion,
  orphaning the original on every reload. It now resumes the existing
  discussion id.
- **Transcript compaction honours its budget at the final tier** instead of
  silently overflowing the model context window when a large prompt leaves
  little room.
- **Password change reports the outcome**, e.g. "Signed out of 2 other
  sessions."

### Verification

- Backend: 131 passed. Frontend: 104 passed (three new test files),
  `svelte-check` 0 errors / 20 pre-existing warnings, production build clean.
- Live Kubernetes deployment exercised: health, auth, mobile `sid` sessions,
  registration-without-UEK, password-change revocation (own session retained,
  other device's refresh token rejected), discussions, message decryption,
  folders, personas, OAuth status, plus SSRF refusal of IMDS / RFC1918 /
  loopback / metadata hostnames and successful public retrieval.

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
