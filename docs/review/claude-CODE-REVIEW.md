# AI Ensemble — Senior Fullstack + Security + UI Review

**Reviewed:** 2026-07-23
**Scope:** `/arbeit/ai-welt/projects/ai-ensemble` — a multi-model AI discussion/consensus system (compare and synthesize answers from multiple AI providers across structured rounds, with automated web research/RAG).
**Stack:** FastAPI 0.116 / SQLAlchemy 2.0 / Alembic / Python 3.12 backend · Svelte 5 + Vite + TypeScript frontend, also shipped as a Capacitor Android app · Docker Compose (dev/staging) + Kubernetes (prod) deployment.

This document is entirely self-contained to this project — it does not reference or compare against any other codebase. A companion document, [`claude-IMPLEMENTATION-GUIDE.md`](./claude-IMPLEMENTATION-GUIDE.md), turns the prioritized findings below into an ordered, step-by-step task list for a coding agent.

**Note on an existing doc:** `docs/frontend-ui-ux-review.md` was written against the pre-Svelte, single-file `frontend/index.html` monolith, which was fully replaced by the current Svelte architecture about an hour after that doc was committed, and 50+ commits have landed since. Its findings are almost entirely obsolete (streaming, concurrency, semantic color tokens, and the Providers view it flagged as missing all exist now). Recommend renaming it to `docs/archive/pre-svelte-migration-review.md` so it stops being read as current guidance — this review below supersedes it.

---

## Overview

The project has real security craft in places — per-user encryption keys derived from the login password, refresh-token rotation with server-side revocation, DOMPurify used consistently everywhere AI-generated markdown is rendered, a native Android build with proper secure-storage token handling. But several critical issues undercut those good intentions: a **hardcoded default admin account with a password published in the docs**, a **fully open `/proxy` endpoint with no SSRF protection**, a **staging deployment that serves the entire frontend source tree** (not just the built output), and a **rate limiter that is very likely non-functional in production** because it isn't configured to read the real client IP behind the reverse proxy. On the frontend, a genuinely user-visible bug means **Advanced Settings silently reset every follow-up turn**, and the **Stop button doesn't actually stop generation** in the fallback path — it keeps an unwanted, billed request running in the background.

Findings are grouped into three areas — **Backend Security & Architecture**, **Frontend UI/UX & Security**, and **DevOps, Repo Hygiene & Docs** — each ordered by severity.

---

## 1. Backend Security & Architecture

### 1.1 Hardcoded default admin account, seeded on every startup (Critical)
`backend/app/db/session.py:57-69` (`init_db()`, called from `main.py:37` on every app startup) unconditionally seeds `admin@local.ai-ensemble` / password `arhatadmin` if it doesn't already exist. This is public source code, so the credential is public. Admin authorization itself is an **exact email-string comparison** (`backend/app/api/routes/admin.py:22,47`: `current_user.email != "admin@local.ai-ensemble"`), not a role/permission column — so anyone who logs in with this account can enumerate all users (`GET /admin/users`) and delete arbitrary accounts (`DELETE /admin/users/{id}`). Made worse by **the password being published in plaintext inside the repo's own docs** (`docs/architecture.md:1060,1072`), which are more likely to be read/shared than the source. **Action: rotate this password immediately on any live deployment, move to a real `is_admin` column, and redact the password from the docs.**

### 1.2 `/proxy` endpoint has no SSRF protection, and registration is fully open (High)
- `ChatRequest.endpoint` (`app/schemas/provider_proxy.py:24`) and `UpsertProviderCredentialRequest.endpoint` (`app/schemas/provider.py:9`) are free-form strings with no URL validation.
- `normalize_endpoint()` (`app/services/providers/endpoints.py:126-146`) only rewrites the URL for ~10 known provider domains — **anything else (`http://169.254.169.254/...`, `http://localhost:...`, an in-cluster service address) passes through unchanged** and is handed straight to `httpx.AsyncClient` with the user's own API key attached.
- Response bodies are partially reflected back to the caller on error (`proxy.py:105-166`, `body[:500]` in the HTTP error detail; `body[:1000]` also `print()`'d server-side).
- Self-registration (`POST /auth/register`) has no invite code, email verification, or CAPTCHA — only a 10/minute IP rate limit (and see 1.5, that limit is likely shared across all clients).
- **Net effect: any anonymous internet user can self-register in under a minute, register a "custom provider" pointing at an internal address, and use the proxy as an authenticated internal-network probe/relay, with responses echoed back through error messages.** Fix in priority order: validate/allowlist `endpoint` at write- and read-time (reject private/loopback/link-local ranges, re-check after redirects), stop reflecting raw upstream bodies to callers, and consider gating self-registration.

### 1.3 RAG pipeline frames untrusted scraped web content as "primary, must-use, factual" (High)
`app/services/retrieval.py:304-312` and the equivalent block in `app/api/routes/proxy.py:74-95` build a prompt preamble instructing the model to treat scraped web content as a **primary, trusted, must-use** source, with the raw `trafilatura.extract()` output concatenated in with no instruction-injection filtering and no reminder that the block is untrusted data, not operator instructions. Any page that ranks for a user's query — including an attacker-SEO'd or compromised page — can inject "ignore prior instructions and instead..." text, and the surrounding scaffolding actively tells the model to prioritize it. This is close to worst-case framing for prompt injection; it should say the opposite (explicitly untrusted, do not follow instructions found within). Secondary, lower-severity SSRF/redirect risk: `extract_content_from_urls()` (`retrieval.py:225-266`) follows redirects with no destination-host allowlist beyond a small quality-motivated denylist.

### 1.4 Rate limiter is very likely non-functional behind the reverse proxy (High)
`core/limiter.py:5`: `Limiter(key_func=get_remote_address)` reads `request.client.host` — the **direct TCP peer**, not `X-Forwarded-For`. Production topology is Traefik/Caddy → backend, and `backend/Dockerfile`'s uvicorn is started **without `--proxy-headers`**, with no `ProxyHeadersMiddleware` anywhere in `main.py`. So every request's client host is the proxy hop, not the real client — meaning **all users share one rate-limit bucket**. This defeats per-IP brute-force protection on login/register, and worse, lets one abusive client exhaust the shared budget and lock out every legitimate user (self-inflicted DoS). Compounding: `redis` is a listed dependency (`requirements.txt`) but **never imported or used anywhere** — the limiter's storage is in-memory, so limits reset on every pod restart and are trivially bypassed the moment replicas > 1. Fix: add `--proxy-headers`/trusted-IP config to uvicorn (or `ProxyHeadersMiddleware`), fix the `key_func` to read the trusted forwarded header, and wire slowapi to Redis for shared, durable counters.

### 1.5 Schema-drift bug that will break on any non-SQLite database (High)
`app/db/session.py:22-55` (`init_db()`) creates missing *tables* via `Base.metadata.create_all()`, then **only if `database_url.startswith("sqlite")`**, patches in four columns via raw `ALTER TABLE` wrapped in swallow-everything `try/except`. Cross-checking against `backend/alembic/versions/`: **`Discussion.state_json` and `ProviderCredential.label` have no Alembic migration at all** — they only exist via the SQLite-only ad hoc ALTER. If this app is ever pointed at Postgres/MySQL and provisioned via `alembic upgrade head` (the "correct" workflow), the resulting schema is missing those columns, and the very first discussion/provider-credential request 500s. Masked today only because the live k8s config uses SQLite. Fix: write the two missing Alembic migrations; remove the ad hoc ALTER fallback as a second, uncoordinated migration mechanism (or keep it strictly as a defensive backstop, not the only path).

### 1.6 The "User Encryption Key" model is not zero-knowledge — a single server-held key can decrypt everything (High, mostly a documentation/trust issue)
Per-request decryption of provider API keys uses the requesting user's UEK (`app/api/routes/providers.py:54,137,230`, `proxy.py:105`) — expected, since the server must forward the plaintext key to providers. But: for mobile clients, the UEK itself is **persisted server-side, encrypted with the global server key**, not the user's password-derived key (`core/sessions.py:39`) — anyone with DB access *and* `CREDENTIAL_ENCRYPTION_KEY` can decrypt every mobile user's UEK (and everything gated behind it) without the user's password. `decrypt_secret()`/`decrypt_field_or_plaintext()` (`core/crypto.py:61-98`) both silently fall back to the global key on any per-user-key failure, and the latter even falls back to returning raw ciphertext as if it were plaintext on total failure. **Recommendation:** either explicitly document this threat model (the app is "encrypted at rest with a server-held master key," not zero-knowledge, despite the "never touches the device" framing in comments), or stop persisting UEKs server-side for mobile sessions and remove the legacy global-key fallback beyond a one-time migration window.

### 1.7 Weak/dev-default secrets, no production guard (Medium-High)
`backend/app/core/config.py:15,19`: `jwt_secret` and `credential_encryption_key` both default to well-known placeholder strings (`"change-me-in-production"`, `"change-me-32-byte-key-change-me-32"`) with no startup check that refuses to boot if they're still in effect. Current deployment configs (`deploy/k8s`, `deploy/compose`) do inject real secrets, so this specific deployment is likely fine today — but the code itself will silently run insecurely (forgeable JWTs, static/guessable Fernet key) the moment it's run anywhere without the env vars set (local dev against a real DB, a fork, a CI job). Add a `Settings` validator that raises if either value equals its default outside a debug/dev mode.

### 1.8 Access tokens carry the raw UEK in the JWT payload, 24h lifetime, no revocation (Medium)
`core/security.py:20-25`, `auth.py:70,148`: the web access-token JWT includes `"uek": uek` directly in its claims, with a 24h default TTL and no server-side denylist/introspection for access tokens (only refresh tokens are tracked). A leaked web access token (XSS, log capture, a misconfigured proxy) hands over both API access and the decryption key for everything, unrevocably, for up to a day. Consider shortening web-token TTL, moving the UEK server-side for web too (mirroring the mobile session design more consistently, per 1.6's broader caveat), or adding an "invalidate all sessions" path that actually covers web JWTs (today `drop_user()` in `core/sessions.py:93` only clears mobile session entries).

### 1.9 Other backend items (Medium/Low)
- **PBKDF2 iteration count (100,000) is below current OWASP guidance (600,000+ for SHA-256)** — `core/crypto.py:23-29`. Bump the count; consider Argon2id when feasible.
- **Fernet key derivation for the legacy server key right-pads with `0x30` bytes instead of using a real KDF** — `core/crypto.py:10-17`. Use `hashlib.sha256(key).digest()` or HKDF instead.
- **Vertex ADC credentials written to a predictable-prefix temp file and process-global `GOOGLE_APPLICATION_CREDENTIALS` env var mutated per-request** (`services/providers/vertex.py:69-88`) — a real concurrency bug: concurrent async requests in the same process can race on this global mutation, not just a style nit.
- **Broad `except Exception: pass`** — 8 bare-pass occurrences across `core/crypto.py`, `auth.py`, `providers.py`, `proxy.py` — hides real bugs and, in the login-time re-encryption migration loop (`auth.py:91-135`), risks silently-incomplete migrations with no logging.
- **Debug `print()` in request-handling code, bypassing the app's own logging config** — `proxy.py:134` (echoes up to 1000 chars of upstream response body to stdout), `discussions.py:58`.
- **Duplicated "apply provider config to client" logic** between `providers.py:15-32` and `proxy.py:19-33` — belongs on the client class, not copy-pasted into two route modules.
- **`discussions.py` repeats the same decrypt-and-parse-response-flags logic near-verbatim four times** (`create_discussion`, `update_discussion`, `get_discussion`, `list_discussions`) — extract a single `_to_response(discussion, uek)` helper.
- **No backend test suite at all** — no `test_*.py` under `backend/app` (only the vendored pytest package inside `.venv`). A separate, well-organized pytest suite does exist under `testing/backend/`, but it's entirely manual (see §3.7).

---

## 2. Frontend UI/UX, Accessibility & Security

### 2.1 Stop button doesn't actually stop generation — resurrects a stopped card with a billed response (High)
`frontend/src/lib/stores/discussion.svelte.ts:404-458` (`queryModel`): the streaming call is properly abortable, but when it throws for *any* reason — including the expected `AbortError` from clicking Stop — the code unconditionally falls back to a **non-streaming retry that doesn't pass the abort signal at all** (compare `generateConsensus`, which does pass the signal). Clicking Stop aborts the stream but immediately fires a new, uncancellable request to the same provider/model that keeps running (and billing) in the background; when it resolves, the code writes `status: "complete"` with no check that the discussion is still running, so a "stopped" card can silently come back with a full answer. This also triggers on any streaming failure, not just user-initiated stop. Fix: check `#running`/`signal.aborted` before the fallback, and pass the abort signal into the fallback `api.chat()` call.

### 2.2 Advanced Settings silently reset to defaults on every follow-up turn (High)
`ChatInput.svelte` is mounted twice as **independent component instances** — once in `ChatHome.svelte:24` (before the first message), once in `ChatMessages.svelte:141` (after a discussion becomes active) — and `AppContainer.svelte:36-40` unmounts one and mounts a fresh one when the view swaps. Every Advanced Settings field (consensus toggle/model, round count, timeout, RAG mode, response/summary format) is **local `$state` initialized to a hardcoded default** (`ChatInput.svelte:20-38`), never seeded from `discussion.data`, even though `DiscussionState` already persists all of these fields turn-over-turn and `nextTurn()` is designed to carry forward a `settings` object. Net effect: a user's carefully configured council settings survive the first turn (captured before the remount) but **silently reset on every subsequent turn** unless manually re-entered. Fix: seed `ChatInput`'s local state from `discussion.data.*` on mount, or better, lift these settings into the `discussion` store as the single source of truth.

### 2.3 Two independently-drifted vision-capability heuristics (Medium)
`frontend/src/lib/utils/helpers.ts:134-140` (`modelSupportsVision`, used for the model-selector badge) and a **second, textually different** regex inline in `ChatInput.svelte:299-306` (used for the "image attached, model may not support vision" warning) have already diverged — different model-name patterns are matched by each — so a model can show a "vision" badge in the selector while `ChatInput` simultaneously warns it may not support vision, or vice versa. Consolidate into the single `helpers.ts` implementation.

### 2.4 Pasted rich text uses a weaker, hand-rolled sanitizer instead of DOMPurify (Medium)
Every AI-generated markdown render path correctly goes through `safeRenderMarkdown()` (`utils/markdown.ts:16-24`, `marked` + `DOMPurify.sanitize()`, unit-tested) — this part is done right, consistently, everywhere. But pasted HTML in the composer takes a **different, weaker path**: `ChatInput.svelte:274-295`'s own `stripDangerous()` only strips a fixed tag list and `on*`/`href`/`src` attributes via regex — it doesn't touch `style` attributes, `srcdoc`, `formaction`, SVG vectors, or the mutation-XSS edge cases DOMPurify specifically guards against — before inserting via `execCommand("insertHTML", ...)` into the live contenteditable DOM. The eventual text sent to the backend is `innerText` (limiting blast radius somewhat), but the intermediate DOM injection into the live page is still a real gap if the regex sanitizer is bypassed. Route pasted HTML through `DOMPurify.sanitize()` (already a dependency) instead.

### 2.5 `--text-tertiary` fails WCAG AA contrast in both themes (Medium)
`frontend/src/app.css:12,51` — dark theme `#52525b` on near-black (~2.7:1), light theme `#a1a1aa` on near-white (~2.5:1); both fail the 4.5:1 AA threshold and even the 3:1 large-text minimum. Used for genuinely informative text throughout (loading/status text, provider/model counts, hint text, log timestamps, "via {model}" attribution) — not purely decorative.

### 2.6 No focus trap or Escape-to-close on the app's only modal-like surface (Medium)
`ProviderPanel.svelte:54-58` — a full off-canvas drawer with a backdrop, but no `role="dialog"`/`aria-modal`, no focus moved in on open or restored on close, and no `Escape` handler anywhere in the codebase. A keyboard user can currently tab from the header straight through into content behind the open drawer. Same gap applies to `DebugPanel.svelte` (moot today since nothing opens it — see 2.8).

### 2.7 Large file uploads parsed synchronously on the main thread, no size caps beyond a blanket 100MB check (Medium)
`frontend/src/lib/utils/extractDocument.ts` — PDF page iteration, XLSX sheet-to-CSV conversion, and PPTX slide-XML extraction (via `@zip.js/zip.js`) all run on the UI thread with no per-format page/row/entry cap and no Web Worker offload. A large-but-valid document well under the 100MB gate (e.g. a 500-page PDF, a million-row spreadsheet, a PPTX with many slide entries) can visibly hang the UI, and there's no zip-bomb-style ratio check on the PPTX unzip path. Extracted text (plus base64 attachments) is also serialized to `localStorage` on every `persist()` call with failures only logged, never surfaced — a user can silently lose in-progress discussion state on refresh after a large attachment.

### 2.8 Dead/unreachable features (Low-Medium)
- **Debug panel can never be opened** — `debug.open` is only ever set by the panel's own internal Close button; no menu item, shortcut, or button anywhere else calls `debug.toggle()`, despite `debug.log()` being called throughout the stores.
- **`stores/nav.svelte.ts` (49 lines) is entirely unused** — a full hash-based tab router with no consumer anywhere; real navigation is handled ad hoc in `AppContainer.svelte`.
- **A third theme, `ps-xai-orange`, is declared in the type (`theme.svelte.ts:2`) but has no CSS and no way to select it** — the toggle only flips dark/light.

### 2.9 Other frontend items (Low)
- **Native blocking dialogs** (`prompt()`/`confirm()`/`alert()` in `ChatSessions.svelte:105,112`, `ProviderPanel.svelte:39`, `ChatInput.svelte:124`) visually clash with an otherwise polished custom dark UI.
- **Copy buttons have `title` but no `aria-label`** (`ModelCard.svelte:52-58`, `ConsensusSection.svelte:46-52`).
- **Resize-handle widgets declare ARIA roles implying operability but have no `tabindex`/keyboard handler** (`ChatSessions.svelte:219-228`'s sidebar resize has `role="separator"` with no keyboard support at all; `ChatInput.svelte:316-317`'s resize handles have neither role nor keyboard alternative).
- **`aria-live` toggled on/off on the same element** rather than kept stable with only its content changing (`ModelCard.svelte:40`) — a known source of inconsistent screen-reader announcement.
- **~12 hardcoded hex colors bypass the token system** across `ConsensusSection.svelte`, `ChatMessages.svelte`, `ChatInput.svelte`, `ModelSelector.svelte` — notably `ConsensusSection.svelte:128-130`'s error state is styled in the *warning* amber color, not `var(--error)`.
- **`ChatInput.svelte` is a 984-line god component** mixing rich-text editing, attachment/file-parsing, a full advanced-settings mega-form, resize handling, and vision-capability warnings — the largest and, per 2.1/2.2, riskiest file in the app, and untested (see 2.10).
- **Android status/navigation bar colors are hardcoded black**, not synced to the in-app light/dark toggle — a light-mode user sees a black system bar over a white app body.
- **Three different loading-state idioms** (animated skeleton in `ModelCard`, plain "Loading…" text in `ChatSessions`/`ProviderPanel`, spinner+text in `ModelSelector`) for the same underlying "waiting on network" state.

### 2.10 Testing (Low, but a real gap)
6 vitest spec files exist and are genuinely meaningful (real logic assertions, not snapshots) — but coverage is concentrated on 2 stores and 1 component. `ChatInput.svelte` (984 lines, the riskiest file), `auth`/`providers`/`models`/`folders`/`debug` stores, the streaming-fallback path where the Stop-button bug lives, and all document-parsing code have zero tests. No coverage reporting configured. No CI runs the suite (see 3.7).

---

## 3. DevOps, Repo Hygiene & Docs

### 3.1 Docker Compose/Caddy serves the entire frontend source tree, not the built output (High)
`deploy/compose/docker-compose.yml:26` mounts `./frontend:/srv:ro`, and `deploy/caddy/Caddyfile:12-15` serves it directly as static files — meaning the "staging" compose stack publicly serves `node_modules/`, `src/`, `package.json`, `capacitor.config.ts`, test files, and TypeScript source/comments, not just `frontend/dist/`. Fix: mount `./frontend/dist:/srv:ro` and require a build step first.

### 3.2 `hostPath` volumes tie "production" to one specific machine and undermine image-based deploys (High)
`deploy/k8s/deployment.yaml:76-84` mounts `hostPath: .../data` (expected, for the SQLite file) but also `hostPath: .../backend/app` (application **source code**) directly into the pod at `/app/app`, overlaying whatever's baked into the `ghcr.io/prashshr/ai-ensemble:v3.4.1` image. `web-deployment.yaml:45-49` does the same for `frontend/dist`. This means `kubectl rollout undo` won't actually roll back code, only the image reference, and the deployment silently depends on a single node having that exact path with (possibly uncommitted) local files.

### 3.3 Default admin password published in checked-in docs (High — see also 1.1)
`docs/architecture.md:1060,1072` documents the exact `admin@local.ai-ensemble` / `arhatadmin` credential in plaintext. Redact once 1.1 is fixed.

### 3.4 `.venv` and a debug APK are tracked in git despite being gitignored (High)
`backend/.venv/` (5,303 files, compiled binaries) and `frontend/android/app-debug.apk` (4.6MB) are both currently tracked — committed before their respective `.gitignore` rules existed, and a gitignore entry doesn't retroactively untrack already-committed files. Both bloat every clone (`.git` is 137MB). Fix: `git rm -r --cached backend/.venv` and `git rm --cached frontend/android/app-debug.apk`.

### 3.5 No CI test gate at all (Medium-High)
The only workflow, `.github/workflows/opencode.yml`, is a chatops trigger (`/oc` comment → third-party AI-assistant action) — it does not run tests, lint, or build anything, and is pinned to `@latest` rather than a version/SHA (a supply-chain smell for an action with `id-token: write`). The real, well-organized pytest suite under `testing/backend/{unit,integration,e2e}/` and the frontend's `vitest` suite are both **entirely manual** — nothing gates merges to `main`.

### 3.6 K8s hardening gaps (Medium)
All three workloads (`deployment.yaml`, `web-deployment.yaml`, `searxng-deployment.yaml`) explicitly set `runAsNonRoot: false`/`fsGroup: 0`, opting out of non-root execution rather than defaulting safely — matching `backend/Dockerfile`'s missing `USER` directive (container runs as root). Only the backend Deployment has liveness/readiness probes; nginx and SearXNG have none. No `.dockerignore` exists anywhere, so `backend/.venv`/`.pytest_cache` get sent as build context even though the Dockerfile doesn't `COPY` them.

### 3.7 Documentation drift (Medium)
`docs/architecture.md` and `docs/production-plan.md` are both dated Jul 9, while significant work has continued past that (folders, admin, Capacitor/CORS fixes, v3.4.1). Concrete drift confirmed by diffing against actual code: the API-routes table is missing the `folders` and `admin` routers entirely; the Compose section describes a renamed `./web` directory and wrong host port (documented 8080, actual 8088); the CORS-origins description is stale relative to the Capacitor-related entries actually shipped; documented image pull policy (`Always`) doesn't match the actual manifest (`IfNotPresent`); `production-plan.md`/`production-handover.md` still describe the pre-migration vanilla-JS/Nginx frontend, not the current Svelte SPA. `scripts/run-dev.sh` is broken for the current frontend (still runs a plain Python static file server against source that requires Vite). The root-level agent-instruction files `AGENTS.md` and `PROJECTS.md` repeat the same stale "vanilla HTML/JS + PostgreSQL" description of the stack — an agent trusting them would start from a materially wrong mental model (the actual stack is Svelte + SQLite everywhere).

### 3.8 Other DevOps/hygiene items (Low)
- `frontend/android/.gitignore:40-42` has the keystore-exclusion lines (`*.jks`/`*.keystore`) commented out — uncomment pre-emptively, before a real release-signing key is ever generated.
- `.quarantine/` (correctly gitignored, 16MB of confirmed-superseded pre-Svelte frontend + pre-reorg test suite) and `.playwright-mcp/` (gitignored debug logs/screenshots) are stale local clutter, safe to delete but not a git risk.
- `frontend-legacy/index.html` (279KB) is a **tracked** duplicate of dead code that's otherwise correctly quarantined and gitignored elsewhere — inconsistent with the project's own quarantine convention; delete or move into `.quarantine/` and untrack.
- `testing/infrastructure/` is a completely empty directory despite being described in `testing/README.md` as covering k8s/Docker infra tests.
- `.env`/`.env.example`/`data/ai_ensemble.db` are all correctly gitignored and untracked — good baseline hygiene there.

---

## Summary table

| # | Area | Finding | Severity |
|---|------|---------|----------|
| 1.1 | Backend | Hardcoded default admin account, password published in docs | Critical |
| 1.2 | Backend | `/proxy` SSRF — no endpoint validation, open self-registration | High |
| 1.3 | Backend | RAG frames untrusted scraped content as primary/trusted | High |
| 1.4 | Backend | Rate limiter likely non-functional behind reverse proxy | High |
| 1.5 | Backend | Missing Alembic migrations — breaks on non-SQLite DBs | High |
| 1.6 | Backend | Not zero-knowledge — server-held global key decrypts everything | High (doc/trust) |
| 1.7 | Backend | Dev-default secrets, no production startup guard | Medium-High |
| 1.8 | Backend | UEK in JWT claims, 24h TTL, no access-token revocation | Medium |
| 1.9 | Backend | PBKDF2 iterations, Fernet padding, Vertex env race, broad excepts, debug prints, duplicated logic, no tests | Medium/Low |
| 2.1 | Frontend | Stop button doesn't abort fallback request — billed, resurrects card | High |
| 2.2 | Frontend | Advanced Settings silently reset every follow-up turn | High |
| 2.3 | Frontend | Two drifted vision-capability heuristics | Medium |
| 2.4 | Frontend | Pasted HTML uses weaker sanitizer than AI-content path | Medium |
| 2.5 | Frontend | `--text-tertiary` fails WCAG AA in both themes | Medium |
| 2.6 | Frontend | No focus trap/Escape on the Providers drawer | Medium |
| 2.7 | Frontend | Large file parsing on main thread, no caps/worker offload | Medium |
| 2.8 | Frontend | Debug panel unreachable, dead nav store, dead theme type | Low-Medium |
| 2.9 | Frontend | Native dialogs, missing aria-labels, unlabeled resize handles, token-bypassing colors, god component, Android bar-color parity | Low |
| 2.10 | Frontend | Test coverage concentrated on 2 stores + 1 component, no CI | Low |
| 3.1 | DevOps | Compose/Caddy serves entire frontend source tree | High |
| 3.2 | DevOps | `hostPath` volumes undermine image-based prod deploys | High |
| 3.3 | Docs | Default admin password published in `architecture.md` | High |
| 3.4 | Repo hygiene | `.venv` + debug APK tracked despite gitignore | High |
| 3.5 | CI | No automated test gate; only workflow is a chatops trigger | Medium-High |
| 3.6 | DevOps | K8s: root containers, missing probes, no `.dockerignore` | Medium |
| 3.7 | Docs | Architecture/production docs and agent-instruction files drifted from code | Medium |
| 3.8 | Repo hygiene | Keystore gitignore commented out, quarantine/legacy clutter, empty test dir | Low |

See [`claude-IMPLEMENTATION-GUIDE.md`](./claude-IMPLEMENTATION-GUIDE.md) for an ordered, step-by-step remediation plan covering the High and Critical items above.
