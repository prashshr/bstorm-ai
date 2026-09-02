# Change Proposal: Hybrid Vision Bridge for Multi-Model Discussions

## Motivation
When users attach images or paste clipboard screenshots (charts, data tables, code snippets, diagrams) into a multi-model discussion, some chosen models (e.g., GPT-4o, Claude 3.7 Sonnet, Gemini 2.5 Pro) are vision-capable while others (e.g., DeepSeek-V3/R1, Qwen 2.5 72B, Llama 3.3) are text-only. Previously, sending image payloads to text-only models caused upstream providers to fail with HTTP 400 errors ("Model does not support image inputs"). 

The **Hybrid Vision Bridge** provides an automated transcription bridge:
1. Vision models receive the native high-resolution image payload directly.
2. Text-only models receive a structured visual transcription extracted via an active vision model, enabling every model in the council to analyze the image data and participate in consensus without crashing.

## Proposed Changes

### 1. Discussion Store Hybrid Vision Bridging (`discussion.svelte.ts`)
- Detect when round attachments contain images and the active council contains text-only models.
- If a vision model is present in the selection or configured providers, execute a fast transcription probe:
  `"Describe and transcribe all data, text, tables, charts, numbers, and visual elements from this image accurately and comprehensively so that a text-only model can analyze it thoroughly."`
- Inject the structured transcription block into the text prompt for text-only models.
- Exclude raw binary `image/*` payloads from the API request for text-only models to eliminate HTTP 400 errors.

### 2. Backend Fallback & Error Prevention (`openai_compatible.py`, `proxy.py`)
- For text-only models without native vision, ensure `_build_openai_content` omits invalid `image_url` blocks when text transcriptions are embedded.

## Verification Plan
1. Validate OpenSpec change proposal via `openspec validate --all`.
2. Execute frontend and backend unit test suites (`npm test`, `pytest`).
3. Verify mixed vision & text-only model execution with image attachment in browser.
4. Rebuild production Docker images and compile Android APK.
