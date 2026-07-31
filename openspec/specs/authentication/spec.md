# Specification: Authentication

## Purpose
Specifies user account authentication, PBKDF2-HMAC-SHA256 User Encryption Key (UEK) derivation, JWT access/refresh token rotation, and Android native session store mapping.

## Requirements

### Requirement: PBKDF2 Key Derivation
The system SHALL derive a 32-byte User Encryption Key (UEK) from the user's plaintext password and 16-byte random salt using PBKDF2-HMAC-SHA256 with 600,000 iterations.

#### Scenario: User logs in with password
- **GIVEN** a registered user email and password
- **WHEN** the user submits `POST /api/auth/login`
- **THEN** backend verifies password hash with bcrypt and derives 32-byte UEK via PBKDF2 600,000 iterations

### Requirement: JWT Access and Refresh Token Rotation
The backend SHALL issue short-lived JWT access tokens (60 minutes) and long-lived refresh tokens (30 days) supporting token rotation and revocation.

#### Scenario: Client rotates refresh token
- **GIVEN** a valid refresh token
- **WHEN** client posts to `POST /api/auth/refresh`
- **THEN** backend revokes old refresh token, registers new refresh token, and issues fresh access token
