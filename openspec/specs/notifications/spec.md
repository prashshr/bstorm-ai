# Specification: Notifications

## Purpose
Specifies progress steppers (`ProgressStepper.svelte`), RAG context status badges, error warning banners, and real-time execution event logging (`DebugPanel.svelte`).

## Requirements

### Requirement: Execution Phase Stepper
The UI SHALL display progress steppers indicating current turn phase (`searching`, `routing`, `streaming`, `consensus`).

#### Scenario: Turn execution starts
- **GIVEN** a submitted user prompt
- **WHEN** backend phase updates occur
- **THEN** progress stepper highlights active phase with animated indicator

### Requirement: Real-Time Debug Event Logging
The frontend SHALL record API events, token errors, and SSE messages into `debug.svelte.ts` store for display in `DebugPanel.svelte`.

#### Scenario: SSE stream error occurs
- **GIVEN** an error event during streaming
- **WHEN** event handler catches error
- **THEN** entry is logged to debug store and visible in the collapsible Debug Panel
