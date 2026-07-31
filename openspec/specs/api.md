# Specification: REST & SSE API Interfaces

# Purpose
The API subsystem defines the complete OpenAPI v3 REST and Server-Sent Events (SSE) contract implemented by the FastAPI backend, detailing endpoints, request DTOs, response schemas, and error status codes.

# Responsibilities
- Serve structured REST endpoints for authentication, provider management, discussion orchestration, folders, and administration.
- Stream model responses via SSE endpoint (`POST /api/proxy/chat/stream`).
- Validate input request bodies via Pydantic v2 schemas.
- Return standard RFC 7807 error responses (`ApiError`: `status`, `detail`).

# Endpoint Summary

### Authentication Routes (`/api/auth`)
- `POST /api/auth/register`: Register new user account.
- `POST /api/auth/login`: Authenticate user, derive UEK, return access & refresh tokens.
- `POST /api/auth/refresh`: Rotate refresh token and issue new access token.
- `POST /api/auth/logout`: Revoke refresh token and invalidate mobile session.

### Provider Routes (`/api/providers`)
- `GET /api/providers`: List user's saved provider credentials.
- `POST /api/providers`: Create or update provider configuration.
- `DELETE /api/providers/{provider_key}`: Delete provider credential.
- `GET /api/providers/{provider_key}/models`: Dynamically discover model IDs.
- `POST /api/providers/{provider_key}/test`: Test provider API key connectivity.

### Discussion Routes (`/api/discussions`)
- `GET /api/discussions`: List user discussions.
- `POST /api/discussions`: Create new multi-model discussion turn.
- `GET /api/discussions/{id}`: Retrieve single discussion details.
- `PUT /api/discussions/{id}`: Update discussion title or metadata.
- `DELETE /api/discussions/{id}`: Delete discussion.
- `GET /api/discussions/{id}/messages`: List turn message records.
- `POST /api/discussions/{id}/research`: Trigger automated follow-up research turn.

### Folder Routes (`/api/folders`)
- `GET /api/folders`: List custom user folders.
- `POST /api/folders`: Create folder.
- `PUT /api/folders/{id}`: Rename folder or update position.
- `DELETE /api/folders/{id}`: Remove folder.
- `POST /api/folders/{id}/discussions/{discussion_id}`: Assign discussion to folder.
- `DELETE /api/folders/{id}/discussions/{discussion_id}`: Unassign discussion from folder.

### Proxy Routes (`/api/proxy`)
- `POST /api/proxy/chat`: Non-streaming multi-model chat execution.
- `POST /api/proxy/chat/stream`: Server-Sent Events (SSE) streaming chat execution.

### Admin Routes (`/api/admin`)
- `GET /api/admin/users`: List all platform users (`is_admin` required).
- `DELETE /api/admin/users/{id}`: Delete user account (`is_admin` required).

# Public Interfaces
- Base URL: `https://ai-ensemble.samkhya.cloud/api`
- OpenAPI JSON: `https://ai-ensemble.samkhya.cloud/openapi.json`
- Interactive Swagger UI: `https://ai-ensemble.samkhya.cloud/docs`

# Dependencies
- `FastAPI`, `Pydantic v2`, `python-jose`.

# Configuration
- OpenAPI title: `"AI Ensemble API"`, version: `"4.2.0"`.

# Current Behaviour
Endpoints return JSON DTOs or text/event-stream chunks. Uncaught exceptions return standard error payloads (`{"detail": "..."}`).

# Constraints
- Requests must include `Content-Type: application/json` header.

# Future Considerations
- API versioning under `/api/v1/*` path prefix.

# Related Specs
- [Backend Spec](backend.md)
- [Authentication Spec](authentication.md)
- [Streaming Spec](streaming.md)
