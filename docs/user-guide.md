# AI Ensemble — User Guide

## What is an Ensemble?

An **AI Ensemble** is like asking 3-5 different experts the same question, then collecting and comparing their answers to get the best possible result. Each model has different strengths, training data, and reasoning styles — together they produce richer answers than any single model.

---

## How It Works — Step by Step

```
          ┌─────────────────────────────────────────────────────┐
          │                YOU ASK A QUESTION                   │
          │  "Best smartphone under 300€ in Berlin?"            │
          └──────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
          ┌─────────────────────────────────────────────────────┐
          │  ①  OPTIONAL: Web Research (RAG)                    │
          │     Searches the internet for relevant data          │
          │     → Tavily → SearXNG → DuckDuckGo                 │
          │     → Injected as context for all models             │
          └──────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
          ┌─────────────────────────────────────────────────────┐
          │  ②  ROUND 1: All models answer in parallel          │
          │                                                      │
          │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
          │  │ Claude   │ │ Gemini   │ │ DeepSeek │  ... 5 models│
          │  └──────────┘ └──────────┘ └──────────┘             │
          │     Each sees: Your question + RAG context           │
          │     Each responds independently                      │
          └──────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
          ┌─────────────────────────────────────────────────────┐
          │  ③  ROUND 2 (optional): Models see each other       │
          │     Each model gets ALL round-1 answers +            │
          │     their own previous answer + RAG context           │
          │     They refine and improve their responses           │
          └──────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
          ┌─────────────────────────────────────────────────────┐
          │  ④  CONSENSUS: One model summarizes everything      │
          │     → Produces a weighted score table                │
          │     → Gives a final verdict                          │
          └──────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
          ┌─────────────────────────────────────────────────────┐
          │  ⑤  RESULTS: Compare, export, share                 │
          │     All rounds, all responses, consensus             │
          └─────────────────────────────────────────────────────┘
```

---

## The User's Journey

### 1. Add a Provider (API Key)
Before you can use models, you need to connect to a provider:

```
What you do:                          What happens:
┌─────────────────────┐               ┌──────────────────────┐
│ Click "Add Provider"│               │ Key is ENCRYPTED     │
│ Paste API key       │──────────────▶│ Stored in database   │
│ Select provider type│               │ Never returned to UI │
│ Click "Save"        │               │ Visible only as •••• │
└─────────────────────┘               └──────────────────────┘
```

**Supported providers:** OpenAI, Anthropic (Claude), Google Gemini, OpenRouter, Perplexity, Vertex AI, and any OpenAI-compatible endpoint.

### 2. Discover Models
Click "Discover Models" to fetch available models from your provider. Select which models to use in the discussion (minimum 2, maximum 5).

### 3. Configure Your Discussion

```
┌──────────────────────────────────────────────────────────────┐
│  Your Question:  "Best smartphone under 300€ in Berlin?"      │
│                                                               │
│  ☑ Enable Web Research (RAG)    ☐ Deep Research              │
│                                                               │
│  Selected Models:                                               │
│  [☑ Claude Opus] [☑ Gemini Flash] [☑ DeepSeek R1]             │
│  [☑ GLM-5] [☑ Qwen 3.7 Max]                                   │
│                                                               │
│  Response Format:  □ Concise  ☑ Detailed  □ Bullet Points     │
│                                                               │
│  [▶  Start Discussion]                                         │
└──────────────────────────────────────────────────────────────┘
```

| Setting | What it does |
|---------|-------------|
| **Web Research (RAG)** | Searches the internet and injects results as context for all models. Green dot = success, red dot = failed. |
| **Deep Research** | Also runs RAG between rounds, so round 2 has fresh web data based on round 1 discussions. |
| **Response Format** | Optional instructions appended to each model's prompt (e.g., "Use bullet points"). |

### 4. Watch the Discussion Unfold

```
ROUND 1 ──────────────────────────────────────────────────────
                                                                 
  Claude Opus    ████████████████████████████  100%  ✓ Done     
  Gemini Flash   ████████████████████████████  100%  ✓ Done     
  DeepSeek R1    ████████████████████████████  100%  ✓ Done     
  GLM-5          ████████████████████████████   85%  ⏳ Running  
  Qwen 3.7 Max   ████████████████              40%  ⏳ Running  
                                                                 
ROUND 2 ──────────────────────────────────────────────────────
  (Models see each other's answers and refine)
                                                                 
CONSENSUS ─────────────────────────────────────────────────────
  Qwen 3.7 Max summarizes the final agreement
```

Each model response shows:
- **Input/output token count** (how much data it processed)
- **Duration** (how long it took)
- **Chars per second** (speed)

### 5. Read the Consensus

After all rounds, one model produces a **consensus summary**:

```
┌─────────────────────────────────────────────────────────┐
│  VERDICT                                                  │
│  Top picks: Samsung Galaxy A26, Xiaomi Redmi Note 14,     │
│  Motorola Moto G85, POCO X7, CMF Phone 2                  │
│                                                           │
│  Weighted Scores:                                          │
│  ┌──────────────┬───────┬───────┬──────────────────────┐  │
│  │ Model        │Weight │ Score │ Rationale             │  │
│  ├──────────────┼───────┼───────┼──────────────────────┤  │
│  │ GLM-5.2      │ 20%   │ 9/10  │ Balanced pricing     │  │
│  │ Gemini Flash │ 20%   │ 8/10  │ Good structure        │  │
│  │ Claude Opus  │ 20%   │ 8/10  │ Practical advice      │  │
│  │ DeepSeek R1  │ 20%   │ 7/10  │ Minor inaccuracies   │  │
│  │ Qwen 3.7 Max │ 20%   │ 6/10  │ Too brief             │  │
│  └──────────────┴───────┴───────┴──────────────────────┘  │
│                                                           │
│  ▶  Buy at MediaMarkt or Saturn for best in-store deals   │
└─────────────────────────────────────────────────────────┘
```

---

## Behind the Scenes — What You Don't See

### The Prompt (what each model actually receives)

When you enable RAG, behind the scenes the system builds a prompt like this:

```
=== WEB RESEARCH CONTEXT ===
[Content from notebookcheck.net, chip.de, idealo.de...]
=== END WEB RESEARCH CONTEXT ===

RAG data: Used | Self Websearch: Not Available | Training Data: Used

[Your original question]
"Best smartphone under 300€ in Berlin?"
```

This runs each round. In round 2, the prompt also includes all round-1 answers from other models, so each model can refine based on what others said.

### Data Source Status

Each model's response starts with a one-line status showing what it used:

```
RAG data: Used | Self Websearch: Not Available | Training Data: Used

Here are my top 5 picks...
```

This makes it transparent whether the model relied on the web research, its own training, or both.

### Export Options

You can export discussions as:
- **JSON** — Full structured data for analysis
- **Markdown** — Clean readable format
- **HTML** — Styled for sharing
- **Text** — Plain text summary

---

## Quick Reference

| Action | What happens |
|--------|-------------|
| **Add a provider** | API key is encrypted with your personal UEK, stored in DB |
| **Select models** | Minimum 2, maximum 5 per discussion |
| **Enable RAG** | 3 search engines run in parallel, results injected into prompt |
| **Start discussion** | All selected models receive the prompt simultaneously |
| **Round 2** | Each model sees all other models' round-1 answers |
| **Consensus** | One model weighs all responses and produces a verdict |
| **Export** | JSON, Markdown, HTML, or Text format |
