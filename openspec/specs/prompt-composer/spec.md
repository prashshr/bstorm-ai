# Specification: Prompt Composer

## Purpose
Specifies the single-card bottom-docked prompt composer component (`ChatInput.svelte`), full-width top drag handle, 4-sided rectangular outline, file attachments, advanced settings popover, and mobile auto-collapse.

## Requirements

### Requirement: Single-Card Bottom Dock Container
The prompt composer SHALL consist of a single rectangular card container anchored to `bottom: 0` without nested inner boxes or empty gaps above the editor.

#### Scenario: User inspects composer card
- **GIVEN** `ChatInput.svelte` rendered on screen
- **WHEN** the user focuses or types inside the card
- **THEN** the entire 4-sided card outline highlights with an accent border, and the editor fills vertical space directly

### Requirement: Bounded Upward Height Dragging
Dragging the top handle SHALL adjust composer height upwards bounded between `130px` and `min(380px, 42vh)`.

#### Scenario: User drags top handle upwards
- **GIVEN** an expanded composer card
- **WHEN** the user drags the top handle upwards
- **THEN** height increases up to max `42vh`, preventing the composer from reaching or covering the centered homepage text

### Requirement: Android / Mobile Auto-Collapse
When a discussion is running (`discussion.running == true`), the composer SHALL automatically collapse to a compact 44px bar on mobile devices.

#### Scenario: Active streaming on Android app
- **GIVEN** models actively streaming answers on mobile/Android
- **WHEN** `discussion.running` becomes true
- **THEN** the composer automatically minimizes to 44px with an animated "Models responding... Pull up to reply" indicator
