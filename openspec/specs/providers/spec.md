# Specification: Providers

## Purpose
Specifies AI provider credential storage, API key Fernet encryption, custom endpoint normalization, GCP Vertex AI service account ADC support, and connection testing.

## Requirements

### Requirement: Encrypted Provider Credential Storage
The system SHALL encrypt user-configured provider API keys and ADC service account JSONs at rest using the user's User Encryption Key (UEK).

#### Scenario: User saves API key for OpenRouter
- **GIVEN** an authenticated user
- **WHEN** the user submits an API key in `ProviderForm.svelte`
- **THEN** the key is Fernet-encrypted before saving in `provider_credentials` database table

### Requirement: Connection Testing Without Session Invalidation
Testing a provider API key (`POST /api/providers/{key}/test`) SHALL catch upstream authorization errors without logging out the user's platform session.

#### Scenario: User tests an invalid provider key
- **GIVEN** a saved provider configuration with an expired API key
- **WHEN** the user clicks the test connection button
- **THEN** backend returns an actionable error message while preserving the user's login session
