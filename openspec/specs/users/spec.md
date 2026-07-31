# Specification: Users

## Purpose
Specifies user registration, account metadata schema, administrative user listing, user deletion, and cascading resource cleanup.

## Requirements

### Requirement: User Account Registration
The system SHALL support user registration via email and password, creating a unique salt and password hash.

#### Scenario: New user registers
- **GIVEN** a new email address and password
- **WHEN** client posts to `POST /api/auth/register`
- **THEN** system hashes password with bcrypt, generates 16-byte salt, and saves user account

### Requirement: Cascading User Deletion
Deleting a user account SHALL permanently purge all associated provider credentials, discussions, messages, and folders.

#### Scenario: Admin deletes user account
- **GIVEN** an active user account
- **WHEN** admin executes `DELETE /api/admin/users/{id}`
- **THEN** user record and all cascading resources are removed from the database
