# Specification: Settings

## Purpose
Specifies discussion execution parameters, response/summary format presets ("Compact", "Elaborate", "Custom", "None"), timeout limits, max tokens, RAG modes, and Deep Research toggles.

## Requirements

### Requirement: Preset Instruction Auto-Fill
Selecting a response or summary format preset SHALL auto-fill the corresponding instruction text.

#### Scenario: User selects Compact summary preset
- **GIVEN** `ChatInput.svelte` advanced settings panel open
- **WHEN** user selects "Compact" summary preset
- **THEN** `summaryFormatText` populates with the pre-configured concise consensus instruction

### Requirement: Parameter Bound Constraints
Response timeout SHALL be constrained between 10s and 300s, and max tokens constrained between 500 and 16,000.

#### Scenario: User configures timeout
- **GIVEN** timeout input field in settings
- **WHEN** user enters a value
- **THEN** system enforces valid ranges (10–300s) before dispatch
