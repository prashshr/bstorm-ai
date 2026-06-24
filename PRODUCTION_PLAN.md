# AI Ensemble Production Plan

This plan focuses on making AI Ensemble production-ready for:

- domain: https://ai-ensemble.samkhya.cloud
- strict surface-area minimization (only required exposure)
- local user login with per-user isolated data and provider keys
- multi-provider support (OpenAI-compatible + major providers)

## 1. Target Architecture

Client Browser -> Reverse Proxy (TLS) -> Backend API -> Provider APIs

- Reverse proxy terminates TLS and forwards only allowed routes.
- Backend is the only component that calls provider APIs.
- Frontend never stores provider keys directly in localStorage.

## 2. Domain + Let's Encrypt

Preferred: Caddy (automatic cert issuance and renewal).

### DNS

- Create `A` or `AAAA` record for `ai-ensemble.samkhya.cloud` to server IP.
- Keep DNS TTL low during initial rollout.

### Caddyfile example

```caddy
ai-ensemble.samkhya.cloud {
    encode zstd gzip

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
    }

    # Serve static frontend assets
    handle_path / {
        root * /opt/ai-ensemble/web
        try_files {path} /ai-ensemble-v5.html
        file_server
    }

    # API only through backend
    handle /api/* {
        reverse_proxy 127.0.0.1:8080
    }

    # Block debug paths
    handle /debug* {
        respond "Not found" 404
    }

    log {
        output file /var/log/caddy/ai-ensemble.log
        format json
    }
}
```

## 3. Exposure Minimization

- Publicly expose only `80` and `443`.
- Bind backend on `127.0.0.1:8080` (or private network only).
- No open debug endpoints.
- No static serving of logs, HAR files, stack traces, or config files.
- Enforce request size limits and rate limits.

Firewall baseline:

- Allow: `22/tcp` (admin), `80/tcp`, `443/tcp`
- Deny all other inbound ports

## 4. Authentication + Per-User Isolation

Use local auth with a database-backed session model.

Core tables:

- `users`: id, email/username, password_hash, created_at, last_login_at
- `sessions`: id, user_id, expires_at, ip_hash, user_agent_hash
- `provider_keys`: id, user_id, provider, key_encrypted, created_at
- `discussions`: id, user_id, title, question, created_at, status
- `messages`: id, discussion_id, user_id, round, model, role, content, usage
- `search_history`: id, user_id, query, filters_json, created_at

Requirements:

- Password hashing: Argon2id (or bcrypt with proper cost)
- HTTP-only, Secure, SameSite cookies for session
- CSRF protection for state-changing requests
- Every read/write filtered by `user_id`
- Never return decrypted keys in API responses

## 5. Provider Abstraction Layer

Implement backend provider adapters with a unified interface:

```text
send_chat(request: UnifiedChatRequest, credentials: UserProviderCredential) -> UnifiedChatResponse
list_models(credentials) -> list[UnifiedModel]
```

Initial adapters:

- OpenAI
- Anthropic
- Google Gemini
- OpenRouter
- Azure OpenAI
- Generic OpenAI-compatible endpoint

Key points:

- Normalize model listing schema.
- Normalize usage metrics (prompt/completion tokens).
- Provider-specific retries and timeout policies.
- Optional fallback chain by user preference.

## 6. Security Controls

- CSP that disallows inline scripts where possible.
- Output sanitization for markdown rendering.
- Backend-side validation for all API payloads.
- Rate limit by IP and by user account.
- Brute-force login protection and account lockout/backoff.
- Audit logging for auth events and provider key changes.

## 7. Data + Secrets Management

- Store DB outside repository (`/var/lib/ai-ensemble` or managed DB).
- Secrets in environment/system secret manager, not git.
- Key encryption at rest with server-side master key.
- Regular encrypted backups for DB and key metadata.

## 8. Migration from Current Prototype

Current prototype stores history and API key material in browser localStorage.

Migration approach:

1. Introduce backend auth and user profile.
2. Add import endpoint to ingest local discussion history.
3. Remove localStorage API key usage from frontend.
4. Switch frontend fetches from provider endpoints to backend `/api/*`.

## 9. Implementation Sequence

1. Scaffold backend (`/api`) with auth, DB models, sessions.
2. Add provider adapter interface and OpenAI-compatible adapter first.
3. Add adapters: Anthropic, Google, OpenAI, OpenRouter, Azure.
4. Move existing frontend calls to backend endpoints.
5. Add per-user history and search endpoints.
6. Deploy behind Caddy with TLS and strict firewall.
7. Add tests and run penetration checklist.

## 10. Production Acceptance Checklist

- [ ] TLS valid and auto-renewing for `ai-ensemble.samkhya.cloud`
- [ ] Only `80/443` exposed publicly
- [ ] Login required for all user data operations
- [ ] Cross-user data access tests fail as expected (no leakage)
- [ ] Provider keys encrypted and never exposed to frontend
- [ ] Major providers functional through adapters
- [ ] Logs have no secrets and no raw keys
- [ ] Debug and non-essential files excluded from repo
