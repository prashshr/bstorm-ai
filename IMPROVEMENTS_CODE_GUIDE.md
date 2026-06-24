# Production Improvements — Code Examples & Implementation Guide

This document provides **copy-paste ready code** for each improvement. Pick and choose based on your priority.

---

## 1. Remove API Key Storage from localStorage

**Current code (UNSAFE):**
```javascript
// Line 654
function saveState() {
    const state = { ...discussionData, apiKey: storedApiKey };  // ❌ STORES KEY
    localStorage.setItem('councilState', JSON.stringify(state));
}
```

**Fixed version:**
```javascript
function saveState() {
    // Create state copy WITHOUT the API key
    const state = { ...discussionData };
    delete state.apiKey;  // Never store the key
    
    localStorage.setItem('councilState', JSON.stringify(state));
}

function loadState() {
    const saved = localStorage.getItem('councilState');
    if (saved) {
        try {
            const state = JSON.parse(saved);
            discussionData = state;
            // NOTE: User must re-enter API key — it's not stored
            
            if (state.status === 'in_progress' && state.id) {
                stateRestored = true;
                discussionRunning = true;
                // ... rest of restore logic
            }
        } catch (e) {
            log('error', 'Could not restore state');
        }
    }
}
```

**Also update these lines:**
- Line 614–615: Don't set `document.getElementById('apiKey').value = ...`
- Line 806: Still store `storedApiKey` in memory (for current session only)

**User experience:**
```javascript
// In HTML, add a note:
<div style="color: var(--text-tertiary); font-size: 12px; margin-bottom: 10px;">
    ℹ️ Your API key is never saved. It's only kept in memory for this session.
</div>
```

---

## 2. Sanitize Markdown Output (XSS Prevention)

**Add DOMPurify to your `<head>`:**
```html
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
```

**Create a helper function:**
```javascript
function renderMarkdown(text) {
    if (!text) return '';
    try {
        const html = marked.parse(text);
        const sanitized = DOMPurify.sanitize(html, {
            ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                          'p', 'br', 'strong', 'em', 'u', 'code', 
                          'pre', 'a', 'ul', 'ol', 'li', 'blockquote'],
            ALLOWED_ATTR: ['href', 'title'],
            RETURN_TRUSTED_TYPE: false
        });
        return sanitized;
    } catch (e) {
        log('error', 'Markdown render failed', { error: e.message });
        return text; // Fall back to plain text
    }
}
```

**Replace all unsafe `.innerHTML` calls:**

**Before:**
```javascript
// Line 1094
responseElement.innerHTML = marked.parse(fullText);

// Line 643
document.getElementById('consensusText').innerHTML = marked.parse(state.consensus);

// Line 1182
document.getElementById('consensusText').textContent = fullText;
```

**After:**
```javascript
// Line 1094
responseElement.innerHTML = renderMarkdown(fullText);

// Line 643
document.getElementById('consensusText').innerHTML = renderMarkdown(state.consensus);

// Line 1182 (keep as textContent, safer)
document.getElementById('consensusText').innerHTML = renderMarkdown(fullText);
```

---

## 3. Implement Retry Logic with Exponential Backoff

**Replace the current silent catch-all:**

**Before:**
```javascript
// Line 1076
} catch (e) {}  // Silent failure!
```

**After — create a retry wrapper:**
```javascript
// At the top of your script
const RETRY_CONFIG = {
    MAX_ATTEMPTS: 3,
    INITIAL_DELAY_MS: 1000,
    MAX_DELAY_MS: 10000
};

function isRetryableError(error) {
    const message = error.message || '';
    const isTimeout = error.name === 'AbortError';
    const is5xx = message.includes('500') || message.includes('503');
    const isRateLimit = message.includes('429');
    return isTimeout || is5xx || isRateLimit;
}

async function queryModelWithRetry(modelId, roundNum, totalRounds, endpoint, apiKey, timeout) {
    let lastError = null;

    for (let attempt = 1; attempt <= RETRY_CONFIG.MAX_ATTEMPTS; attempt++) {
        try {
            log('info', `Querying ${modelId} (attempt ${attempt}/${RETRY_CONFIG.MAX_ATTEMPTS})`);
            return await queryModel(modelId, roundNum, totalRounds, endpoint, apiKey, timeout);
        } catch (error) {
            lastError = error;
            log('warn', `${modelId} attempt ${attempt} failed`, { error: error.message });

            if (attempt < RETRY_CONFIG.MAX_ATTEMPTS && isRetryableError(error)) {
                const delay = Math.min(
                    RETRY_CONFIG.INITIAL_DELAY_MS * Math.pow(2, attempt - 1),
                    RETRY_CONFIG.MAX_DELAY_MS
                );
                log('info', `Retrying ${modelId} in ${delay}ms...`);

                // Show user: "Retrying in 5s..."
                showStatus(`🔄 Retrying ${modelId} in ${Math.ceil(delay / 1000)}s...`, 'warning');

                await new Promise(r => setTimeout(r, delay));
            } else {
                // Not retryable or max attempts reached
                throw error;
            }
        }
    }

    throw lastError;
}

// Update runRound to use the retry wrapper:
async function runRound(roundNum, totalRoundsNum, endpoint, apiKey, timeout) {
    const modelsRound = document.getElementById(`modelsRound${roundNum}`);
    if (!modelsRound) {
        modelsRound = document.createElement('div');
        modelsRound.id = `modelsRound${roundNum}`;
        modelsRound.className = 'models-grid';
        document.getElementById('discussionSection').appendChild(modelsRound);
    }

    const promises = selectedModels.map(modelId =>
        queryModelWithRetry(modelId, roundNum, totalRoundsNum, endpoint, apiKey, timeout)
            .catch(error => {
                // Capture error but continue with next model
                log('error', `Failed to query ${modelId}`, { error: error.message });
                roundErrors[roundNum] = roundErrors[roundNum] || [];
                roundErrors[roundNum].push(`${modelId}: ${error.message}`);
            })
    );

    await Promise.all(promises);
    showRoundStatus();
}
```

---

## 4. Improve Error Handling & Logging

**Create a structured logger:**
```javascript
const Logger = {
    logs: [],
    MAX_LOGS: 500,
    ERROR_LISTENERS: [],

    log(level, message, meta = {}) {
        const entry = {
            timestamp: new Date().toISOString(),
            level: level.toUpperCase(),
            message,
            meta
        };
        
        this.logs.push(entry);
        if (this.logs.length > this.MAX_LOGS) {
            this.logs.shift();
        }

        // Console output
        const style = `color: ${level === 'error' ? 'red' : level === 'warn' ? 'orange' : 'blue'}`;
        console.log(`%c[${entry.level}]`, style, message, meta);

        // Notify listeners (for remote logging)
        if (level === 'error') {
            this.ERROR_LISTENERS.forEach(fn => fn(entry));
        }
    },

    info(message, meta) { this.log('info', message, meta); },
    warn(message, meta) { this.log('warn', message, meta); },
    error(message, meta) { this.log('error', message, meta); },

    downloadLogs() {
        const blob = new Blob([JSON.stringify(this.logs, null, 2)], 
                             { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ensemble-logs-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },

    // Optional: send errors to a backend
    onError(callback) {
        this.ERROR_LISTENERS.push(callback);
    }
};

// Replace global `log()` function
function log(message, meta = {}) {
    Logger.info(message, meta);
}

// Send errors to your backend (optional):
Logger.onError((entry) => {
    // POST to your backend
    // fetch('/api/errors', { method: 'POST', body: JSON.stringify(entry) });
});
```

**Update error handling in `queryModel()`:**

**Before:**
```javascript
} catch (error) {
    clearTimeout(timeoutId);
    const status = error.name === 'AbortError' ? 'timeout' : 'error';
    const errorMsg = error.message;
    // ... (lines 1100-1115)
}
```

**After:**
```javascript
} catch (error) {
    clearTimeout(timeoutId);

    const status = error.name === 'AbortError' ? 'timeout' : 'error';
    const errorMsg = error.message;
    const details = {
        modelId,
        roundNum,
        endpoint,
        statusText: error.statusText || 'Unknown',
        isNetwork: error instanceof TypeError
    };

    Logger.error(`${modelId} failed in round ${roundNum}`, details);

    discussionData.rounds[roundNum][modelId] = { text: '', status };
    responseElement.textContent = `${status === 'timeout' ? '⏱️ Timeout' : '❌ Error'}: ${errorMsg}`;
    card.classList.remove('connecting');
    card.classList.add(status);
    badgeElement.className = `model-badge badge-${status}`;
    badgeElement.textContent = status === 'timeout' ? '⏱️' : '✗';

    roundErrors[roundNum] = roundErrors[roundNum] || [];
    roundErrors[roundNum].push(`${modelId}: ${errorMsg}`);

    saveState();
    showRoundStatus();

    // Only throw if this is not retryable
    if (!isRetryableError(error)) {
        throw error;
    }
}
```

---

## 5. Input Validation

**Create a validator function:**
```javascript
function validateInputs() {
    const endpoint = document.getElementById('endpoint').value.trim();
    const apiKey = document.getElementById('apiKey').value.trim();
    const question = document.getElementById('question').value.trim();
    const instructions = document.getElementById('instructions').value.trim();
    const timeout = parseInt(document.getElementById('timeout').value);
    const rounds = parseInt(document.getElementById('rounds').value);

    const errors = [];

    // Endpoint validation
    if (!endpoint) {
        errors.push('Endpoint URL is required');
    } else if (!endpoint.startsWith('http://') && !endpoint.startsWith('https://')) {
        errors.push('Endpoint must start with http:// or https://');
    } else {
        try {
            new URL(endpoint);
        } catch (e) {
            errors.push('Invalid endpoint URL format');
        }
    }

    // API Key validation
    if (!apiKey) {
        errors.push('API key is required');
    } else if (apiKey.length < 10) {
        errors.push('API key seems too short (minimum 10 characters)');
    }

    // Question validation
    if (!question) {
        errors.push('Question is required');
    } else if (question.length < 5) {
        errors.push('Question must be at least 5 characters');
    } else if (question.length > 5000) {
        errors.push('Question too long (max 5000 characters)');
    }

    // Instructions validation (optional)
    if (instructions && instructions.length > 2000) {
        errors.push('Instructions too long (max 2000 characters)');
    }

    // Timeout validation
    if (isNaN(timeout) || timeout < 5 || timeout > 600) {
        errors.push('Timeout must be between 5 and 600 seconds');
    }

    // Rounds validation
    if (isNaN(rounds) || rounds < 1 || rounds > 5) {
        errors.push('Rounds must be between 1 and 5');
    }

    if (selectedModels.length < 2) {
        errors.push('Select at least 2 models');
    } else if (selectedModels.length > 5) {
        errors.push('Select at most 5 models');
    }

    return {
        valid: errors.length === 0,
        errors,
        data: {
            endpoint: endpoint.replace(/\/$/, ''),  // Remove trailing slash
            apiKey,
            question,
            instructions,
            timeout,
            rounds
        }
    };
}

// Use in startDiscussion():
async function startDiscussion() {
    const validation = validateInputs();

    if (!validation.valid) {
        validation.errors.forEach(err => {
            showStatus(`❌ ${err}`, 'error');
        });
        return;
    }

    const { endpoint, apiKey, question, instructions, timeout, rounds } = validation.data;

    // ... rest of startDiscussion logic
}
```

---

## 6. Handle localStorage Quota

**Add quota checking:**
```javascript
function saveState() {
    try {
        const state = { ...discussionData };
        delete state.apiKey;  // Never store key
        
        localStorage.setItem('councilState', JSON.stringify(state));
        checkStorageQuota();
    } catch (e) {
        if (e.name === 'QuotaExceededError') {
            Logger.error('localStorage quota exceeded', { error: e.message });
            showStatus(
                '❌ Storage quota full. ' +
                'Clear browser cache or delete old discussions. ' +
                'Data will not be saved.',
                'error'
            );
            return false;
        }
        throw e;
    }
    return true;
}

function checkStorageQuota() {
    if (!navigator.storage?.estimate) return;

    navigator.storage.estimate().then(({ usage, quota }) => {
        const percentUsed = (usage / quota) * 100;
        
        if (percentUsed > 90) {
            showStatus(
                `⚠️ Storage ${Math.round(percentUsed)}% full. ` +
                'Consider clearing old discussions.',
                'warning'
            );
        }

        Logger.info('Storage check', { percentUsed: percentUsed.toFixed(1), quota, usage });
    });
}

// Auto-prune old discussions
function pruneHistory(maxHistorySize = 20) {
    if (queryHistory.length > maxHistorySize) {
        const removed = queryHistory.length - maxHistorySize;
        queryHistory = queryHistory.slice(-maxHistorySize);
        
        try {
            localStorage.setItem('councilHistory', JSON.stringify(queryHistory));
            Logger.info(`Pruned ${removed} old discussions`);
        } catch (e) {
            if (e.name === 'QuotaExceededError') {
                // Still can't fit, remove more
                queryHistory = queryHistory.slice(-10);
                localStorage.setItem('councilHistory', JSON.stringify(queryHistory));
                Logger.warn('Had to prune to 10 discussions');
            }
        }
    }
}
```

---

## 7. Network Stall Detection

**Wrap fetch with timeout + stall detection:**
```javascript
async function queryModel(modelId, roundNum, totalRounds, endpoint, apiKey, timeout) {
    // ... existing setup code ...

    const controller = new AbortController();
    let timeoutId = null;
    let stallTimeoutId = null;
    let hasReceivedData = false;

    try {
        // Hard timeout
        timeoutId = setTimeout(() => {
            controller.abort();
            Logger.warn(`Timeout: ${modelId} after ${timeout}s`);
        }, timeout * 1000);

        const response = await fetch(`${endpoint}/chat/completions`, { ... });

        if (!response.ok) {
            throw new Error(`API Error ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let streamedChunks = 0;

        // Stall detection: reset stall timer on each chunk
        function resetStallTimer() {
            clearTimeout(stallTimeoutId);
            hasReceivedData = true;
            stallTimeoutId = setTimeout(() => {
                if (hasReceivedData) {  // Only abort if no new data
                    Logger.warn(`Connection stalled: ${modelId} (no data for 15s)`);
                    responseElement.textContent += '\n\n⚠️ Connection stalled. Retrying...';
                    controller.abort();
                }
            }, 15000);
        }

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            resetStallTimer();

            const chunk = decoder.decode(value);
            for (const line of chunk.split('\n')) {
                if (line.startsWith('data: ') && line.length > 7) {
                    try {
                        const json = JSON.parse(line.slice(6));
                        const content = json.choices?.[0]?.delta?.content || '';
                        if (content) {
                            fullText += content;
                            streamedChunks++;
                            responseElement.textContent = fullText;
                            responseElement.scrollTop = responseElement.scrollHeight;
                        }
                    } catch (e) {
                        Logger.warn(`Failed to parse SSE chunk`, { line: line.slice(0, 50) });
                    }
                }
            }
        }

        clearTimeout(stallTimeoutId);
        clearTimeout(timeoutId);

        // ... rest of success handling ...

    } catch (error) {
        clearTimeout(timeoutId);
        clearTimeout(stallTimeoutId);

        const status = error.name === 'AbortError' ? 'timeout' : 'error';
        Logger.error(`${modelId} failed`, { status, error: error.message });

        // ... error handling ...
    }
}
```

---

## 8. Rate Limiting

**Simple request throttling:**
```javascript
const RequestThrottler = {
    lastRequestTimes: {},
    MIN_INTERVAL_MS: 2000,  // min 2s between requests

    canMakeRequest(key) {
        const now = Date.now();
        const lastTime = this.lastRequestTimes[key] || 0;
        const elapsed = now - lastTime;

        if (elapsed < this.MIN_INTERVAL_MS) {
            return {
                allowed: false,
                remainingMs: this.MIN_INTERVAL_MS - elapsed
            };
        }

        this.lastRequestTimes[key] = now;
        return { allowed: true, remainingMs: 0 };
    }
};

// In startDiscussion():
async function startDiscussion() {
    const validation = validateInputs();
    if (!validation.valid) { /* ... */ return; }

    const throttle = RequestThrottler.canMakeRequest('start_discussion');
    if (!throttle.allowed) {
        const seconds = Math.ceil(throttle.remainingMs / 1000);
        showStatus(`Please wait ${seconds}s before starting another discussion`, 'warning');
        return;
    }

    // ... proceed with discussion
}

// Add visual feedback in UI:
<button onclick="startDiscussion()" id="startBtn">Start Discussion</button>

<script>
// Disable button for 2s after click
function startDiscussionWithFeedback() {
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Starting...';

    startDiscussion().finally(() => {
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '▶️ Start Discussion';
        }, 2000);
    });
}
</script>
```

---

## 9. Version Tracking

**Add at the top of your script:**
```javascript
// App version — increment on breaking changes
const APP_VERSION = '1.0.0';
const STORAGE_VERSION_KEY = 'appVersion';

// Call this in the load event
function checkAndInitializeVersion() {
    const savedVersion = localStorage.getItem(STORAGE_VERSION_KEY);
    
    if (savedVersion && savedVersion !== APP_VERSION) {
        Logger.warn('Version mismatch', { old: savedVersion, new: APP_VERSION });
        Logger.info('Clearing old data due to version change');
        
        // Clear old data to prevent compatibility issues
        localStorage.clear();
        localStorage.setItem(STORAGE_VERSION_KEY, APP_VERSION);
        
        showStatus(
            `✓ Updated to v${APP_VERSION}. Your data was reset (this is normal).`,
            'info'
        );
    } else {
        localStorage.setItem(STORAGE_VERSION_KEY, APP_VERSION);
    }
}

// Add cache-busting headers in <head>:
// <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
// <meta http-equiv="Pragma" content="no-cache">
// <meta http-equiv="Expires" content="0">
```

---

## 10. CORS Error Handling

**Better error messages:**
```javascript
async function discoverModels() {
    const endpoint = document.getElementById('endpoint').value.trim();
    const apiKey = document.getElementById('apiKey').value.trim();

    if (!endpoint || !apiKey) {
        showStatus('Please enter endpoint and API key', 'error');
        return;
    }

    showStatus('Discovering models...', 'info');

    try {
        const response = await fetch(`${endpoint}/models`, {
            headers: { 'Authorization': `Bearer ${apiKey}` }
        });

        // Check for CORS or network errors
        if (response.type === 'opaque') {
            throw new Error(
                'CORS error: Server blocked the request. ' +
                'Ensure your endpoint allows requests from this domain. ' +
                'Or, use a CORS proxy if testing locally.'
            );
        }

        if (!response.ok) {
            const text = await response.text();
            const isCorsError = response.status === 0 || 
                               text.includes('CORS') ||
                               text.includes('Access-Control');

            if (isCorsError) {
                throw new Error(
                    `CORS Error ${response.status}: ` +
                    'Your endpoint may not allow requests from this domain. ' +
                    'Ask your API provider to allow this domain.'
                );
            } else {
                throw new Error(
                    `API Error ${response.status}: ${text.substring(0, 100)} ` +
                    `(Check API key and endpoint URL)`
                );
            }
        }

        const data = await response.json();
        // ... success path
    } catch (error) {
        const message = error.message ||
                       (error instanceof TypeError && error.message.includes('Failed to fetch'))
                        ? 'Network error or CORS blocked. Check endpoint URL and browser console.'
                        : 'Unknown error';

        Logger.error('Model discovery failed', { error: message });
        showStatus(`❌ ${message}`, 'error');
    }
}
```

---

## Summary: Integration Steps

1. **Back up your current HTML file**
2. **Add DOMPurify to CDN** (in `<head>`)
3. **Replace the logger** (entire `log()` function and add `Logger` class)
4. **Add validators** (`validateInputs()`)
5. **Update `queryModel()` with retry logic** and stall detection
6. **Update `saveState()` to skip API key**
7. **Add storage quota checks** (`checkStorageQuota()`)
8. **Test thoroughly** before deploying
9. **Update version number** when done

Each section is independent, so you can implement in any order. Start with security (items 1, 2) and error handling (items 3, 4).

