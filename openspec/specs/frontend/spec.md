# Specification: Frontend

## Purpose
Specifies the single-page application (SPA) architecture, reactive store state management, component layout hierarchy, and user interface rendering built with Svelte 5 and Vite.

## Requirements

### Requirement: Svelte 5 Runes Reactive State
The frontend SHALL manage application state using Svelte 5 Runes (`$state`, `$derived`, `$effect`) and class-based stores in `.svelte.ts` files.

#### Scenario: Real-time UI updates during SSE streaming
- **GIVEN** an active model stream receiving text deltas
- **WHEN** new stream events arrive from the backend
- **THEN** Svelte 5 Runes stores update reactive `$state`, triggering immediate DOM re-renders

### Requirement: Single-Container Layout Structure
The main application shell SHALL maintain a fixed top header, a fixed centered hero area, and a single bottom-docked prompt composer.

#### Scenario: Composer resizing on homepage
- **GIVEN** the homepage interface
- **WHEN** the user drags the top handle of the prompt composer
- **THEN** only the composer height changes upwards while the top header and hero text remain completely fixed
