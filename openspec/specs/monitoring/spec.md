# Specification: Monitoring

## Purpose
Specifies GET `/health` endpoint probe readiness/liveness checks, database connection checks, and rate limit telemetry.

## Requirements

### Requirement: Health Probe Endpoint
The backend SHALL expose `GET /health` returning `{"status": "ok"}` with HTTP 200 OK.

#### Scenario: Kubernetes liveness probe executes
- **GIVEN** backend pod running in cluster
- **WHEN** kubelet issues HTTP GET to `/health`
- **THEN** endpoint responds in <500ms with `{"status": "ok"}`

### Requirement: Rate Limited Probe Protection
The `/health` endpoint SHALL be rate-limited to 60 requests per minute per client IP.

#### Scenario: Excessive health probe calls
- **GIVEN** client exceeding 60 calls/min
- **WHEN** probe checks executed
- **THEN** SlowAPI enforces rate limit rule
