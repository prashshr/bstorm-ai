# Specification: Database

## Purpose
Specifies relational database persistence, SQLAlchemy 2.0 ORM schemas (`User`, `Discussion`, `Message`, `ProviderCredential`, `Folder`), SQLite/PostgreSQL support, and Alembic migrations.

## Requirements

### Requirement: Relational Model Mappings
The database SHALL define ORM models with foreign key constraints and user ownership relationships.

#### Scenario: Database schema initialization
- **GIVEN** database engine setup (`app/db/session.py`)
- **WHEN** application starts
- **THEN** SQLAlchemy ORM initializes engine tables and validates schema column compatibility

### Requirement: Alembic Schema Version Control
Database schema modifications SHALL be versioned and applied via Alembic migration scripts.

#### Scenario: Running migration upgrades
- **GIVEN** pending database migrations
- **WHEN** `alembic upgrade head` executes
- **THEN** database schema updates to latest revision without data loss
