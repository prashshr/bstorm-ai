# Specification: Model Selection

## Purpose
Specifies model discovery, capability classification, multi-provider model selection, and favorite model management.

## ADDED Requirements

### Requirement: Favorite Models Bookmarking
The system SHALL allow users to mark models as favorites by clicking a star icon located to the left of each model in the model selection list.

#### Scenario: User bookmarks a model as favorite
- **GIVEN** a model displayed in `ModelSelector.svelte` (e.g. `openrouter::openai/gpt-4o`)
- **WHEN** the user clicks the star icon button to the left of the model name
- **THEN** the model is added to the user's persistent favorite list and the star is rendered active/filled

### Requirement: Bottom Favorites Panel with Provider Disambiguation
The right panel SHALL provide a bottom section with upwards unfold/collapse displaying all favorited models. Because model names may be identical across different providers (e.g. `deepseek-chat` from OpenRouter vs custom Omniroute), each favorite item SHALL display the provider name in a light color tone subtag.

#### Scenario: User views and selects favorite models
- **GIVEN** favorited models across different providers in `ProviderPanel.svelte`
- **WHEN** the user unfolds the bottom Favorites section
- **THEN** favorited models are displayed with their distinct provider names in a light color tone and can be directly toggled into the active discussion selection
