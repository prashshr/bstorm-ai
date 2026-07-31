# Specification: Chat

## Purpose
Specifies the conversation thread UI view, round-by-round discussion turns, side-by-side model response cards, consensus synthesis cards, and floating jump-to-latest scroll buttons.

## Requirements

### Requirement: Turn-Based Multi-Model Rendering
The system SHALL display user messages, attachments, side-by-side model response cards, and consensus summary sections for every turn in a discussion.

#### Scenario: User views active conversation turn
- **GIVEN** a discussion turn with responses from multiple models
- **WHEN** the turn renders in `ChatMessages.svelte`
- **THEN** user prompts appear in message bubbles, model answers render in side-by-side cards, and the consensus synthesis card displays at the bottom

### Requirement: Floating Jump to Latest Button
The chat view SHALL render a floating "Jump to Latest" scroll button whenever the user is scrolled up during active streaming.

#### Scenario: User scrolls up while models are streaming
- **GIVEN** active model streaming and `atBottom == false`
- **WHEN** new text deltas arrive
- **THEN** the "Jump to Latest" button appears, allowing 1-click smooth scrolling to the bottom
