# Change Proposal: Stateful Actor-Based Agent Runtime & Event Stream Architecture

## Motivation
Traditional multi-model systems execute isolated 1-shot parallel prompts followed by a single static summary. To transform AI-Ensemble into an interactive expert panel, discussions are refactored into a **Stateful Actor Runtime**. Each selected model operates as an autonomous **Agent Actor** with an inbox, memory, opinion, and confidence score. A **Moderator FSM** orchestrates inter-agent cross-talk, challenges, and evolving consensus versions (`v1 -> v2 -> v3`).

## Proposed Changes

### 1. Event-Driven Discussion Log (`Everything is an Event`)
- Replace static message turn structures with a typed event log stream:
  - `UserAsked`
  - `AgentResponded`
  - `AgentQuestioned`
  - `AgentCritiqued`
  - `AgentRevised`
  - `ModeratorDecision`
  - `ConsensusUpdated`
  - `ConfidenceShifted`

### 2. Stateful Agent Actors & Specialist Personas
- **Agent Actor State**: Each agent maintains `inbox`, `memory` (claims made, claims retracted, questions asked/received), `opinion`, and `confidence %` (0–100%).
- **Specialist Personas**: Pre-built specialist roles mapped to models:
  - 🏗️ `System Architect`
  - 🛡️ `Security Auditor`
  - 🔍 `Researcher`
  - ⚖️ `Legal / Compliance`
  - 😈 `Devil's Advocate`
  - 💻 `Pragmatic Coder`
- **Agent-to-Agent Mentions**: Agents address each other directly (`@SecurityAuditor`, `@Architect`), triggering targeted inbox replies.

### 3. Moderator FSM & Evolving Consensus
- **Moderator Orchestration**: A finite-state machine decides next speakers, checks consensus stability, triggers research passes, and stops early if agreement is reached in 1 round.
- **Evolving Consensus**: Consensus updates dynamically (`v1 -> v2 -> v3`) as the debate progresses.

### 4. GitHub PR-Style Threaded UI
- Render discussion threads with Agent Avatars, Role Badges, Confidence Trajectory Bars (`94% -> 81%`), `@Agent` mention badges, and Evolving Consensus Cards.

## Verification Plan
1. Validate OpenSpec change proposal via `openspec validate --changes`.
2. Execute backend pytest suite covering event schemas, agent memory, and moderator FSM transitions.
3. Execute frontend vitest suite covering agentRuntime store and event stream parsing.
4. Deploy v5.0.0 container image to k3s cluster and compile Android APK.
