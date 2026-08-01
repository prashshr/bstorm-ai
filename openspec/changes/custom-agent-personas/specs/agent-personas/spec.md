# Specification: Agent Personas

## Purpose
Specifies custom Agent Personas, system prompt overrides, avatar badges, and CRUD REST APIs (`/api/personas`).

## ADDED Requirements

### Requirement: Custom Agent Persona Management
The system SHALL allow users to create, update, list, and delete custom Agent Personas containing a custom name, role description, system prompt, avatar, and assigned model key.

#### Scenario: User creates a custom Security Auditor agent
- **GIVEN** an authenticated user
- **WHEN** user submits `POST /api/personas` with name `"Security Auditor"`, role `"OWASP Expert"`, system prompt `"You are a security auditor..."`, avatar `"🛡️"`, and model `"openrouter::openai/gpt-4o"`
- **THEN** system saves the persona and returns the created `AgentPersona` record

### Requirement: Default-Off Consensus Synthesis
Discussions SHALL default to `consensusEnabled = false` unless explicitly toggled on by the user.

#### Scenario: User starts a new discussion
- **GIVEN** a new discussion initialized in `discussion.svelte.ts`
- **WHEN** user submits a prompt
- **THEN** models answer individually without generating an automated consensus summary card
