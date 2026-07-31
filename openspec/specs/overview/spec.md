# Specification: Overview

## Purpose
AI-Ensemble is an enterprise-grade multi-provider AI discussion and consensus platform. It allows users to prompt multiple Large Language Models (LLMs) simultaneously, observe their parallel streaming responses, and synthesize an automated consensus summary across model outputs.

## Requirements

### Requirement: Multi-Provider LLM Parallel Execution
The system SHALL dispatch user prompts concurrently to multiple selected AI providers (OpenAI, Anthropic, Gemini, Vertex AI, Perplexity, DeepSeek, Groq, Ollama, Requesty, Mammouth) and stream their delta outputs in real-time.

#### Scenario: User submits prompt to multiple models
- **GIVEN** an authenticated user with configured AI provider API keys
- **WHEN** the user selects 2 or more models and submits a prompt
- **THEN** the system dispatches parallel requests to each provider and streams response deltas to the UI

### Requirement: Zero-Knowledge Envelope Encryption
The system SHALL encrypt all user prompts, model responses, provider credentials, and search history at rest using AES-256-Fernet encryption keys derived from the user's password via PBKDF2.

#### Scenario: Prompt and credential persistence
- **GIVEN** an active user session with derived User Encryption Key
- **WHEN** the user saves API credentials or submits chat prompts
- **THEN** payload data is encrypted into Fernet ciphertext before being saved in the database
