# Specification: Relational Database Architecture

# Purpose
The Database subsystem specifies relational data persistence, SQLAlchemy 2.0 ORM model definitions, schema relationships, index optimization, connection pooling, and versioned Alembic schema migrations.

# Responsibilities
- Provide ORM mapping for core application domain entities (`User`, `ProviderCredential`, `Discussion`, `Message`, `Folder`, `folder_discussions`, `RefreshToken`, `SessionStore`, `SearchHistory`).
- Support dual database engines: SQLite (`sqlite:///./data/ai_ensemble.db`) for lightweight development/k3s hostPath and PostgreSQL for enterprise production.
- Execute runtime schema drift compatibility shims (`app/db/session.py`) to auto-patch missing database columns during version upgrades.
- Manage schema migrations via Alembic.

# Entity Relationship Diagram

```mermaid
erDiagram
    USER ||--o{ PROVIDER_CREDENTIAL : owns
    USER ||--o{ DISCUSSION : owns
    USER ||--o{ FOLDER : owns
    USER ||--o{ REFRESH_TOKEN : owns
    USER ||--o{ SESSION_STORE : owns
    USER ||--o{ SEARCH_HISTORY : owns

    DISCUSSION ||--o{ MESSAGE : contains
    FOLDER ||--o{ FOLDER_DISCUSSIONS : contains
    DISCUSSION ||--o{ FOLDER_DISCUSSIONS : assigned_to

    USER {
        int id PK
        string email
        string hashed_password
        string encryption_salt
        string master_key_encrypted
        boolean is_admin
        datetime created_at
    }

    PROVIDER_CREDENTIAL {
        int id PK
        int user_id FK
        string provider
        string api_key_encrypted
        string endpoint
        string label
        string project_id
        string region
        string adc_json_encrypted
    }

    DISCUSSION {
        int id PK
        int user_id FK
        string title_encrypted
        string question_encrypted
        string retrieved_context_encrypted
        boolean use_rag
        string state_json
        datetime created_at
        datetime updated_at
    }

    MESSAGE {
        int id PK
        int discussion_id FK
        string model
        string role
        string content_encrypted
        int tokens
        float duration_seconds
        int round_num
        datetime created_at
    }

    FOLDER {
        int id PK
        int user_id FK
        string name
        int position
        datetime created_at
    }

    FOLDER_DISCUSSIONS {
        int folder_id PK, FK
        int discussion_id PK, FK
        int position
    }
```

# Data Flow
1. FastAPI API routes execute database operations using SQLAlchemy async or scoped session factory (`get_db()`).
2. ORM queries execute with explicit filtering by `user_id` to enforce data isolation.
3. Database changes commit within transactional units of work.

# Internal Components
- `app/db/session.py`: Database engine instantiation, sessionmaker factory, and `init_db()` migration drift shim.
- `app/models/models.py`: Core ORM models.
- `app/models/folder.py`: Folder and folder_discussions ORM models.
- `alembic/versions/`: Versioned migration scripts (`3b5c8a1f6d20_add_refresh_tokens.py`, `4b12c9d7e3f1_add_folders.py`, etc.).

# Public Interfaces
- FastAPI Dependency: `db: Session = Depends(get_db)`
- Alembic CLI: `alembic upgrade head`, `alembic revision --autogenerate -m "..."`.

# Dependencies
- `sqlalchemy` `2.0.41`, `alembic` `1.16.2`, `psycopg2-binary` (for PostgreSQL).

# Configuration
- `DATABASE_URL`: Connection string in `.env` (`sqlite:///./data/ai_ensemble.db` or `postgresql://user:pass@host/dbname`).

# Current Behaviour
At application startup, `init_db()` initializes engine tables and applies runtime column drift patches before accepting API traffic.

# Constraints
- Foreign key constraints are enforced on SQLite via `PRAGMA foreign_keys=ON;`.

# Future Considerations
- Database connection pool health monitoring and slow query logging.

# Related Specs
- [Backend Spec](backend.md)
- [Storage Spec](storage.md)
