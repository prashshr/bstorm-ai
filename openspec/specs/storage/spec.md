# Specification: Storage

## Purpose
Specifies zero-knowledge payload data encryption at rest using User Encryption Keys (UEK) and AES-256-Fernet, and mobile Android session store persistence.

## Requirements

### Requirement: Field-Level Fernet Encryption
Prompts, response contents, RAG contexts, provider API keys, and search history SHALL be Fernet-encrypted before database insert/update.

#### Scenario: User saves API key
- **GIVEN** plaintext API key entered by user
- **WHEN** backend persists credential
- **THEN** key is encrypted with AES-256-Fernet using user's UEK and stored as ciphertext

### Requirement: Mobile Session Store Mapping
The backend SHALL maintain a `SessionStore` table mapping session IDs (`sid`) to encrypted UEK envelopes for mobile native client persistence.

#### Scenario: Android app resumes session
- **GIVEN** valid session ID (`sid`) in mobile request header
- **WHEN** API route executes
- **THEN** backend looks up decrypted UEK from session store to process payload
