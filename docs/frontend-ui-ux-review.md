# AI Ensemble — Frontend UI/UX Review & Modernization Plan

> **Status:** Review and recommendation only. No source code was modified. No dependencies were installed. No files were renamed or deleted.
>
> **Scope reviewed:** `frontend/index.html` (5,155 lines, single-file SPA), backend API routes under `backend/app/api/routes/`, and repository documentation (`README.md`, `docs/`).
>
> **Evidence conventions used throughout:**
> - **OBSERVED** — directly verified from repository code.
> - **INFERRED** — strongly inferred from implementation.
> - **RECOMMENDED** — proposed future direction.
>
> Runtime behavior was **not** visually observed. The application was not run; all findings derive from static inspection of the code. Statements about visual behavior are marked INFERRED where they rely on reading CSS/JS rather than a running instance.

---

## 1. Executive Summary

AI Ensemble is a **multi-model AI "council" / deliberation tool**. A user configures one or more LLM providers (BYOK), selects 2–5 models, asks a question, and the app runs the models through 2–3 structured rounds (with optional live web-search RAG), then a consensus model synthesizes a final answer. The entire frontend is a **single 5,155-line `frontend/index.html`** file (OBSERVED) containing inline `<style>`, inline JS, and a large amount of inline `style="..."` attributes, served statically by nginx (OBSERVED, `README.md:42`).

### Strongest aspects
- **Feature-rich and genuinely useful workflow.** The round-based deliberation, per-model retry/skip/replace, consensus synthesis, token/latency stats, RAG + deep-research toggles, export, and resumable sessions form a coherent and unusually complete product (OBSERVED, `startDiscussion`/`runRound`/`queryModel`/`generateConsensus`).
- **Robust degradation & offline behavior.** The app works logged-out with `localStorage` history, and falls back gracefully when the backend is unavailable (OBSERVED, `loadHistory:2868`, `saveState:2817`, `startDiscussion:3742`).
- **Security-conscious framing.** Markdown is sanitized with DOMPurify before injection (OBSERVED, `queryModel:4347`); API keys are described as encrypted server-side and never re-exposed (OBSERVED, tooltips at `index.html:1250`, `1444`).
- **Reasonable dark-first visual language.** The x.ai-inspired near-black + single-orange-accent palette is consistent and modern in intent (OBSERVED, `:root` tokens `index.html:87`).

### Weakest aspects
- **Single-file, inline-everything architecture.** 5,155 lines, **190 inline `style="..."` attributes**, **18 `!important`**, **64 inline `onclick=` handlers** (OBSERVED, counts via grep). This is the single largest maintainability and consistency risk.
- **Broken/contradictory CSS foundations.** The `:root` block opens with login-page/model-card selectors nested *inside* the `:root { ... }` declaration (OBSERVED, `index.html:10–86`) — these rules are effectively invalid where placed. The left provider sidebar has `display: none !important;` immediately followed by `display: flex;` (OBSERVED, `index.html:250–253`), so a whole navigation surface is dead. `--accent-hover` is referenced but never defined (OBSERVED, `index.html:815`).
- **Semantic color collapse.** `--success`, `--error`, `--warning`, `--proceed` are **all set to orange** (OBSERVED, `index.html:101–107`). Success, warning, and error are visually indistinguishable — a real usability and accessibility problem for a status-heavy app.
- **No accessibility layer.** **Zero** `role`, `aria-*`, `tabindex`, or `alt` attributes exist (OBSERVED, grep returned only `<label>` and `for=`). Custom clickable `<div>`s, emoji-only status badges, and no focus-visible styling.
- **No streaming.** Despite the review brief's mention of streaming, the backend proxy returns a single JSON `output` (OBSERVED, `backend/app/api/routes/proxy.py:87,131`) and the frontend does `await response.json()` (OBSERVED, `queryModel:4315`). Long responses appear all-at-once after a full round-trip — poor perceived performance.
- **Sequential model execution, not parallel.** Rounds query models **one at a time with a 1,500 ms stagger** (OBSERVED, `runRound:3872–3874`). For 5 models this serializes latency; the UI implies a "council" but executes a queue.
- **Admin capability exists in the backend but has no UI.** `GET /admin/users` and `DELETE /admin/users/{id}` exist (OBSERVED, `backend/app/api/routes/admin.py:14,38`) with **no frontend surface** (OBSERVED, no "admin" references in `index.html`).

### Biggest opportunities
1. Extract CSS/JS into separate files and introduce a **small design-token system + utility classes** to kill the 190 inline styles without a framework.
2. **Restore semantic status colors** and add a real accessibility layer (roles, focus, contrast) — high value, low risk.
3. **Stream responses** (SSE) and **run models in parallel** — the two changes with the largest perceived- and actual-performance impact.
4. **Consolidate the "New Discussion" setup** into a clearer 3-step flow and surface the hidden admin + provider-health capabilities.

### Overall recommendation
**Do not rewrite.** The application logic is mature and works. Pursue an **incremental, in-place modernization**: split the file, add a token layer + utilities, fix the broken CSS and semantic colors, add accessibility, then invest in streaming + parallelism and a cleaner setup/chat layout. A framework migration (React/Vue) is explicitly **not** recommended at this stage (see §17).

---

## 2. Current Frontend Architecture

| Concern | Finding | Evidence |
|---|---|---|
| **Framework** | None. Vanilla HTML + CSS + JS, single file. | `frontend/index.html` is the entire app (`README.md:42`) |
| **Build tooling** | None. No `package.json`, no bundler, no lockfile in `frontend/`. Served statically by nginx. | Only `frontend/index.html` present; `README.md:93–95` serves via `python -m http.server` |
| **Runtime dependencies** | `marked` (Markdown) and `DOMPurify` (sanitize), both loaded from `cdn.jsdelivr.net` unpinned (no version, no SRI). | `index.html:7–8` |
| **Styling system** | One large inline `<style>` block using CSS custom properties, plus ~190 inline `style="..."` attributes and 18 `!important`. | `index.html:9–1234`; grep counts |
| **Theming** | 3 themes via `[data-theme]`: default dark, `light`, `ps-xai-orange`; toggled and persisted. | `index.html:110,134`; `toggleTheme:2675`, `loadTheme:2686` |
| **Component structure** | No components. HTML built via template strings in JS (`innerHTML`) and static markup. | e.g. `renderRoundTimeline:3826`, `queryModel:4174`, `renderModelSelection:3203` |
| **Routing** | Hash-based single "route" for the active discussion id; tab switching via `switchMainTab`. | `handleHash:4997`, `switchMainTab:2760` |
| **State management** | Module-level `let` globals (`selectedModels`, `discussionData`, `queryHistory`, `authToken`, …) persisted to `localStorage` and optionally synced to backend. | `index.html:1704–1756`, `saveState:2817`, `loadState:2768` |
| **API integration** | `authFetch` wrapper adds bearer token; endpoints: `/api/auth/*`, `/api/providers*`, `/api/discussions*`, `/api/proxy/chat`. | `authFetch:2314`; `README.md:122–134` |
| **Entry points** | `#loginPage` (auth gate), `#appContainer` (main app), `#addProviderModal`, `#debugPanel`. | `index.html:1238,1333,1269,1682` |

### Backend surface relevant to the UI (OBSERVED)
- `backend/app/api/routes/proxy.py` — `POST /api/proxy/chat` returns `ChatResponse(provider, model, output)`; **non-streaming** (`proxy.py:22,87,131`).
- `backend/app/api/routes/discussions.py` — CRUD + `/research` (deep research) endpoints.
- `backend/app/api/routes/providers.py` — save/list creds, discover models.
- `backend/app/api/routes/admin.py` — `list_users`, `delete_user` (**no UI**).
- `backend/app/api/routes/auth.py` — register/login.

---

## 3. Complete Feature Preservation Inventory

> **All of the following are OBSERVED in the code and MUST be preserved through any modernization. No item here may be removed to "simplify" the UI. The redesign changes presentation and structure, never capability.**

### Authentication & session
- [ ] Register user (`registerUser:2554`)
- [ ] Login with username **or** email (`loginUser:2586`, identifier normalization `normalizeAuthIdentifier:2237`)
- [ ] Logout (`logoutUser:2614`)
- [ ] Bearer-token session, header "Logged in as" + logout (`index.html:1338`)
- [ ] Password show/hide toggle (`togglePasswordVisibility:2694`, used at `1253`,`1447`)
- [ ] Works logged-out with local-only history (`loadHistory:2868`)

### Provider configuration (BYOK)
- [ ] Provider presets: OpenRouter, OpenAI, Perplexity, Google Vertex/Gemini, Mammouth, Requesty, Custom (`STATIC_PRESETS:1728`, modal `1279–1286`)
- [ ] Add/configure provider modal with per-preset endpoint, key, auth link (`addProvider:1781`, `saveModalProvider:1929`)
- [ ] Custom provider name field (`modalCustomProviderName:1290`)
- [ ] Google Vertex GCP project + region fields + endpoint templating (`gcpVertexFields:1301`, `onGcpFieldsChange:1799`)
- [ ] OpenRouter OAuth/SSO PKCE sign-in (`startOpenRouterOAuth:5037`, `handleOpenRouterOAuthCallback:5056`, `sha256:5018`)
- [ ] "Login & Get Key" per-provider deep link (`modalWebAuthLink:1320`)
- [ ] Save provider credential (`saveProviderCredential:2469`, `saveActiveSetupProvider:1808`)
- [ ] Reset/delete provider (`resetActiveProvider:2499`)
- [ ] Provider grid selector with active/inactive status dots (`providerGridList:1410`, `renderProviderList:2372`)
- [ ] Select saved provider (`selectSavedProvider:2418`)
- [ ] Inline API config panel (endpoint + key + discover/save/reset) (`apiConfigPanel:1422`)
- [ ] Left provider sidebar + models slide-out panel (present but currently dead via CSS; capability must remain) (`left-panel:1359`, `modelsPanel:1378`)

### Model discovery, health, selection
- [ ] Discover models from provider (`discoverModels:3065`)
- [ ] Free/Paid pricing badges (OpenRouter) (`renderModelSelection:3235`)
- [ ] Background model health check OK/KO/testing (`checkAllModelsHealth:3274`)
- [ ] Retest all models (`retestAllModels:3364`)
- [ ] Model selection grid, 2–5 models, checkbox toggle (`renderModelSelection:3203`, `onCheckboxToggle:3527`)
- [ ] Active ensemble pills w/ per-model remove (`updateActiveEnsembleDisplay:3542`, `removeModelFromEnsemble:3591`)
- [ ] Consensus model dropdown (`updateConsensusDropdown:3435`)
- [ ] Multi-provider composite model ids (`provider::model`) (`normalizeSelectedModels:3409`)

### Discussion / council engine
- [ ] Start discussion with validation (2–5 models, question required) (`startDiscussion:3687`)
- [ ] 2 or 3 rounds (`rounds` select `1537`)
- [ ] Round timeline w/ collapsible rounds (`renderRoundTimeline:3826`, `toggleRound:3851`)
- [ ] Per-model query with timeout + abort (`queryModel:4147`)
- [ ] Round 1 initial positions; round N reviews prior rounds (context assembly `queryModel:4246`)
- [ ] Manual "Proceed to Round N" gating (`showProceedButton:3912`, `proceedToNextRound:3933`)
- [ ] Per-model retry (`retryModel:4424`), skip (`skipModel:4429`), replace-with-different-model dropdown (`getModelReplacementDropdownHtml:3992`, `replaceModelInCard:4081`)
- [ ] Response format presets (default/compact/elaborate) + custom instructions (`applyResponseFormat:3662`, `1511`)
- [ ] Summary/consensus format presets + custom summary instructions (`applySummaryFormat:3672`, `1524`)
- [ ] Timeout (sec) and Max tokens per response controls (`1543`,`1547`)
- [ ] Consensus synthesis (`generateConsensus:4471`)
- [ ] Stop discussion & summarize partial (`stopDiscussion:4664`)
- [ ] Close/reset discussion (`closeAndResetDiscussion:4701`)
- [ ] Card expand / collapse / fullscreen overlay (`toggleExpand:4447`, `toggleFullscreen:4454`)

### RAG / research
- [ ] "Use Live Web Search (RAG)" toggle (`useRagCheckbox:1498`)
- [ ] "Deep Research Mode" (re-search each round) dependent toggle (`deepResearchCheckbox:1502`, `proceedToNextRound:3938`)
- [ ] RAG status indicator + loading shimmer (`ragStatusDisplay:1583`, `setRagLoading:4804`, `updateRagStatusDisplay:4821`)
- [ ] Retrieved-context injection into prompts (`queryModel:4239`)

### Attachments
- [ ] File upload / drag-drop, file list, remove file (`setupFileUpload:2624`, `handleFiles:2640`, `renderFileList:2648`, `removeFile:2656`) — file names injected as prompt context (`queryModel:4274`)

### Stats / analytics
- [ ] Per-model token/latency stats (in/out/ctx%/duration/chars-per-sec) (`renderModelStats:4586`)
- [ ] Per-round aggregate stats badge (`updateRoundHeaderStats:4634`)
- [ ] Whole-discussion aggregate stats + peak-context tracking (`recalculateDiscussionStats:4600`)
- [ ] Progress bar + progress text + progress stats (`updateProgressStats:4655`, `progress-container:1603`)

### History & persistence
- [ ] Discussion history list (server + local) (`loadHistory:2868`, `renderHistory:2944`)
- [ ] Filter: all/completed/running (`filterHistory:3033`)
- [ ] Sort: newest/oldest/A–Z (`historySort:1660`)
- [ ] Keyword + fuzzy search (`fuzzyMatch:2923`)
- [ ] Expand history detail (`toggleHistoryDetail:3042`)
- [ ] View completed / resume in-progress (`loadHistoryView:3057`, `resumeDiscussion:4950`)
- [ ] Copy history summary / query (`copyHistorySummary:3047`, `copyHistoryQuery:4742`)
- [ ] Restore-last-discussion banner (`restoreLastDiscussion:2706`, `dismissRestore:2730`)
- [ ] Load discussion + render rounds from state (`loadDiscussion:4841`, `renderRound:4886`)
- [ ] Hash-based deep link to a discussion (`handleHash:4997`)

### Export / share
- [ ] Export Markdown (`exportMarkdown:4758`), Export JSON (`exportJSON:4779`), Copy to clipboard (`copyToClipboard:4792`)
- [ ] Copy question (`copyQuestion:4736`), unique filename generation (`getUniqueFilename:4750`)

### Diagnostics / admin
- [ ] Debug panel: toggle, level filter (all/error/warn/info), clear (`toggleDebug:4564`, `renderDebugPanel:4569`, `debugLog:2176`)
- [ ] Status message toasts (`showStatus:4797`)
- [ ] **Backend admin: list/delete users** (`admin.py:14,38`) — capability exists; **currently unexposed in UI** (RECOMMENDED to add a surface; must not be lost)

### Global UI
- [ ] Theme toggle + persistence (`toggleTheme:2675`, `loadTheme:2686`) — 3 themes
- [ ] Main tabs: New / Current / History (`main-tabs:1391`)
- [ ] "Current Discussion" tab with live status dot (`updateStatusDot:2663`, `updateMainTabVisibility:2151`)
- [ ] Click-title-to-home (`index.html:1347`)

---

## 4. Current UX and UI Assessment

### Navigation (INFERRED from markup + JS)
Three top tabs (New / Current / History) drive a tab-content swap; the "Current Discussion" tab is hidden until a discussion is active (`updateMainTabVisibility:2151`). A left provider sidebar and a models slide-out panel **exist in markup but are disabled** via `display:none !important` (`left-panel:250`, `modelsPanel:1378`), so provider navigation collapses entirely into the "New Discussion" tab's Step-1 grid. Result: navigation is simple but the "New Discussion" tab carries too much — provider config, model discovery/health, ensemble selection, RAG, formats, timeouts, consensus model, and the question — all stacked vertically (`tab-new:1398`).

### Chat / round view
Rounds render as collapsible accordions containing a responsive `models-grid` (`minmax(320px,1fr)`, `index.html:777`). Each model is a **card** with a name, status badge (emoji), a Markdown-rendered response (max-height 600px, vertically resizable), and expand/fullscreen/retry/skip actions. Cards are click-to-expand to full-row width (`model-card.expanded:68`). This is a solid pattern, but:
- Status is communicated **only** by emoji + border color, and the border colors for `complete`/`incomplete` are both `--border` (i.e., no color) (OBSERVED, `index.html:791–792`).
- Because execution is sequential (`runRound:3872`), only one card is "connecting" at a time; the "council" feels like a queue (INFERRED).
- No streaming, so each card jumps from "Connecting…" to a full answer (OBSERVED, `queryModel:4315,4347`).

### Multi-model comparison
Comparison is implicit — cards sit side by side in a grid, and round N prompts include prior rounds' text (`queryModel:4257`). There is **no explicit diff/side-by-side compare mode**, no way to pin or collapse-all, and no per-model color identity beyond the raw model name string.

### Council workflow (rounds/deliberation)
Strong conceptually: initial positions → review rounds → consensus, with manual proceed gating and deep-research between rounds. But the round semantics ("Initial Positions" vs "Review & Discussion", `renderRoundTimeline:3835`) and the consensus step are not visually explained to a first-time user; discoverability of retry/skip/replace is low (they appear only after a response and are small buttons).

### Configuration
Provider setup is spread across: the Step-1 grid, an inline "Edit" panel, **and** a separate full-screen "Add Provider" modal (`addProviderModal:1269`) that duplicates endpoint/key fields. Two parallel ways to enter the same credentials is confusing (INFERRED). Settings live under an "⚙️ All the Settings" collapsible (`settingsBody:1484`) mixing question text, RAG, formats, rounds, timeout, tokens, and consensus model in one long form.

### Analytics
Token/latency stats are computed and shown per model, per round, and per discussion (`renderModelStats:4586`, `updateRoundHeaderStats:4634`, `updateProgressStats:4655`). There is **no cost estimate** (tokens are estimated as `chars/4`, `queryModel:4355`), and **no dedicated analytics screen** — stats are scattered inline.

### Administration
No UI. Backend `list_users`/`delete_user` are unreachable from the frontend (OBSERVED).

### Mobile / desktop / large screens
- Breakpoints at 1024px and 768px only (OBSERVED, `@media` at `181,207,1180,1192`). Below 768px the layout stacks and grids go single-column.
- Desktop container caps at `max-width:1440px` (`appContainer:1333`) / `1320px` (`.container:176`) — inconsistent max widths.
- No ultrawide strategy; content is centered with large empty side gutters on wide monitors (INFERRED).
- Many fixed pixel font sizes and paddings (e.g., header `34px`/`28px`) rather than fluid/`rem` (OBSERVED).

### Accessibility
- **No ARIA/roles/tabindex/alt anywhere** (OBSERVED). Clickable `<div>`s (`panel-section-title`, model cards, round headers use `<button>` which is good, but many controls are divs with `onclick`).
- Status conveyed by **color + emoji only**; with all semantic colors set to orange, colorblind and screen-reader users cannot distinguish success/warn/error (OBSERVED, `index.html:101–107`).
- No visible focus styles defined; default outlines likely suppressed by resets (INFERRED, `* {}` reset `158`).
- Emoji used as sole meaning carriers (🔗 ✓ ⚠️ ⏱️ ✗) without text alternatives (OBSERVED).

### Error handling
Good coverage in logic: per-model error/timeout states, retry/skip, consensus failure box with diagnostics (`generateConsensus:4550`), round error box (`showRoundStatus:3983`), rollback on failed discovery (`discoverModels:3176`). Presentation is inconsistent (inline styled boxes, emoji, `--error` = orange).

### Loading states
Present: "Connecting…" per card, RAG shimmer bar (`rag-loading-bar:815`), "Generating consensus…", progress bar. But no skeletons, and the shimmer references undefined `--accent-hover` (OBSERVED, `815`).

### Empty states
Minimal: history shows "No discussions yet" (`renderHistory:2949`). No empty states for "no providers configured", "no models discovered yet", or first-run onboarding.

---

## 5. Highest-Priority Problems

| Priority | Problem | Evidence | User Impact | Recommendation | Complexity |
|---|---|---|---|---|---|
| **P0** | Semantic status colors all collapsed to orange (`--success`/`--error`/`--warning`/`--proceed` = `#ff5c00`) | `index.html:101–107` | Users cannot distinguish success vs warning vs error; accessibility failure | Restore distinct green/amber/red semantic tokens (keep orange as brand accent) | Low |
| **P0** | Zero accessibility layer (no `role`/`aria`/`tabindex`/`alt`; status via emoji+color only) | grep: no ARIA matches | Unusable with keyboard/screen readers; WCAG failures | Add roles/labels, focus-visible styles, text alongside status icons, `aria-live` for round status | Medium |
| **P0** | Broken CSS: rules nested inside `:root{}`; dead left sidebar (`display:none!important` then `display:flex`) | `index.html:10–86`, `250–253` | Whole navigation surface dead; unpredictable styling | Fix `:root` block; decide sidebar's fate (restore as real nav) | Low–Med |
| **P1** | No streaming — full round-trip then dump | `proxy.py:131`, `queryModel:4315,4347` | Long waits with no incremental feedback; feels slow | Add SSE streaming end-to-end; render tokens progressively | Medium |
| **P1** | Sequential model execution with 1.5 s stagger | `runRound:3872–3874` | 5-model round latency is additive; "council" feels like a queue | Run models concurrently with a small concurrency cap; keep stagger only for rate-limit safety | Medium |
| **P1** | Single 5,155-line file; 190 inline styles, 18 `!important`, 64 inline `onclick` | grep counts | Very hard to maintain, no consistency guardrails | Split into `index.html` + `styles.css` + `app.js`; introduce tokens + utility classes | Medium |
| **P1** | Duplicate provider-entry paths (Step-1 inline panel + full-screen modal) | `apiConfigPanel:1422`, `addProviderModal:1269` | Confusing; two ways to enter same creds | Consolidate to one provider drawer/modal | Medium |
| **P1** | Unpinned CDN deps without SRI (`marked`, `DOMPurify`) | `index.html:7–8` | Supply-chain risk; breakage if CDN updates | Pin exact versions + `integrity`/SRI, or self-host | Low |
| **P2** | Admin (list/delete users) unreachable from UI | `admin.py:14,38`; no UI refs | Admins cannot manage users in-app | Add gated Admin view | Medium |
| **P2** | Setup tab overloaded (provider+models+health+RAG+formats+timeouts+consensus+question stacked) | `tab-new:1398–1565` | Cognitive overload; poor first-run discoverability | Progressive 3-step layout with clear hierarchy | Medium |
| **P2** | No cost estimation; tokens estimated as chars/4 | `queryModel:4355` | Users flying blind on spend | Use real usage from provider responses; show cost estimate | Medium |
| **P2** | Only 2 real breakpoints; fixed px sizing; two different max-widths | `@media`; `1333` vs `176` | Inconsistent responsive behavior; weak tablet/ultrawide | Fluid type/space scale; unify container width | Medium |
| **P2** | Global mutable state + `innerHTML` template rebuilds | `1704–1756`; `renderHistory`, `queryModel` | Fragile, re-render churn, XSS surface if sanitization slips | Encapsulate state; render via safe DOM builders; keep DOMPurify | Med–High |
| **P3** | Emoji-driven iconography throughout | pervasive | Inconsistent rendering across OS; not scalable | Adopt a small inline SVG icon set | Low–Med |
| **P3** | No skeletons/empty states for providers/models/first-run | `renderHistory:2949` only | New users see blank areas | Add empty + skeleton states | Low |
| **P3** | Double-calls & dead code (`updateStatusDot()` twice, `closeDiscussionSummary()` twice) | `3805–3806`, `4732–4733` | Minor churn/confusion | Clean up during refactor | Low |

---

## 6. Proposed Design Direction

A **calm, dense, keyboard-friendly "operator console"** for running AI councils — not a flashy marketing dashboard. Keep the dark-first, single-accent identity but make it structurally sound and semantically honest.

- **Layout philosophy:** Persistent left rail (icon+label nav) → main work area → optional right context drawer (stats/diagnostics). Reuse the already-present-but-dead left panel concept as the real nav. Content max-width unified (e.g., 1440px work area; discussion grids allowed to breathe wider).
- **Navigation:** Left rail: New / Current / History / Providers / Analytics / (Admin, gated). Top bar keeps brand, user, theme, and a global "New discussion" action. This surfaces Providers, Analytics, and Admin without adding features — it only *organizes* existing ones.
- **Typography:** One family (system stack is fine). A `rem`-based type scale: 12 / 13 / 14 / 16 / 20 / 28. Body 14px/1.5. Monospace only for stats and code.
- **Spacing:** 4px base scale: 4, 8, 12, 16, 24, 32. Replace ad-hoc px paddings with scale tokens/utilities.
- **Color usage:** Brand orange for primary actions and focus accents only. **Restore semantic greens/ambers/reds** for status. Neutral grays for surfaces. Keep 3 themes.
- **Surfaces:** Two elevation levels max (`bg-secondary` cards on `bg-primary`). Kill decorative shadows on wide areas; keep subtle 1px borders (`--border`).
- **Borders/radii:** Unify radius to a 2-step scale (6px controls, 10px cards/modals). Currently mixes 3/4/6/8/12px.
- **Cards:** Model cards keep expand/fullscreen but gain a colored left status accent, a provider chip, and a compact stats footer.
- **Dialogs:** One modal pattern (focus-trapped, ESC to close, `role="dialog"`), reused for Add Provider and any confirmations.
- **Forms:** Consistent input component (label above, help text below, error state). Group advanced settings under labeled disclosure sections, not one giant "All the Settings".
- **Tables:** For History and Analytics — dense, sortable, sticky header, zebra optional.
- **Charts:** Only if Analytics warrants it; prefer lightweight inline SVG bars over a charting library (see §14).
- **Code blocks:** Keep current styling; add a copy button and optional soft-wrap toggle. Defer syntax highlighting unless justified (§11).
- **Chat messages / model responses:** Provider chip + model name + status pill (icon **and** text) + timing. Streaming text with a caret while active.
- **Tool calls:** N/A today (no tool-calling observed) — reserve a compact "activity" row pattern for future.
- **Status indicators:** Pill = icon + text + semantic color. Never color-only.
- **Responsive:** Rail collapses to icons on tablet, to a bottom bar / hamburger on mobile. Grids reflow 1→2→N columns.

---

## 7. Screen-by-Screen Recommendations

### 7.1 Login (`#loginPage`, `index.html:1238`)
- **Purpose:** Auth gate (login/register), reassurance about key security.
- **Problems:** Centered card is fine; no error focus management; password toggle is an unlabeled emoji button; no `aria-live` for `#loginStatusMsg`.
- **Improvements:** Label the toggle (`aria-label`), move focus to first invalid field, `role="alert"` on status, `autocomplete` already present (good). Add subtle first-run copy ("Bring your own API keys").
- **Must remain:** Register, login-by-username-or-email, password visibility, security note.
- **Priority:** P2 · **Files:** `index.html:1238–1266`, `loginUser:2586`, `registerUser:2554`.

### 7.2 New Discussion setup (`#tab-new`, `index.html:1398`)
- **Purpose:** Configure provider → select models → set question & options → start.
- **Problems:** Everything stacked; two provider-entry paths; "All the Settings" mega-form; dead left sidebar duplicates provider selection.
- **Improvements:** Reframe as 3 clear steps with sticky progress: **1) Provider & Models** (grid + discover + health), **2) Question & Research** (question, RAG, deep research, attachments), **3) Council Settings** (rounds, timeout, tokens, formats, consensus model) in a labeled disclosure. Single provider entry via one drawer. Add empty states ("No provider yet — add one").
- **Must remain:** Every control listed in §3 (providers, discovery, health, ensemble, RAG/deep-research, formats, rounds, timeout, tokens, consensus model, attachments, start).
- **Priority:** P2 · **Files:** `1398–1565`, `discoverModels:3065`, `renderModelSelection:3203`, `startDiscussion:3687`.

### 7.3 Add Provider modal (`#addProviderModal`, `index.html:1269`)
- **Purpose:** Configure a provider preset (endpoint, key, Vertex/OAuth specifics).
- **Problems:** Duplicates inline config; not focus-trapped; not `role="dialog"`; overlay not ESC-dismissible.
- **Improvements:** Make this the *single* provider-entry surface; add focus trap, ESC, `aria-modal`. Keep per-preset conditional fields (custom name, GCP, OAuth, auth link).
- **Must remain:** All 7 presets, custom name, GCP project/region, OAuth SSO, "Login & Get Key", save & discover.
- **Priority:** P1 · **Files:** `1269–1330`, `saveModalProvider:1929`, `onModalProviderChange:1888`.

### 7.4 Current Discussion (`#tab-current`, `index.html:1570`)
- **Purpose:** Live council run — status, question, models, rounds, consensus, export, controls.
- **Problems:** Non-color status; sequential feel; consensus/summary/export sections all stacked; controls at bottom only.
- **Improvements:** Sticky run header (round X of N, live counts, stop). Model cards stream; parallel connecting states. Consensus as a distinct, clearly-labeled "Final Synthesis" panel. Persistent export/stop controls. Right drawer for token/latency/RAG diagnostics.
- **Must remain:** Round timeline + collapse, per-card expand/fullscreen/retry/skip/replace, RAG status, progress + stats, consensus, discussion summary, export (MD/JSON/copy), stop & summarize, close.
- **Priority:** P1 · **Files:** `1570–1648`, `runRound:3860`, `queryModel:4147`, `generateConsensus:4471`.

### 7.5 History (`#tab-history`, `index.html:1649`)
- **Purpose:** Browse/search/resume past discussions.
- **Problems:** Filter buttons hand-styled inconsistently; list is compact but not scannable (no status pills, no model chips, no token totals at a glance).
- **Improvements:** Convert to a dense table/list with status pill, date, model count, token total, and quick actions (view/resume/copy/export). Keep fuzzy search, filters, sort.
- **Must remain:** all/completed/running filter, sort, keyword+fuzzy search, expand detail, view/resume, copy summary/query.
- **Priority:** P2 · **Files:** `1649–1675`, `renderHistory:2944`, `filterHistory:3033`.

### 7.6 Debug panel (`#debugPanel`, `index.html:1682`)
- **Purpose:** Diagnostics log with level filter.
- **Problems:** Fine functionally; visually detached; not keyboard reachable clearly.
- **Improvements:** Dock as a right-drawer tab alongside stats; keep level filter + clear; add copy-all.
- **Must remain:** toggle, level filter (all/error/warn/info), clear.
- **Priority:** P3 · **Files:** `1682–1696`, `renderDebugPanel:4569`.

### 7.7 Providers view (RECOMMENDED — surfaces existing capability)
- **Purpose:** Manage all saved providers, their status dots, discovered models, health.
- **Rationale:** The provider sidebar exists but is dead (`left-panel:250`); provider management is buried in setup. A dedicated view organizes existing `renderProviderList`, `selectSavedProvider`, `resetActiveProvider`, `discoverModels`, `checkAllModelsHealth`.
- **Must remain:** add/select/reset provider, discover, health, OAuth.
- **Priority:** P2.

### 7.8 Analytics view (RECOMMENDED — organizes existing stats)
- **Purpose:** Aggregate token/latency across discussions; per-model comparison.
- **Rationale:** Stats already computed (`recalculateDiscussionStats:4600`) but scattered. Add cost estimate here.
- **Priority:** P2/P3.

### 7.9 Admin view (RECOMMENDED — exposes backend admin)
- **Purpose:** List/delete users (gated to admin).
- **Rationale:** `admin.py:14,38` unreachable today.
- **Priority:** P2.

---

## 8. Chat and AI Council UX (Deep Review)

**Observed flow:** `startDiscussion` → optional RAG fetch → `runRound(1)` → sequential `queryModel` per model (1.5 s stagger) → manual "Proceed" → `runRound(2..N)` (round N includes prior rounds in prompt) → `generateConsensus` → completed. Retry/skip/replace available per card; stop-and-summarize any time.

### Normal chat
There is no "single-model chat" mode; the minimum is a 2-model council. **RECOMMENDED:** keep the council as the core, but the same card+stream pattern trivially supports a 1-model quick-ask mode later (do not remove council).

### Parallel model responses
- **OBSERVED:** Not parallel. `runRound` awaits each `queryModel` in series with `setTimeout(1500)` between (`3872–3874`).
- **RECOMMENDED:** Fire models concurrently with a configurable concurrency cap (e.g., 3) and keep a small jitter/stagger for rate-limit safety. Show all cards in "connecting" simultaneously. This is the single biggest actual-latency win.

### Multi-model discussions / rounds
- Round headers label "Initial Positions" vs "Review & Discussion" (`3835`) — good, but users don't see *why* round 2 differs. **RECOMMENDED:** a one-line explainer per round and a visual indicator that round N reads round N-1.
- Manual proceed gating is a strength for cost control — **keep it**, but also offer an "auto-proceed" toggle.

### Model comparison / expand-collapse
- **OBSERVED:** cards expand to full width (`model-card.expanded:68`), fullscreen overlay (`toggleFullscreen:4454`).
- **RECOMMENDED:** add "expand all / collapse all", and a side-by-side "compare 2" mode reusing existing cards. Give each model a stable color/chip for cross-round tracking.

### Tool activity
- None today. Reserve a compact activity-row pattern; do not build speculative UI.

### Streaming
- **OBSERVED:** none (§5). **RECOMMENDED (P1):** SSE from `/api/proxy/chat` → append tokens to the card's response element; show a blinking caret and live char/s. Preserve the existing truncation heuristic (`queryModel:4330`) as a post-stream check.

### Failures / retries / fallbacks
- **OBSERVED:** per-model error/timeout with retry/skip/replace; round error box; consensus failure diagnostics (`generateConsensus:4550`). Strong.
- **RECOMMENDED:** unify into semantic-colored pills; add "retry all failed" bulk action; surface provider-health hints ("model marked KO earlier").

### Final synthesis
- **OBSERVED:** `generateConsensus` renders sanitized Markdown, flags truncation (`4542`). Good.
- **RECOMMENDED:** label it clearly as "Final Synthesis / Consensus", show which consensus model produced it, and make it visually distinct (accent border already present, keep it).

### Long conversations
- **OBSERVED:** all rounds render into the DOM; each response max-height 600px scroll (`817`). For 3 rounds × 5 models × long Markdown, DOM grows large; round N prompt concatenates *all* prior text (`queryModel:4257`), which is correct but token-heavy.
- **RECOMMENDED:** collapse completed rounds by default (only current expanded); virtualize only if a real perf issue is measured (§11 — only-if-needed).

---

## 9. Navigation and Information Architecture

**Goal: reorganize, never remove.** Proposed left-rail IA that maps every existing capability to a home:

- **New** → §7.2 setup (3 steps).
- **Current** → §7.4 live run (only visible when active, as today).
- **History** → §7.5.
- **Providers** → §7.7 (moves provider add/select/reset/discover/health out of the setup tab into a dedicated, always-available home — but setup still offers quick inline selection).
- **Analytics** → §7.8 (aggregates existing stats + cost).
- **Admin** → §7.9 (gated; exposes existing backend admin).
- **Top bar** → brand/home, "Logged in as / Logout", theme toggle, global "New discussion" button.
- **Right drawer (contextual)** → Diagnostics (debug log) + Run stats; open on demand.

This uses **progressive disclosure** (advanced settings in labeled sections), **contextual controls** (right drawer), and **tabs/rail** to reduce the current single-tab overload without hiding anything essential.

---

## 10. Design System Recommendation (lightweight)

Introduce a small token layer at `:root` (fixing the current broken block) and a thin utility-class set. **No framework, no CSS-in-JS.**

```
/* Spacing (4px base) */         --sp-1:4px --sp-2:8px --sp-3:12px --sp-4:16px --sp-6:24px --sp-8:32px
/* Radii */                      --r-sm:6px --r-md:10px --r-full:9999px
/* Type scale (rem) */           --fs-xs:.75rem --fs-sm:.8125rem --fs-md:.875rem --fs-base:1rem --fs-lg:1.25rem --fs-xl:1.75rem
/* Borders */                    --border, --border-hover (keep)
/* Elevation (2 levels) */       --shadow-1, --shadow-2
/* Brand */                      --accent, --accent-light, --accent-dark (keep)
/* Semantic (RESTORE distinct) */
  --success:#22c55e  --success-bg:rgba(34,197,94,.12)
  --warning:#f59e0b  --warning-bg:rgba(245,158,11,.12)
  --error:#ef4444    --error-bg:rgba(239,68,68,.12)
  --info:#3b82f6
/* Interaction states */         hover/active/disabled tokens per surface
/* Focus */                      --focus-ring:0 0 0 2px var(--bg-primary),0 0 0 4px var(--accent)
/* Density */                    optional [data-density="compact"] tightening paddings
```

- Add a global `:focus-visible { box-shadow: var(--focus-ring); }`.
- Utility classes: `.stack-*`, `.row`, `.muted`, `.pill`, `.pill--success/-warning/-error`, `.btn`, `.btn--primary/-secondary/-ghost`, `.card`, `.input`, `.help`. These replace the 190 inline styles incrementally.
- **Density mode** justified: this is an information-dense operator tool; offer compact/comfortable toggle persisted like theme.

---

## 11. Performance Recommendations

### Immediate wins (low risk)
- **Pin CDN deps + SRI** or self-host `marked`/`DOMPurify` (`index.html:7–8`) — avoids surprise breakage and enables caching.
- **Collapse completed rounds by default** to shrink live DOM (`renderRoundTimeline` currently expands round 1; keep only current expanded).
- **Debounce history search** (`historySearch` `oninput="renderHistory()"`, `1669`) — currently re-renders the entire list on every keystroke (`renderHistory:2944`).
- **Batch stat recomputation** — `recalculateDiscussionStats` iterates all rounds/models on every model completion (`4600`); fine now, but debounce during bursts.

### Medium-term
- **Streaming (SSE)** — biggest perceived-perf win (§8).
- **Parallel model execution with concurrency cap** — biggest actual-perf win (`runRound:3872`).
- **Split file** so CSS/JS can be cached separately and minified; removes re-parse cost of a 5,155-line document.
- **Replace `innerHTML` rebuilds** in hot paths (`renderModelSelection`, `renderHistory`) with targeted DOM updates to avoid full re-render churn.

### Only-if-needed (measure first)
- **List virtualization** for History or very long round grids — only if a large dataset is measured as slow.
- **Syntax highlighting** for code blocks — nice, but adds a dependency (highlight.js ~large). Defer unless users request it.
- **Web worker** for Markdown parsing of very large responses — only if main-thread jank is observed during streaming.

---

## 12. Accessibility Recommendations

- **Keyboard:** ensure every interactive element is a real `<button>`/`<a>`/input or has `role`+`tabindex`+key handlers. Round headers already use `<button>` (good, `3834`); model cards and `panel-section-title` use div `onclick` — convert or add roles.
- **Focus:** add global `:focus-visible` ring (§10); trap focus in modals (`addProviderModal`, fullscreen overlay); return focus on close.
- **Contrast:** verify text on `--bg-tertiary`; `--text-tertiary:#52525b` on dark may fail 4.5:1 for body text — reserve for large/decorative only.
- **Semantics:** add `role="dialog"`+`aria-modal`+labelled title to modals; `aria-live="polite"` to `#roundStatusInfo`/`#progressText`/`#statusMsg`; `role="alert"` to error boxes.
- **ARIA:** label icon-only buttons (theme toggle, password eye, close `×`, retest 🔄, debug 🐛). Give status badges text + `aria-label` (e.g., "Complete", "Error").
- **Reduced motion:** wrap pulse/shimmer/transform animations in `@media (prefers-reduced-motion: reduce)` (currently `pulse`, `ragShimmer`, card `translateY` always animate — `811,814,64`).
- **Screen readers:** don't rely on emoji as sole meaning; add visually-hidden text.
- **Forms:** every input has a `<label for>` already (good, §2). Add error association via `aria-describedby`.
- **Tables (History/Analytics):** use real `<table>` with `<th scope>`.
- **Charts:** provide text/table equivalents.

---

## 13. Responsive Design Strategy

- **Mobile (<640px):** left rail → bottom tab bar or hamburger drawer; single-column model grid (already, `1230`); sticky run header; larger tap targets (≥44px). Ensure the Add Provider modal scrolls.
- **Tablet (640–1024px):** rail collapses to icons; 2-column model grid; setup steps remain vertical.
- **Laptop (1024–1440px):** full rail + work area; model grid `auto-fit minmax(320px,1fr)` (keep).
- **Desktop (1440–1920px):** unify max width; allow discussion grid to use more columns; right drawer docked.
- **Ultrawide (>1920px):** cap the reading column for consensus/synthesis text, but let the model grid expand to more columns instead of leaving huge empty gutters. Consider a max content width with centered layout + optional 3-pane (nav / work / diagnostics).
- Introduce breakpoints at ~640 and ~1440 (currently only 768/1024). Use `rem` + `clamp()` for fluid type.

---

## 14. Dependency Assessment

**Default stance: add no new runtime dependency unless clearly justified.**

| Candidate | Reason it might be added | Benefit | Cost / bundle | Maintenance risk | Can existing code solve it? | Verdict |
|---|---|---|---|---|---|---|
| Pin/self-host `marked` + `DOMPurify` (already used) | Supply-chain safety | Reproducible, SRI, cacheable | ~0 (already loaded) | Low | N/A | **Do it** (pin + SRI or vendor locally) |
| Icon set (inline SVG, e.g. Lucide subset) | Replace inconsistent emoji | Consistent, scalable, a11y-labelable | Copy only used SVGs (~few KB) | Low | Partially (hand-draw) | **Optional, low priority** — inline a small SVG subset, no npm dep |
| Syntax highlighter (highlight.js/Prism) | Code block coloring | Nicer code | +large JS/CSS | Medium | Basic `<pre><code>` already styled | **Defer** — only if requested |
| Charting lib (Chart.js/uPlot) | Analytics charts | Rich charts | +JS | Medium | Inline SVG bars suffice for token/latency | **Avoid** — use inline SVG |
| Framework (React/Vue/Svelte) | Componentization | DX, reactivity | Build pipeline, large shift, regression risk | High | Yes — utilities + DOM builders | **Avoid now** (see §17) |
| Animation lib (Framer/GSAP) | Motion | Polish | +JS | Medium | CSS transitions already present | **Avoid** |
| State lib (Redux/Zustand) | State mgmt | Structure | +JS + framework | High | Module + small store object | **Avoid** |

**Net new required dependencies: 0.** Only *pin/vendor* the two you already use.

---

## 15. Implementation Roadmap

> Each phase is independently shippable and reversible. Preserve every §3 feature at every step.

### Phase 0 — Safety & baseline
- **Scope:** Capture screenshots of all screens/states (login, setup, live run at each round, consensus, history, debug, modal, both themes). Record the §3 inventory as an automated smoke checklist. Note current bundle/DOM metrics.
- **Benefit:** Regression baseline; enables confident refactor.
- **Risk:** None (read-only).
- **Areas:** whole app.
- **Validation:** Screenshot diff set + feature checklist committed to `docs/`.

### Phase 1 — Foundations & consistency
- **Scope:** Fix broken `:root` block (`10–86`); restore semantic colors (`101–107`); define missing `--accent-hover`; add token layer + `:focus-visible` + reduced-motion; pin/vendor CDN deps + SRI. **No layout change.**
- **Benefit:** Correct styling, distinguishable status, safer deps.
- **Risk:** Low (visual only).
- **Areas:** `<style>`, `<head>`.
- **Validation:** Visual diff vs Phase 0; verify status colors differ; a11y contrast spot-check.

### Phase 2 — Structure & navigation
- **Scope:** Split into `index.html` + `styles.css` + `app.js`; introduce utility classes and begin replacing inline styles; decide the left-rail IA (§9); resolve the dead sidebar; consolidate provider entry to one surface.
- **Benefit:** Maintainability; discoverability of Providers/Analytics/Admin.
- **Risk:** Medium (event wiring while moving inline `onclick`).
- **Areas:** file structure, nav, provider config.
- **Validation:** Full §3 checklist; keyboard tab-order pass.

### Phase 3 — Core chat & council experience
- **Scope:** Parallel model execution w/ concurrency cap; SSE streaming; model status pills (icon+text+color); provider chips; expand/collapse-all; consensus relabeled "Final Synthesis"; right diagnostics drawer.
- **Benefit:** Faster, clearer, modern council UX.
- **Risk:** Medium–High (touches proxy + `queryModel`/`runRound`). Backend SSE change required (`proxy.py`).
- **Areas:** `runRound`, `queryModel`, `generateConsensus`, proxy route.
- **Validation:** Timing comparison vs baseline; failure/retry/skip/replace still work; truncation heuristic intact.

### Phase 4 — Configuration & analytics surfaces
- **Scope:** Providers view; Analytics view (aggregate stats + cost estimate from real usage); Admin view (list/delete users); History as dense table.
- **Benefit:** Surfaces hidden capability; better daily use.
- **Risk:** Medium.
- **Areas:** new views, `admin.py` wiring, `renderHistory`.
- **Validation:** Admin gated correctly; analytics matches per-run stats.

### Phase 5 — Performance & accessibility
- **Scope:** Debounce search; targeted DOM updates in hot paths; collapse-completed-rounds; full ARIA/roles/focus-trap/aria-live; reduced-motion; table semantics.
- **Benefit:** Snappier, WCAG-aligned.
- **Risk:** Low–Medium.
- **Areas:** render functions, modals, status regions.
- **Validation:** Keyboard-only run-through; screen-reader smoke; Lighthouse a11y.

### Phase 6 — Polish
- **Scope:** Icon set (inline SVG), skeletons/empty states, density toggle, ultrawide 3-pane, micro-interactions (respecting reduced-motion).
- **Benefit:** Finished, premium feel.
- **Risk:** Low.
- **Areas:** global.
- **Validation:** Visual QA across breakpoints/themes.

---

## 16. Quick Wins (low risk, high value, small effort)

1. **Restore semantic status colors** (`index.html:101–107`) — green/amber/red distinct from brand orange.
2. **Fix the `:root` block** so nested login/model-card rules are moved out (`10–86`).
3. **Define `--accent-hover`** (referenced at `815`) so the RAG shimmer renders correctly.
4. **Pin CDN versions + add SRI** to `marked`/`DOMPurify` (`7–8`).
5. **Add `:focus-visible` outline + `prefers-reduced-motion` guard** (global).
6. **Label icon-only buttons** (theme toggle `1352`, password eye `1253/1447`, modal close `1273`, retest `1463`, debug `1681`) with `aria-label`.
7. **Add text to status badges** (not emoji-only) in `queryModel` badge updates (`4344,4402`).
8. **Debounce `renderHistory`** on search input (`1669`).
9. **Remove obvious dead/double calls** (`updateStatusDot()` twice `3805`, `closeDiscussionSummary()` twice `4732`).
10. **Collapse completed rounds by default** in `renderRoundTimeline` to reduce DOM/visual noise.

---

## 17. Things Not To Do

- **Do not migrate to a SPA framework** (React/Vue/Svelte) as step one. The logic is mature; a rewrite risks losing the many subtle behaviors in §3 (rollback on discovery failure, composite `provider::model` handling, resume/restore, truncation heuristics). Modernize in place first.
- **Do not remove any feature** to "simplify" — no dropping retry/skip/replace, deep research, debug panel, exports, health checks, OAuth, or Vertex fields.
- **Do not hide provider/model controls** behind obscure gestures that harm discoverability; use labeled disclosure instead.
- **Do not add a charting or animation library** for decoration; inline SVG + CSS transitions suffice.
- **Do not introduce a state-management library** for a single-user, single-view console.
- **Do not over-glassmorphize / over-gradient / oversize cards** — this is a dense operator tool, not a landing page.
- **Do not keep unpinned CDN scripts** in production (supply-chain risk).
- **Do not rely on color or emoji alone** for status (accessibility regression).
- **Do not unify all semantic colors to one hue** (the current root cause of the status-legibility problem).

---

## 18. Final Recommended Target State

AI Ensemble should feel like a **fast, focused AI operations console**. On login, a persistent left rail exposes New / Current / History / Providers / Analytics / (Admin). Starting a council is a clean three-step flow — pick provider & models (with live health and free/paid badges), write the question and choose research depth, then confirm council settings behind a tidy disclosure. Pressing **Start** fires all models **in parallel**, and their answers **stream in simultaneously** into a responsive grid of cards, each with a provider chip, a clear icon-plus-text status pill in honest semantic colors, and a compact stats footer (tokens, latency, ctx%). Rounds are explained inline; the user decides when to proceed (or opts into auto-proceed). The **Final Synthesis** stands out as the destination, attributed to its consensus model. A right-hand drawer offers diagnostics and run stats without cluttering the main view. Everything is keyboard-navigable, screen-reader-labeled, respects reduced motion, and adapts from phone to ultrawide. Under the hood it is plain HTML/CSS/JS — now split into cached files with a small token system and utility classes — so it stays **fast to load, easy to maintain, and consistent**, with **zero features lost** relative to today.

---

## 19. Top 10 Recommendations (ranked)

1. **Restore distinct semantic status colors** (green/amber/red) separate from brand orange. *Evidence:* `index.html:101–107` sets success/error/warning/proceed all to `#ff5c00`. *Impact:* fixes the most damaging usability/a11y defect. *(P0, quick win)*
2. **Add a real accessibility layer** — roles, `aria-label`s on icon buttons, `aria-live` status, focus-visible, focus-trapped modals, reduced-motion. *Evidence:* zero ARIA/roles found; `pulse`/`ragShimmer` always animate (`811,814`). *(P0)*
3. **Fix broken CSS foundations** — un-nest rules from `:root{}` (`10–86`), define `--accent-hover` (`815`), resolve the dead left sidebar (`250–253`). *(P0)*
4. **Split the single 5,155-line file** into `index.html` + `styles.css` + `app.js` and introduce a token layer + utility classes to retire the 190 inline styles / 18 `!important` / 64 inline `onclick`. *Evidence:* grep counts. *(P1)*
5. **Stream responses via SSE** end-to-end. *Evidence:* `proxy.py:131` returns single `output`; `queryModel:4315` awaits full JSON. *Impact:* largest perceived-performance gain. *(P1)*
6. **Execute models in parallel** with a concurrency cap. *Evidence:* `runRound:3872–3874` runs serially with a 1.5 s stagger. *Impact:* largest actual-latency gain. *(P1)*
7. **Consolidate provider entry** into one drawer/modal and add a dedicated **Providers** view. *Evidence:* duplicate paths `apiConfigPanel:1422` vs `addProviderModal:1269`; dead `left-panel:250`. *(P1/P2)*
8. **Pin & SRI (or vendor) the CDN deps.** *Evidence:* unpinned `marked`/`DOMPurify` at `index.html:7–8`. *(P1, quick win)*
9. **Introduce a left-rail IA** that surfaces existing-but-hidden capability — Providers, Analytics (with cost estimate), and the unexposed **Admin** (`admin.py:14,38`) — without removing anything. *(P2)*
10. **Reframe the New Discussion setup** into a clear 3-step flow with progressive disclosure, and add empty/skeleton states. *Evidence:* overloaded `tab-new:1398–1565`; only "No discussions yet" empty state (`renderHistory:2949`). *(P2)*

---

*End of review. No application source was modified; this document is the sole deliverable.*
