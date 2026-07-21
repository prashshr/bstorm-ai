from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import models  # noqa: F401
    from app.core.security import get_password_hash

    Base.metadata.create_all(bind=engine)

    # Schema drift fallback: ensure state_json column exists on existing SQLite DBs
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
        finally:
            db.close()

    # Seed default admin user
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.email == "admin@local.ai-ensemble").first()
        if not admin:
            admin = models.User(
                email="admin@local.ai-ensemble",
                password_hash=get_password_hash("arhatadmin"),
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
