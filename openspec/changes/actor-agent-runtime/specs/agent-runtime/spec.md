# Specification: Agent Runtime

## Purpose
Specifies the separation of static AgentDefinition (identity & capabilities) from dynamic per-discussion AgentRuntime (inbox, memory, confidence, opinion) owned by the Discussion space.

## ADDED Requirements

### Requirement: Separation of AgentDefinition and AgentRuntime
The system SHALL separate static `AgentDefinition` (Name, Avatar, Role, System Prompt, Provider, Model, Capabilities, Temperature) from dynamic `AgentRuntime` (Discussion ID, Confidence %, Inbox, Claims, State, Memory, Current Opinion).

#### Scenario: Same agent participates in multiple concurrent discussions
- **GIVEN** a static `AgentDefinition` for "System Architect"
- **WHEN** the "System Architect" agent participates in 2 separate discussions
- **THEN** a unique `AgentRuntime` is instantiated for each discussion, isolating runtime memory, inboxes, and confidence scores

### Requirement: Discussion-Owned Agent Runtimes
Each `Discussion` instance SHALL own and contain its active `AgentRuntime` instances and Moderator FSM.

#### Scenario: Discussion state initialization
- **GIVEN** a discussion session with 3 assigned agent definitions
- **WHEN** the discussion session starts
- **THEN** the discussion creates 3 isolated `AgentRuntime` instances and 1 Moderator FSM bound to its discussion ID
