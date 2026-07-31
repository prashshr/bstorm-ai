# Specification: Routing

## Purpose
Specifies the provider client factory (`factory.py`), URL endpoint canonicalization (`endpoints.py`), and DTO transformation for multi-provider API requests.

## Requirements

### Requirement: Factory Client Instantiation
The backend SHALL instantiate the appropriate `ProviderClient` subclass based on the provider key alias.

#### Scenario: User dispatches request to Anthropic model
- **GIVEN** a request specifying provider key `"anthropic"`
- **WHEN** `factory.get_provider_client()` is invoked
- **THEN** it returns an instance of `AnthropicClient` configured with decrypted API keys

### Requirement: Endpoint Normalization
The system SHALL canonicalize custom provider base URLs into valid completion endpoints using `normalize_endpoint_url()`.

#### Scenario: User enters custom base URL for Ollama
- **GIVEN** a user-configured endpoint URL `"http://localhost:11434"`
- **WHEN** the provider client prepares outbound request
- **THEN** the URL is normalized to `"http://localhost:11434/v1/chat/completions"`
