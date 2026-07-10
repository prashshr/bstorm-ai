# AI Ensemble — Frontend Implementation Plan

> Generated from review of `docs/frontend-ui-ux-review.md` against actual codebase.
> Baseline SHA: `30658b5`
> Plan date: 2026-07-10

## Recommendation Classification

| # | Review Recommendation | Verdict | Rationale |
|---|----------------------|---------|-----------|
| 1 | Restore semantic status colors | **ACCEPT** | Bug: all `--success`/`--error`/`--warning` set to orange. Low risk, high value. |
| 2 | Full accessibility layer (roles, ARIA, focus traps) | **MODIFY** | Quick wins only: `aria-label`, `:focus-visible`, text+emoji badges. Defer full ARIA. |
| 3 | Fix broken CSS foundations | **ACCEPT** | `:root` nesting, undefined `--accent-hover`, dead sidebar. Clear bugs. |
| 4 | Split single 5,155-line file | **REJECT** | User override: no rewrite. Splitting is restructuring without feature gain. |
| 5 | Stream responses via SSE | **ACCEPT** | User override #6 mandates streaming. Implement SSE end-to-end. |
| 6 | Execute models in parallel | **ACCEPT** | User override #7. Bounded concurrency (semaphore, max 3). |
| 7 | Consolidate provider entry | **DEFER** | Two paths work; risk of breaking existing flow. |
| 8 | Pin CDN deps + SRI | **ACCEPT** | Quick win, supply-chain safety. |
| 9 | Left-rail IA + new views (Providers/Analytics/Admin) | **REJECT** | User override #5: no new navigation surfaces without validation. |
| 10 | 3-step setup flow | **REJECT** | Restructures UI without clear benefit. |
| 11 | Collapse completed rounds by default | **DEFER** | User override #8: no UX default changes without evidence. |
| 12 | Debounce history search | **DEFER** | Minor performance win; defer to next iteration. |
| 13 | Remove dead/double calls | **ACCEPT** | `updateStatusDot()` ×2, `closeDiscussionSummary()` ×2. Low risk. |

## Implementation Stages

### Stage 1 — CSS Foundations & Quick Wins
**Files:** `frontend/index.html`
**Scope:**
1. Fix `:root` block — move nested `.login-page-container`, `.model-card`, `.app-layout.full-width` rules out of `:root {}`
2. Restore distinct semantic colors: `--success: #22c55e`, `--warning: #f59e0b`, `--error: #ef4444` with matching `-bg` variants (keep `--proceed` as brand orange)
3. Define `--accent-hover: #ff7e33` (was referenced but undefined at line 815)
4. Pin CDN `marked` and `DOMPurify` to exact versions with `integrity` SRI attributes
5. Add `:focus-visible` global style for keyboard accessibility
6. Add `aria-label` to icon-only buttons (theme toggle, password eye, modal close, debug toggle)
7. Replace emoji-only status badges with text+emoji (e.g., `✓` → `✓ Complete`)
8. Fix double calls: `updateStatusDot()` called twice at 3805-3806, `closeDiscussionSummary()` twice at 4732-4733
9. Define `@media (prefers-reduced-motion: reduce)` for pulse/shimmer animations

### Stage 2 — Bounded Model Concurrency
**Files:** `frontend/index.html`
**Scope:**
1. Replace sequential `for...of` model loop in `runRound()` with concurrent execution
2. Implement async semaphore with max 3 concurrent queries
3. Preserve 500ms initial stagger for rate-limit safety
4. All model cards show "connecting" simultaneously
5. Preserve all error handling, retry, skip, and replacement behavior

### Stage 3 — Backend SSE Streaming
**Files:** `backend/app/services/providers/base.py`, `backend/app/services/providers/openai_compatible.py`, `backend/app/api/routes/proxy.py`, `backend/app/schemas/provider_proxy.py`
**Scope:**
1. Add `chat_stream` abstract method to `ProviderClient` base class (default fallback to batch)
2. Implement `chat_stream` for `OpenAICompatibleClient` using `httpx.AsyncClient.stream()` — reads SSE `data:` lines and yields text deltas
3. Add SSE streaming endpoint `POST /api/proxy/chat/stream` returning `StreamingResponse` with `text/event-stream`
4. Accept same `ChatRequest` payload, return SSE events: `data: {"type":"delta","content":"..."}\n\n` and `data: {"type":"done","content":"..."}\n\n`
5. Handle errors: `data: {"type":"error","detail":"..."}\n\n`
6. Preserve existing batch endpoint; streaming is additive

### Stage 4 — Frontend Streaming
**Files:** `frontend/index.html`
**Scope:**
1. Add `queryModelStream()` function using `fetch` with `response.body.getReader()` for streaming consumption
2. On each SSE `data:` event, append tokens to the card's response element
3. Show a blinking caret (`▊`) while streaming
4. Update `queryModel()` to detect streaming support and fall back to batch
5. Preserve all existing truncation heuristic, stats calculation, and error handling
6. Consensus generation also uses streaming where possible

### Stage 5 — Testing & Release
**Files:** `testing/backend/integration/test_proxy.py`, `backend/app/main.py`
**Scope:**
1. Add integration tests for streaming endpoint
2. Run full test suite (89+ existing tests) to verify no regressions
3. Bump version: `backend/app/main.py` → `"1.1.0"` (feature release after v1.0.12)
4. Create git tag `v1.1.0`

## Rollback Procedure
- Baseline SHA: `30658b5`
- To roll back all changes: `git reset --hard 30658b5 && git clean -fd`