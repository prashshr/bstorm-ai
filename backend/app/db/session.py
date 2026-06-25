from collections.abc import Generator

from sqlalchemy import create_engine
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
