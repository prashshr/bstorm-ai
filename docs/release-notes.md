# Release Notes

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
