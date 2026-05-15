"""
SQLAlchemy ORM model: interactions table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.connection import Base


class InteractionModel(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default=text("'pending'")
    )

    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(255), nullable=True)

    interaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    follow_up_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    last_edited_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    __table_args__ = (
        Index("idx_interactions_type", "type"),
        Index("idx_interactions_status", "status"),
        Index("idx_interactions_date", interaction_date.desc()),
        Index("idx_interactions_client_date", "client_id", interaction_date.desc()),
    )

    def __repr__(self) -> str:
        return f"<InteractionModel {self.type} [{self.status}] — {self.subject[:40]}>"
