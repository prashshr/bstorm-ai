# Specification: Consensus

## Purpose
Specifies Moderator FSM orchestration, dynamic consensus versioning (`v1 -> v2 -> v3`), early-stop debate termination, and confidence score trajectory tracking.

## ADDED Requirements

### Requirement: Moderator FSM Orchestration
The Moderator SHALL operate as a finite-state machine deciding speaker turns, checking consensus stability, and terminating debate early if agreement is reached.

#### Scenario: All agents agree in Round 1
- **GIVEN** a discussion where all selected agents express high confidence and identical stances in Round 1
- **WHEN** the Moderator FSM evaluates consensus stability
- **THEN** the Moderator emits `Consensus v1` and terminates the debate early without forcing unnecessary rounds

### Requirement: Dynamic Evolving Consensus
Consensus SHALL update versioned iterations (`v1 -> v2 -> v3`) in real-time as agents challenge and refine each other's points.

#### Scenario: Agent revises stance in Round 2
- **GIVEN** `Consensus v1` generated after Round 1
- **WHEN** Agent B revises its stance in Round 2 following peer review
- **THEN** the Moderator updates the synthesis to `Consensus v2` highlighting the newly resolved trade-off
