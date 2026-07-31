# Specification: Authorization

## Purpose
Specifies Role-Based Access Control (RBAC), user resource ownership isolation, admin privileges, and dependency injection authorization guards.

## Requirements

### Requirement: Resource Ownership Isolation
The backend SHALL restrict access to discussions, folders, and provider credentials strictly to the owner user (`user_id`).

#### Scenario: User queries discussion by ID
- **GIVEN** an authenticated user
- **WHEN** user requests a discussion ID owned by another user
- **THEN** backend returns HTTP 404 Not Found to prevent resource enumeration

### Requirement: Administrative Privilege Guard
Admin endpoints (`/api/admin/*`) SHALL assert that `user.is_admin` is True.

#### Scenario: Non-admin user calls admin route
- **GIVEN** an authenticated non-admin user
- **WHEN** user calls `GET /api/admin/users`
- **THEN** backend returns HTTP 403 Forbidden
