# Specification: User Account Management

# Purpose
The Users subsystem specifies user account lifecycle operations, account profile management, administrative user listing, user deletion, and encryption key re-wrapping upon password changes.

# Responsibilities
- Support user registration (`email`, `password`).
- Provide administrative user management (`GET /api/admin/users`, `DELETE /api/admin/users/{id}`).
- Maintain user account metadata (`created_at`, `is_admin`, `encryption_salt`, `master_key_encrypted`).
- Handle user account deletion, cascading deletion of associated provider credentials, discussions, messages, and folders.

# Architecture

```mermaid
graph TD
    AdminUI[Admin Interface] -->|GET /api/admin/users| AdminRoute[app/api/routes/admin.py]
    AdminRoute -->|Verify is_admin| AdminGuard[deps.get_admin_user]
    AdminGuard --> DB[(User ORM Model)]
    
    AdminUI -->|DELETE /api/admin/users/{id}| DeleteRoute[Delete User Route]
    DeleteRoute --> Cascade[Cascade Delete ProviderCredentials, Discussions, Folders]
    Cascade --> DB
```

# User Schema (`User` ORM Model)

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary key |
| `email` | String | Unique user email address |
| `hashed_password` | String | Bcrypt password hash |
| `encryption_salt` | String | Base64-encoded 16-byte random salt for PBKDF2 |
| `master_key_encrypted` | String | Encrypted UEK envelope master key |
| `is_admin` | Boolean | Administrative privilege flag |
| `created_at` | DateTime | User registration timestamp |

# Data Flow
1. Admin user sends `GET /api/admin/users`.
2. Admin route returns list of user DTOs (`UserResponse`: `id`, `email`, `is_admin`, `created_at`).
3. Admin user sends `DELETE /api/admin/users/{id}`.
4. Database executes cascading delete, purging all linked provider credentials, discussions, messages, and folders.

# Internal Components
- `app/models/models.py`: `User` SQLAlchemy ORM class.
- `app/api/routes/admin.py`: Administration routes.
- `app/schemas/auth.py`: User DTO schemas.

# Public Interfaces
- REST Endpoints:
  - `GET /api/admin/users`
  - `DELETE /api/admin/users/{user_id}`

# Dependencies
- `SQLAlchemy`, `FastAPI`, `bcrypt`.

# Configuration
- Admin initialization script or flag in `.env`.

# Current Behaviour
Users register via `/api/auth/register`. Admins can inspect active user accounts and purge accounts via administrative routes.

# Constraints
- Deleting a user permanently destroys all associated encrypted discussion records and provider credentials.

# Future Considerations
- Account password reset flow via email verification tokens.

# Related Specs
- [Authentication Spec](authentication.md)
- [Authorization Spec](authorization.md)
- [Database Spec](database.md)
