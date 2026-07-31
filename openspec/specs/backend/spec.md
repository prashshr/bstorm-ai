# Specification: Backend

## Purpose
Specifies the FastAPI backend web API server, rate limiting, authentication dependency injection, zero-knowledge encryption, and provider routing services.

## Requirements

### Requirement: OpenAPI REST & SSE Endpoint Routes
The backend SHALL expose REST endpoints and SSE streams for user authentication, provider credentials, discussions, folders, and proxy chat.

#### Scenario: Backend receives chat stream request
- **GIVEN** an authenticated HTTP POST request to `/api/proxy/chat/stream`
- **WHEN** the payload is validated and credentials decrypted
- **THEN** FastAPI returns an `EventSourceResponse` or `StreamingResponse` emitting SSE event frames

### Requirement: Rate Limiting Guardrails
The system SHALL enforce route-level rate limits using SlowAPI to prevent API abuse and DDoS attacks.

#### Scenario: Client exceeds rate limit
- **GIVEN** a client exceeding the configured endpoint rate limit
- **WHEN** additional requests are sent to the API
- **THEN** SlowAPI returns HTTP 429 Too Many Requests
