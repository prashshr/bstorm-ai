# UI / Frontend Design Council — Project Brief

## Context

You are one of several AI agents participating in a design council. I will share screenshots of the current UI with you. You do not have access to the source code.

Your task is to provide **your own independent, unbiased assessment** of:

1. The current UI quality, consistency, and production-readiness.
2. What should change to meet modern production standards.
3. The best frontend architecture and tech stack for this specific use-case.

Do not ask for more screenshots or code access — base your assessment strictly on the screenshots provided and the project description below. I am collecting independent opinions from multiple agents, so do not coordinate or align with others.

---

## Project Description

**AI-Ensemble** is a production-grade multi-provider AI discussion platform.

Users assemble a panel of 2–5 AI models from different providers (OpenAI, Anthropic, Gemini, OpenRouter, DeepSeek, etc.), pose a single question to all of them, and the models respond in structured rounds. A dedicated **consensus model** then synthesises the responses into a weighted summary. The system also supports **live web search (RAG)** — it can fetch real-time context from the web before each discussion round to ground the models' answers.

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) + SQLAlchemy + Alembic |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Frontend | **Vanilla HTML + Vanilla CSS + Vanilla JavaScript** (single `index.html`, ~5500 lines, no framework, no build step) |
| Backend Auth | JWT with encrypted credential storage |
| Deployment | K3s Kubernetes (K8s) with Traefik ingress, cert-manager TLS |
| Frontend Serving | nginx:1.27-alpine container (hostPath mount to the single `index.html`) |
| CI/CD | GitHub Actions → GHCR → K3s |
| AI Providers | OpenAI-compatible APIs, Anthropic, Gemini, OpenRouter, Vertex, Requesty, Mammouth |
| RAG Pipeline | Self-hosted SearXNG (fallback: DuckDuckGo), optional Tavily API |

### Key Technical Detail

The entire frontend is a **single `index.html` file** containing all HTML markup, inline CSS (~700 lines in a single `<style>` block), and inline JavaScript (~3500 lines in a single `<script>` block). There is no framework, no bundler, no module system, and no build step. The file is served by a plain nginx container with no custom config — just the default static file server.

---

## Current UI — What You Will See in Screenshots

### Screenshots I Will Share

1. **Login Page** — username/password form, branding, debug toggle
2. **Main Layout (New Discussion tab)** — header, left sidebar (provider list), main area with settings
3. **Provider Configuration** — API endpoint input, provider selection, model listing
4. **Discussion in Progress** — round timeline, individual model responses, loading states
5. **Discussion Summary** — consensus synthesis with weighted scores
6. **History View** — past discussions list with search
7. **Provider Tab** — active provider details, model management

### UI Characteristics

- Dark theme with orange accent (#ff5c00)
- SVG icon sprite system (Feather-style icons)
- CSS custom properties for theming (dark/light toggle exists)
- Responsive layout with flexbox/grid
- Inline styles mixed with CSS classes
- Tab-based navigation: New Discussion, Provider, Current Discussion, History
- Drag-and-drop file attachment zone on the question input
- RAG progress indicator with loading bar
- Streaming responses displayed in round cards
- Export button for discussion summaries

---

## What I Need From You

Answer the following **independently**. Be specific and opinionated — do not hedge. State what you believe is the best approach for THIS project, not generic best practices.

### 1. Frontend Architecture & Tech Stack

Given that the project is a **single-file vanilla JS SPA** served by nginx:

- Should it stay vanilla (no framework)? If so, what improvements to the single-file architecture would you recommend?
- If it should adopt a framework: **which one** (React, Vue, Svelte, Solid, etc.) and **why specifically for this use-case**? Consider the discussion UI's dynamic nature (streaming responses, round progression, real-time state).
- How should the build pipeline work given the existing K3s deployment (GitHub Actions → GHCR → nginx container)?
- What about state management? The app has auth state, provider config, active discussion state, history, RAG settings, file attachments — how should these be organised?

### 2. UI / UX Critique

Based solely on what you see in the screenshots:

- What looks dated, inconsistent, or unpolished?
- What is missing for a production-quality experience?
- What accessibility issues do you spot?
- How is the responsive design? Mobile readiness?
- What would significantly improve the user experience for this specific workflow (configuring providers → asking a question → watching multi-model discussion → reading a synthesis)?

### 3. Modern Standards

For a 2026 production SaaS product in the AI tools space:

- What design system should this app follow (or build its own)?
- How should streaming model responses be displayed? (Current approach: card-based round timeline with loading spinners)
- What about dark/light mode, typography, spacing, motion?
- Any bleeding-edge UI patterns (e.g. AI-specific UX patterns) that would elevate this product?

### 4. Risk Assessment

- What is the biggest risk in keeping the current architecture?
- What is the biggest risk in adopting a new framework?
- What would you **not** change?

---

## Format Your Response

Please structure your response in four sections matching the four questions above. Keep each section concise but specific. End with a **single recommendation paragraph** that states what you believe is the single most impactful change this project should make.
