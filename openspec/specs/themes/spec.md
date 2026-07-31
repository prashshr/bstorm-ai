# Specification: Themes

## Purpose
Specifies CSS custom design tokens (`app.css`), dark/light theme switching (`data-theme`), high-contrast accessible focus rings, and PDF/print export formatting.

## Requirements

### Requirement: Dark and Light Theme Switching
The application SHALL support instant switching between dark (`:root`) and light (`data-theme="light"`) CSS design tokens.

#### Scenario: User toggles theme button
- **GIVEN** dark theme active by default
- **WHEN** user clicks sun/moon icon in header
- **THEN** system sets `data-theme="light"` on `document.documentElement` and persists choice in local storage

### Requirement: PDF Export Print Layout
The application SHALL apply `@media print` styles hiding UI bars and rendering a clean single-column transcript for PDF exports.

#### Scenario: User prints chat transcript
- **GIVEN** an active discussion
- **WHEN** user clicks Export -> Print / PDF
- **THEN** header, sidebar, and composer hide, and transcript renders on white background with high contrast
