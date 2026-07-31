# Specification: Ensemble

## Purpose
Specifies multi-model concurrent dispatches, staggered request dispatching (`MAX_CONCURRENT = 3`, `STAGGER_MS = 500`), multi-round discussion passes, and automated consensus summary synthesis.

## Requirements

### Requirement: Staggered Concurrent Dispatch
The frontend discussion store SHALL queue and dispatch chat completion requests with a 500ms staggering delay between models to prevent upstream rate limit bursts.

#### Scenario: User sends prompt to 3 models simultaneously
- **GIVEN** 3 models selected (e.g. GPT-4o, Claude 3.5, Gemini 2.0)
- **WHEN** the user clicks Send
- **THEN** Model 1 dispatches immediately at T=0ms, Model 2 dispatches at T=500ms, and Model 3 dispatches at T=1000ms

### Requirement: Automated Consensus Synthesis
When `consensusEnabled` is true, the system SHALL dispatch a synthesis prompt containing all completed model replies to the designated consensus model upon round completion.

#### Scenario: Round 1 models finish streaming
- **GIVEN** all models in Turn 1 completed streaming their answers
- **WHEN** consensus mode is enabled
- **THEN** the store dispatches a summary synthesis request to the consensus model and renders the consensus card at the bottom of the turn
