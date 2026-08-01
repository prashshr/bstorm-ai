# Change Proposal: Custom Agent Personas and Default-Off Consensus

## Motivation
Users need the ability to define custom Agent Personas for discussion panels—assigning distinct names, roles, system prompts, avatars, and underlying model providers (e.g. `@SecurityAuditor` on GPT-4o, `@SystemArchitect` on Claude 3.5). Furthermore, discussions should default to `consensusEnabled = false` so models reply individually without forcing an automated consensus summary unless explicitly requested.

## Proposed Changes

### 1. Custom Agent Personas
- **Backend Model & API (`/api/personas`)**: Introduce `AgentPersona` database entity (`id`, `user_id`, `name`, `role_description`, `system_prompt`, `model`, `avatar`) and CRUD REST API endpoints.
- **Frontend Personas Store (`personas.svelte.ts`)**: Manage custom agent personas state and API synchronization.
- **UI Integration**: Allow users to assign custom personas to discussion turns, rendering persona avatars, custom names, and role badges on model cards in `ChatMessages.svelte`.

### 2. Default Consensus Setting
- Set `consensusEnabled = false` by default across new discussions and turns, preserving 1-shot individual agent responses unless user toggles consensus ON.

## Verification Plan
1. Validate OpenSpec proposal via `openspec validate --changes`.
2. Execute backend unit and integration test suites via `pytest`.
3. Execute frontend test suite via `vitest`.
4. Deploy web container image to k3s cluster and compile Android APK.
