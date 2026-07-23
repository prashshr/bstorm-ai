from __future__ import annotations
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    encryption_salt: Mapped[str | None] = mapped_column(String(100), nullable=True)
    master_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adc_json_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    """Server-side record of an issued refresh token (mobile clients).
    Only the SHA-256 hash is stored; the raw token is shown to the client once.
    Supports revocation (logout) and device scoping."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True)
    sid: Mapped[str] = mapped_column(String(64), index=True)
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionStore(Base):
    """Persistent store of mobile session UEKs, keyed by opaque sid.

    Mobile clients receive an access token carrying only a `sid`; the server
    resolves the user's UEK from here. Persisting it (encrypted with the
    server key) means UEKs survive backend process restarts, so the discussion
    list keeps decrypting titles after a pod restart instead of showing
    encrypted blobs.
    """

    __tablename__ = "session_store"

    sid: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    uek_encrypted: Mapped[str] = mapped_column(Text)
    exp: Mapped[float] = mapped_column(default=0.0)


class Discussion(Base):
    __tablename__ = "discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="new")
    state_json: Mapped[str] = mapped_column(Text, default="")  # Full discussion state
    retrieved_context_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="discussion", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discussion_id: Mapped[int] = mapped_column(ForeignKey("discussions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    model: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="assistant")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    discussion = relationship("Discussion", back_populates="messages")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
