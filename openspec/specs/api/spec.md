# Specification: API

## Purpose
Specifies the FastAPI REST endpoints and SSE streaming contracts for Auth, Providers, Discussions, Folders, Proxy Chat, and Admin operations.

## Requirements

### Requirement: OpenAPI Contract Validation
API endpoints SHALL validate JSON request DTOs using Pydantic v2 schemas and return standard error responses on failure.

#### Scenario: Client submits invalid JSON payload
- **GIVEN** an endpoint receiving invalid JSON
- **WHEN** Pydantic validation fails
- **THEN** backend returns HTTP 422 Unprocessable Entity with field error details

### Requirement: Stream Response Headers
The proxy streaming endpoint (`POST /api/proxy/chat/stream`) SHALL return HTTP header `Content-Type: text/event-stream`.

#### Scenario: Client initiates SSE stream request
- **GIVEN** request to `/api/proxy/chat/stream`
- **WHEN** backend accepts request
- **THEN** response headers specify `text/event-stream` and disable response caching
