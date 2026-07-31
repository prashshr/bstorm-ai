# Specification: Conversations

## Purpose
Specifies discussion CRUD operations, turn history persistence, folder organization, date-based session grouping, and chat transcript exports.

## Requirements

### Requirement: Zero-Knowledge Discussion Persistence
Discussion titles, questions, model responses, and RAG contexts SHALL be encrypted with the user's User Encryption Key (UEK) before being written to the database.

#### Scenario: User saves a new discussion turn
- **GIVEN** a completed discussion turn
- **WHEN** backend persists the records to SQLite/PostgreSQL
- **THEN** prompt text and model messages are encrypted with AES-256-Fernet using the user's UEK

### Requirement: Hierarchical Folder Assignment
Users SHALL be able to create custom folders and assign/remove discussions within folders.

#### Scenario: User moves discussion to folder
- **GIVEN** a discussion and an existing folder
- **WHEN** the user assigns the discussion to the folder
- **THEN** an entry is created in the `folder_discussions` table and the sidebar updates hierarchically
