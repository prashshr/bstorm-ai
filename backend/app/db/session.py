from collections.abc import Generator
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger("ai_ensemble.db")

_IS_SQLITE = settings.database_url.startswith("sqlite")

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if _IS_SQLITE else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        """SQLite ignores foreign keys unless they are enabled per connection.

        The models declare ``ondelete="CASCADE"`` on their foreign keys, so
        without this pragma deleting a user or discussion leaves orphaned
        child rows (messages, credentials, refresh tokens, sessions).
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Schema drift fallback: ensure columns exist on existing SQLite DBs.
    # Alembic is now the source of truth for new installs; this is a
    # compatibility shim for pre-migration SQLite deployments.
    if settings.database_url.startswith("sqlite"):
        db = SessionLocal()
        try:
            db.execute(text("ALTER TABLE discussions ADD COLUMN state_json TEXT DEFAULT ''"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("ALTER TABLE users ADD COLUMN encryption_salt TEXT"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("ALTER TABLE users ADD COLUMN master_key_encrypted TEXT"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("ALTER TABLE provider_credentials ADD COLUMN label VARCHAR(100)"))
            db.commit()
        except Exception:
            db.rollback()

        # Ensure is_admin column exists on older SQLite databases
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    # Migrate legacy admin: set is_admin=True for the hardcoded admin account
    # if it exists, then log instructions for creating a new admin.
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.email == "admin@local.ai-ensemble").first()
        if admin and not admin.is_admin:
            admin.is_admin = True
            db.commit()
            logger.info("Migrated legacy admin account: admin@local.ai-ensemble now has is_admin=True")
        if not admin:
            logger.warning(
                "No admin account found. Create one with: "
                "POST /api/auth/register with a secure password, then "
                " UPDATE users SET is_admin=1 WHERE email='<your-email>';"
            )
    finally:
        db.close()
