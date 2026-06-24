# Production Readiness Action Plan

**Start Date:** 2024-06-24  
**Goal:** Make AI Ensemble production-ready  
**Timeline:** 2–4 weeks (depending on resources)

---

## Phase 1: Critical Security Fixes (Week 1, ~8 hours)

**Goal:** Eliminate CRITICAL vulnerabilities before any user-facing deployment.

### Task 1.1: Remove API Key Storage ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Remove `apiKey: storedApiKey` from `saveState()` function (line 654)
  - [ ] Update `loadState()` to NOT restore API key (line 614–615)
  - [ ] Clear API key from `discussionData` before saving (lines 814–827)
  - [ ] Add user warning in UI: "API key not saved for security"
  - [ ] Test: Refresh page mid-discussion, verify API key is empty
  - [ ] Update documentation: "API keys reset on refresh"

**Files to modify:**
- `ai-ensemble-v5.html` (lines 608–683 in `loadState()` and `saveState()`)

**PR checklist:**
- [ ] No API key in any localStorage key
- [ ] Warning message clear to user
- [ ] Tested on browser with DevTools

---

### Task 1.2: Fix XSS via Unescaped Markdown ✓
- **Time:** 2 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Add DOMPurify to CDN in `<head>` (line 7)
  - [ ] Create `renderMarkdown()` helper function
  - [ ] Audit ALL `.innerHTML = marked.parse(...)` calls:
    - Line 1094: `responseElement.innerHTML = marked.parse(fullText)`
    - Line 643: `document.getElementById('consensusText').innerHTML = marked.parse(...)`
    - Line 1182: Similar in consensus generation
  - [ ] Replace with sanitized version
  - [ ] Test with malicious payloads: `<img src=x onerror="alert(1)">`
  - [ ] Test with normal markdown: bold, italic, links, code blocks

**Files to modify:**
- `ai-ensemble-v5.html` (head section + script section)

**PR checklist:**
- [ ] DOMPurify loaded from CDN
- [ ] No unescaped `marked.parse()` remains
- [ ] Tested with XSS payloads
- [ ] Normal markdown still renders correctly

---

### Task 1.3: Fix Silent Error Swallowing ✓
- **Time:** 2 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Replace bare `} catch (e) {}` at line 1076
  - [ ] Implement `isRetryableError()` helper
  - [ ] Add retry logic wrapper: `queryModelWithRetry()`
  - [ ] Track retry attempts in UI (show "Attempt 2/3")
  - [ ] Log all errors with context (model, round, error type)
  - [ ] Test: Break network mid-request, verify retry happens
  - [ ] Test: Timeout on one model, verify others continue
  - [ ] Test: All models fail, verify user sees errors (not blank)

**Files to modify:**
- `ai-ensemble-v5.html` (queryModel section, runRound section)

**PR checklist:**
- [ ] No silent error catches remain
- [ ] Retry logic tested with network throttling
- [ ] User sees retry progress
- [ ] Failed models show descriptive errors

---

### Task 1.4: Add Input Validation ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Create `validateInputs()` function
  - [ ] Validate endpoint URL (http/https, valid format)
  - [ ] Validate API key length (min 10 chars)
  - [ ] Validate question (5–5000 chars)
  - [ ] Validate timeout (5–600 seconds)
  - [ ] Validate rounds (1–5)
  - [ ] Validate model count (2–5)
  - [ ] Call validation before `startDiscussion()`
  - [ ] Show all validation errors to user (not just first)
  - [ ] Test with edge cases: empty, very long, special chars

**Files to modify:**
- `ai-ensemble-v5.html` (startDiscussion section)

**PR checklist:**
- [ ] No invalid inputs reach API
- [ ] All error messages clear and specific
- [ ] Edge cases tested (empty, max length, negative timeout, etc.)

---

**Phase 1 Verification (before moving to Phase 2):**
```bash
# Test checklist:
- [ ] Run on local machine with DevTools open
- [ ] Try starting discussion, refresh mid-way, verify:
  - API key is gone
  - Can resume discussion WITHOUT re-entering key? (NO, expect error or prompt)
  - Error messages are clear
- [ ] Try with malicious question: "<img src=x onerror=alert('xss')>"
  - Verify it renders as text, not executed
- [ ] Network throttle in DevTools to 'Slow 3G'
  - Trigger timeout, verify retry happens (3 times)
  - Verify user sees progress "Attempt 2/3"
- [ ] Try entering invalid inputs:
  - Endpoint: "not a url" → should show error
  - Timeout: "999" → should clamp/error
  - Question: "" → should error
```

---

## Phase 2: Error Handling & Observability (Week 2, ~6 hours)

**Goal:** Make failures visible and debuggable.

### Task 2.1: Implement Structured Logging ✓
- **Time:** 2 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Create `Logger` class with levels (info, warn, error)
  - [ ] Store logs in memory (max 500 entries)
  - [ ] Add "Download Logs" button for users to share
  - [ ] Replace all `console.log()` with `Logger.info()`
  - [ ] Replace all error catches with `Logger.error()`
  - [ ] Add metadata to logs (modelId, roundNum, endpoint, etc.)
  - [ ] Test: Create discussion, download logs, verify structure
  - [ ] Test: Error occurs, check logs include full context

**Files to modify:**
- `ai-ensemble-v5.html` (top of script, all log calls)

**PR checklist:**
- [ ] Logger class implemented
- [ ] All `console.log()` calls use Logger
- [ ] Download logs button works and produces valid JSON
- [ ] Logs include timestamp, level, message, metadata

---

### Task 2.2: Add Network Stall Detection ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Add stall timer (15 seconds no data)
  - [ ] Reset stall timer on each data chunk
  - [ ] Abort request if stall detected
  - [ ] Show user: "⚠️ Connection stalled"
  - [ ] Allow retry (user clicks "Retry" button)
  - [ ] Test: Throttle network to very slow (DevTools)
  - [ ] Verify stall is detected after 15s

**Files to modify:**
- `ai-ensemble-v5.html` (queryModel function)

**PR checklist:**
- [ ] Stall timer works (test with slow network)
- [ ] User sees "Connection stalled" message
- [ ] Can retry after stall

---

### Task 2.3: CORS Error Handling ✓
- **Time:** 1 hour
- **Owner:** (You)
- **Checklist:**
  - [ ] Detect CORS errors (response.type === 'opaque')
  - [ ] Detect network errors (TypeError with "Failed to fetch")
  - [ ] Show helpful error messages (not just "Error")
  - [ ] Suggest fixes in error message (e.g., "Ask API provider to allow this domain")
  - [ ] Test: Try with non-existent domain → should get helpful error

**Files to modify:**
- `ai-ensemble-v5.html` (discoverModels, queryModel functions)

**PR checklist:**
- [ ] CORS errors show helpful message
- [ ] Network unreachable shows different message than CORS
- [ ] User knows how to fix (or who to ask)

---

### Task 2.4: localStorage Quota Handling ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Wrap `localStorage.setItem()` in try-catch
  - [ ] Detect `QuotaExceededError`
  - [ ] Show user: "Storage quota full. Clear cache or delete old discussions."
  - [ ] Implement `pruneHistory()` to auto-delete old entries
  - [ ] Implement `checkStorageQuota()` to warn at 80% full
  - [ ] Test: Create many large discussions until quota hits
  - [ ] Verify pruning happens and discussion doesn't crash

**Files to modify:**
- `ai-ensemble-v5.html` (saveState, loadHistory functions)

**PR checklist:**
- [ ] Storage quota errors handled gracefully
- [ ] User gets clear message about quota
- [ ] Auto-pruning prevents quota crash
- [ ] Tested with large discussions

---

**Phase 2 Verification:**
```bash
# Test checklist:
- [ ] Restart browser, download logs → valid JSON with timestamps
- [ ] Slow network test:
  - Throttle to "Slow 3G" in DevTools
  - Start discussion
  - Wait 15s without data
  - Verify "Connection stalled" appears
- [ ] Test CORS error:
  - Change endpoint to "https://nonexistent.com/api"
  - Click "Discover Models"
  - Verify error message is helpful (not just "Error")
- [ ] Test storage quota:
  - Set a small quota in DevTools
  - Create discussion
  - Verify quota error handled gracefully
```

---

## Phase 3: Reliability & Performance (Week 3, ~5 hours)

**Goal:** Make the app more robust and fast.

### Task 3.1: Add Rate Limiting ✓
- **Time:** 1 hour
- **Owner:** (You)
- **Checklist:**
  - [ ] Create `RequestThrottler` class
  - [ ] Prevent more than 1 "Start Discussion" per 2 seconds
  - [ ] Disable button for 2s after click
  - [ ] Show countdown if user clicks too fast
  - [ ] Test: Click "Start" button rapidly, verify throttle works

**Files to modify:**
- `ai-ensemble-v5.html` (startDiscussion function)

**PR checklist:**
- [ ] Can't spam "Start" button
- [ ] Visual feedback (button disabled, countdown)

---

### Task 3.2: Version Tracking ✓
- **Time:** 0.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Add `APP_VERSION = '1.0.0'` constant
  - [ ] Check version on load
  - [ ] Clear old data if version changed
  - [ ] Add cache-busting headers (already in HTML?)
  - [ ] Test: Update version number, reload, verify cache cleared

**Files to modify:**
- `ai-ensemble-v5.html` (top of script, meta tags in head)

**PR checklist:**
- [ ] Version constant present
- [ ] Version check happens on load
- [ ] Cache busting headers present

---

### Task 3.3: Add Accessibility (ARIA) ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Add `aria-label` to all buttons
  - [ ] Add `aria-live="polite"` to status messages
  - [ ] Add `role="status"` to status boxes
  - [ ] Add `role="button"` to clickable divs (if any)
  - [ ] Use text + icon for status (not color alone)
  - [ ] Add keyboard shortcuts (Escape to stop, Ctrl+S to export)
  - [ ] Test with screen reader (VoiceOver on Mac, or free NVDA on Windows)

**Files to modify:**
- `ai-ensemble-v5.html` (HTML + script for keyboard handling)

**PR checklist:**
- [ ] Screen reader can navigate all interactive elements
- [ ] Status messages announced
- [ ] Keyboard shortcuts work

---

### Task 3.4: Mobile Responsiveness ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Test on iPhone (DevTools device emulation)
  - [ ] Test on Android (DevTools device emulation)
  - [ ] Ensure touch targets ≥44×44px
  - [ ] Add mobile-specific CSS (max-width: 768px)
  - [ ] Test input fields with mobile keyboard
  - [ ] Test model card readability
  - [ ] Test scroll behavior (should smooth-scroll)

**Files to modify:**
- `ai-ensemble-v5.html` (CSS media queries)

**PR checklist:**
- [ ] Looks good on iPhone SE (small screen)
- [ ] Looks good on iPad (wide screen)
- [ ] Touch targets are large enough
- [ ] Text is readable without zooming

---

**Phase 3 Verification:**
```bash
# Test checklist:
- [ ] DevTools: Test on iPhone, iPad, Android
  - [ ] Text readable without zoom
  - [ ] Buttons easily tappable
- [ ] Keyboard test:
  - [ ] Tab through buttons
  - [ ] Escape stops discussion
  - [ ] Ctrl+S exports markdown
- [ ] Screen reader test (macOS VoiceOver):
  - [ ] Tab to "Start Discussion" button, VO reads "Start Discussion"
  - [ ] Start discussion, VO announces "Model response connecting"
  - [ ] Status messages read aloud
```

---

## Phase 4: Testing & Documentation (Week 4, ~5 hours)

**Goal:** Ensure quality and help users.

### Task 4.1: Write Unit Tests ✓
- **Time:** 2.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Set up Jest or Vitest
  - [ ] Test input validation function
  - [ ] Test retry logic with mocked fetch
  - [ ] Test markdown sanitization
  - [ ] Test localStorage quota handling
  - [ ] Achieve ≥70% code coverage
  - [ ] All tests passing locally

**Tools:**
- Jest: `npm install --save-dev jest`
- Vitest: `npm install --save-dev vitest`

**Example test:**
```javascript
describe('validateInputs', () => {
    it('should reject short questions', () => {
        // Set up DOM with short question
        const result = validateInputs();
        expect(result.valid).toBe(false);
        expect(result.errors).toContain('Question must be at least 5 characters');
    });
});
```

**PR checklist:**
- [ ] Test file included (e.g., `ai-ensemble.test.js`)
- [ ] Tests cover main logic paths
- [ ] All tests pass locally
- [ ] Coverage report shows ≥70%

---

### Task 4.2: Write Documentation ✓
- **Time:** 1.5 hours
- **Owner:** (You)
- **Checklist:**
  - [ ] Update README with:
    - Features
    - Setup (how to run)
    - API compatibility (OpenRouter, Ollama, OpenAI, Azure)
    - Configuration options
    - Troubleshooting (CORS, timeouts, etc.)
  - [ ] Add CHANGELOG with v1.0.0 release notes
  - [ ] Add SECURITY.md:
    - API keys not stored
    - No data sent to our servers
    - XSS protected
  - [ ] Create DEPLOYMENT.md for self-hosting:
    - Docker (optional)
    - Environment variables
    - Nginx config for CORS
  - [ ] Add comments in code for complex functions

**Files to create:**
- `README.md` (main documentation)
- `CHANGELOG.md` (version history)
- `SECURITY.md` (security info)
- `DEPLOYMENT.md` (deployment guide)

**PR checklist:**
- [ ] README is clear and complete
- [ ] Troubleshooting section covers common issues
- [ ] Security practices documented

---

### Task 4.3: Create Deployment Guide ✓
- **Time:** 1 hour
- **Owner:** (You)
- **Checklist:**
  - [ ] Document how to run locally (`python3 -m http.server 3000`)
  - [ ] Document how to deploy to hosting (Netlify, Vercel, GitHub Pages, AWS S3, etc.)
  - [ ] Document how to add CORS headers for self-hosted APIs
  - [ ] Document monitoring setup (optional: Sentry, LogRocket)
  - [ ] Document how to report bugs / get support

**Example Netlify deployment:**
```bash
# netlify.toml
[build]
  publish = "."

[[redirects]]
  from = "/*"
  to = "/ai-ensemble-v5.html"
  status = 200
```

**PR checklist:**
- [ ] Deployment steps clear
- [ ] Works on at least one hosting platform
- [ ] CORS config explained for API endpoints

---

### Task 4.4: Load Testing ✓
- **Time:** 1 hour
- **Owner:** (You)
- **Checklist:**
  - [ ] Test app with 5 simultaneous discussions
  - [ ] Test with very long questions (5000 chars)
  - [ ] Test with very long responses (2000+ tokens)
  - [ ] Monitor browser memory usage (should not leak)
  - [ ] Check localStorage growth (should stabilize)
  - [ ] Test on slow network (DevTools throttle)
  - [ ] Document performance baseline

**Test script:**
```javascript
// In browser console:
for (let i = 0; i < 5; i++) {
    setTimeout(() => startDiscussion(), i * 2000);
}
```

**PR checklist:**
- [ ] App handles 5+ concurrent discussions
- [ ] No memory leaks
- [ ] localStorage doesn't blow up
- [ ] Slow network doesn't hang UI

---

**Phase 4 Verification:**
```bash
# Test checklist:
- [ ] `npm test` or `vitest` passes all tests
- [ ] README.md exists and is clear
- [ ] Deploy to Netlify/Vercel, confirm works
- [ ] Load test: 5 concurrent discussions, monitor DevTools
- [ ] Final review: does app feel production-ready?
```

---

## Pre-Launch Checklist

Before announcing to users:

- [ ] All critical security issues fixed
- [ ] Logging working (can download logs)
- [ ] Retry logic tested
- [ ] CORS errors show helpful messages
- [ ] localStorage quota handled
- [ ] Tests passing (≥70% coverage)
- [ ] Documentation complete
- [ ] Mobile tested (iOS + Android)
- [ ] Accessibility tested (screen reader)
- [ ] Load tested (5+ concurrent)
- [ ] Performance baseline documented
- [ ] Error tracking set up (optional: Sentry)
- [ ] README clear and complete
- [ ] Security.md published
- [ ] Deployment guide written

---

## Weekly Standup Template

```
Week N: [Phase]
====================

Completed:
- [ ] Task N.M: <description>
- [ ] Task N.M: <description>

Blockers:
- None / <blocker description>

Next Week:
- [ ] Task N.M: <description>
- [ ] Task N.M: <description>

Quality metrics:
- Test coverage: X%
- Bugs found: Y
- Performance: Z ms response time
```

---

## Success Criteria

✅ **Phase 1 (Critical):** No security vulnerabilities  
✅ **Phase 2 (Reliability):** All errors visible & debuggable  
✅ **Phase 3 (UX):** Works on mobile, accessible, fast  
✅ **Phase 4 (Quality):** Documented, tested, production-ready  

**Final exit criteria:**
- Zero critical/high severity issues remaining
- ≥70% test coverage
- Documentation complete
- Load test passes
- User can start → complete discussion without errors
- User can recover from network failure
- User can export results (Markdown + JSON)

---

## Estimated Timeline

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1 (Critical) | 1 week (8h) | Secure, no XSS, proper error handling |
| 2 (Observability) | 1 week (6h) | Full logging, CORS help, stall detection |
| 3 (UX) | 1 week (5h) | Mobile, accessible, rate limited |
| 4 (Quality) | 1 week (5h) | Tested, documented, deploy-ready |
| **Total** | **4 weeks (24h)** | **Production-Ready App** |

**Effort breakdown:**
- 1 dev working full-time: 3 weeks
- 1 dev part-time (20h/week): 5 weeks
- 2 devs: 2 weeks

---

## Communication Plan

### Week 1 (End of Phase 1):
> "We're hardening security. API keys are no longer stored locally for safety. You'll need to re-enter your API key each session (we're considering OAuth for the future)."

### Week 2 (End of Phase 2):
> "Reliability is here. Failed requests retry automatically. Network issues are now clearly shown. Download logs to share with support if needed."

### Week 3 (End of Phase 3):
> "Better everywhere. Works on mobile, screen reader friendly, and much faster. Give it a try!"

### Week 4 (Launch):
> "🎉 AI Ensemble v1.0.0 is here! Production-ready, fully tested, and documented. Read the README for usage & troubleshooting."

---

## Post-Launch Maintenance

- Monitor error logs daily for first week
- Respond to GitHub issues within 24h
- Release patch fixes (v1.0.1) as bugs found
- Plan v1.1 with user feedback (optional backend, persistent storage, etc.)
- Run monthly performance audits

