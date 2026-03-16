"""
SQLAlchemy ORM model: interaction_attachments table.
Stores metadata only — actual files live in S3.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.connection import Base


class AttachmentModel(Base):
    __tablename__ = "interaction_attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    interaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[str] = mapped_column(
        String(20), nullable=False, default="internal_note",
        server_default=text("'internal_note'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_attachments_interaction_id", "interaction_id"),
        Index("idx_attachments_uploaded_by", "uploaded_by"),
    )

    def __repr__(self) -> str:
        return f"<AttachmentModel {self.file_name} ({self.content_type})>"
