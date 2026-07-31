# Specification: Streaming

## Purpose
Specifies Server-Sent Events (SSE) streaming formats (`data: {"type": "delta"|"done"|"error"|"phase"}`), line buffering, and ReadableStream event parsing.

## Requirements

### Requirement: Real-Time SSE Chunk Transmission
The backend proxy SHALL stream completion deltas over HTTP Server-Sent Events (`text/event-stream`).

#### Scenario: Provider API streams response token
- **GIVEN** an active proxy chat stream request
- **WHEN** the upstream provider yields text tokens
- **THEN** the backend transmits SSE frames `data: {"type": "delta", "content": "chunk"}\n\n` to the client

### Requirement: Upstream Stream Error Isolation
Upstream provider 401/500 errors during streaming SHALL be captured as SSE error events without terminating or logging out the user's platform session.

#### Scenario: Upstream provider returns 401 during SSE stream
- **GIVEN** an active SSE stream connection
- **WHEN** the upstream provider API returns 401 Unauthorized
- **THEN** the backend emits `data: {"type": "error", "error": "Provider authorization failed"}` and closes the stream gracefully
