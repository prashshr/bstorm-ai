# Token Usage & Context Window Stats — Suggestion

## What Users Want to See

| Question | Why It Matters |
|----------|----------------|
| "How many tokens did each model consume?" | Budget tracking, compare model costs |
| "How much context am I sending per round?" | Understand why responses get truncated |
| "What % of my max_tokens did each response use?" | Tune max_tokens setting per discussion |
| "Which rounds/ models have the biggest outputs?" | Identify expensive queries |
| "Total tokens for the whole discussion?" | Cost estimation, history search |

---

## What We Can Track (without a tokenizer)

We can't get **exact** token counts without running a tokenizer on the client side, but we can get **excellent estimates** from data we already have:

| Metric | Source | Accuracy |
|--------|--------|----------|
| **Input chars sent** | `userMessage.length` (already logged) | Exact |
| **Input token estimate** | `userMessage.length / 4` | ~85% accurate |
| **Output tokens received** | `fullText.length / 4` | ~85% accurate |
| **Max tokens allowed** | `maxTokens` (already stored) | Exact |
| **Context window % used** | `(inputEstimate + outputTokens) / maxTokens × 100` | Good estimate |
| **Time taken** | `Date.now()` at start/end | Exact |

---

## Where to Show It

### 1. On Each Model Card (Live) — Per-Response Stats

**Location:** Inside each `.model-card`, below the response text, in a compact stat bar.

```
┌──────────────────────────────────────────────┐
│  claude-opus-4-6                       ✓ ✅  │
│                                              │
│  [response text...]                          │
│                                              │
│  ───────────────────────────────────────     │
│  📊 2,150 tok out · 8,200 tok ctx · 26%     │
│  ⏱ 4.2s · 1,047 chars/s                     │
└──────────────────────────────────────────────┘
```

**What to show:**
- **Output tokens** — estimated from response length
- **Context tokens** — estimated from userMessage sent
- **% of max_tokens used** — `(outputEstimate / maxTokens) × 100`
- **Response time** — how long the model took
- **Chars/s** — throughput rate (helps spot throttling)

### 2. In Round Header (Live) — Per-Round Totals

**Location:** Next to "Round N of M" in the round header

```
Round 2: Review & Discussion                📊 12.4K ctx · 8.1K out · 5 models
```

**What to show:**
- **Total context sent** — sum of all userMessages for this round
- **Total output** — sum of all model responses in this round
- **Model count** — how many models responded

### 3. In Progress Bar Area (Live) — Running Totals

**Location:** Below the progress bar

```
📊 Total: 32.4K input · 18.7K output · 3/3 rounds complete
```

### 4. In History Tab (Persisted) — Discussion-Level Stats

**Location:** In the compact history item metadata, and in the expanded detail view

**Compact view:**
```
✅ Should Germany restart nuclear?     Mar 15 · 5m · 3r · 📊 89K total tokens
```

**Expanded detail view:**
```
📊 Token Usage Summary
──────────────────────────────────────
Max tokens per response:    6,000
Total input (estimate):     52,400 tokens
Total output (estimate):    36,800 tokens
Total discussion:           89,200 tokens
Avg response length:        2,453 tokens
Longest response:           5,810 tokens (claude-opus-4-6 R3)
Context % used:             26% avg · 98% peak (mistral-large-3 R3)

Round Breakdown:
  Round 1: 8,200 ctx → 12,400 out (5 models)
  Round 2: 24,100 ctx → 14,200 out (5 models)
  Round 3: 42,500 ctx → 10,200 out (4 models, 1 error)
```

---

## How to Store the Data

### Extend `discussionData.rounds[roundNum][modelId]` to include stats:

```javascript
// Current structure
discussionData.rounds[1]['claude-opus-4-6'] = {
    text: '...',
    status: 'complete'
};

// New structure — add stats
discussionData.rounds[1]['claude-opus-4-6'] = {
    text: '...',
    status: 'complete',
    stats: {
        inputChars: 8200,          // userMessage.length
        outputChars: 8600,         // fullText.length
        inputTokens: 2050,         // estimated (chars/4)
        outputTokens: 2150,        // estimated (chars/4)
        maxTokens: 6000,           // from maxTokens setting
        contextPercent: 26,        // outputTokens / maxTokens * 100
        startTime: 1719234567890,  // Date.now() before fetch
        endTime: 1719234572090,    // Date.now() after response
        durationMs: 4200,          // endTime - startTime
        charsPerSec: 1047          // outputChars / (durationMs/1000)
    }
};
```

### Extend `discussionData` to include discussion-level stats:

```javascript
discussionData = {
    // ... existing fields ...
    stats: {
        totalInputTokens: 52400,
        totalOutputTokens: 36800,
        totalTokens: 89200,
        avgResponseLength: 2453,
        longestResponse: { model: 'claude-opus-4-6', round: 3, tokens: 5810 },
        roundStats: {
            1: { inputTokens: 8200, outputTokens: 12400, modelCount: 5 },
            2: { inputTokens: 24100, outputTokens: 14200, modelCount: 5 },
            3: { inputTokens: 42500, outputTokens: 10200, modelCount: 4 }
        }
    }
};
```

### Auto-calculate after each model response:

```javascript
// In queryModel(), after response completes:
discussionData.rounds[roundNum][modelId].stats = {
    inputChars: userMessage.length,
    outputChars: fullText.length,
    inputTokens: Math.round(userMessage.length / 4),
    outputTokens: Math.round(fullText.length / 4),
    maxTokens: maxTokens,
    contextPercent: Math.round((Math.round(fullText.length / 4) / maxTokens) * 100),
    startTime: startTime,
    endTime: Date.now(),
    durationMs: Date.now() - startTime,
    charsPerSec: Math.round(fullText.length / ((Date.now() - startTime) / 1000))
};

// Auto-update discussion-level stats
recalculateDiscussionStats();
```

---

## Which Files to Modify

| File | Changes |
|------|---------|
| `ai-ensemble-v5.html` (JS) | Add stats tracking in `queryModel()` after response completes |
| `ai-ensemble-v5.html` (JS) | Add `recalculateDiscussionStats()` function |
| `ai-ensemble-v5.html` (JS) | Add `renderModelStats()` to show stats in model card |
| `ai-ensemble-v5.html` (JS) | Add stats to round header, progress bar area |
| `ai-ensemble-v5.html` (JS) | Update `renderHistory()` to show stats in compact + detail views |
| `ai-ensemble-v5.html` (CSS) | Add stats bar styles |

---

## Implementation Estimate

| Task | Effort |
|------|--------|
| Add stats object to model response data | 15 min |
| Add `recalculateDiscussionStats()` function | 15 min |
| Add stats bar to model card (HTML+CSS) | 30 min |
| Add round-level stats to round header | 20 min |
| Add total stats to progress area | 15 min |
| Update history to show stats | 30 min |
| **Total** | **~2 hours** |

---

## Would you like me to implement this?

I can add the full token usage tracking system if you'd like:

1. **Data layer** — Capture input/output token estimates, timing, context % on every model response
2. **Model card stats bar** — Compact stats below each response (tokens out, ctx %, time)
3. **Round header stats** — Per-round totals (total ctx, output, model count)
4. **Progress area stats** — Running discussion total
5. **History stats** — Per-discussion token summary in both compact and expanded view
6. **All stored in discussionData** — Persisted for future reference