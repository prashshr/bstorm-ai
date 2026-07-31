# Specification: Model Selection

## Purpose
Specifies model discovery, Vertex AI Smart Discovery across GCP regions, vision vs text-only model capability classification, and model selection state management.

## Requirements

### Requirement: Dynamic Model Discovery
The system SHALL query provider `/models` endpoints or execute GCP Vertex AI regional catalog probing to return accessible model IDs.

#### Scenario: User discovers models for a provider
- **GIVEN** a verified provider credential
- **WHEN** the user selects the provider in `ModelSelector.svelte`
- **THEN** backend fetches available model IDs and populates the selectable model list

### Requirement: Vision Model Capability Classification
The system SHALL classify models using regex patterns (`VISION_RE` vs `TEXT_ONLY_RE`) and display inline warnings when images are attached to text-only models.

#### Scenario: User attaches image with DeepSeek text model selected
- **GIVEN** DeepSeek (text-only model) selected in composer
- **WHEN** the user attaches an image file
- **THEN** `ChatInput.svelte` displays a vision warning banner suggesting a vision model (GPT-4o, Gemini, Claude 3.5)
