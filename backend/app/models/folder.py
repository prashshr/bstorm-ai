from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


folder_discussions = Table(
    "folder_discussions",
    Base.metadata,
    Column("folder_id", Integer, ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True),
    Column("discussion_id", Integer, ForeignKey("discussions.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, default=0),
)


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), default="Untitled folder")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    discussions = relationship(
        "Discussion",
        secondary=folder_discussions,
        backref="folders",
        order_by="folder_discussions.c.position",
    )
