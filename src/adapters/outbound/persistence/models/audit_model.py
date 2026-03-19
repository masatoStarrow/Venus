"""
SQLAlchemy ORM model: interaction_audit table.
Tracks field-level changes on interactions (HU-11 / HU-12).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.connection import Base


class AuditModel(Base):
    __tablename__ = "interaction_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    interaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False
    )
    edited_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    edited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_audit_interaction_id", "interaction_id"),
        Index("idx_audit_edited_by", "edited_by"),
    )

    def __repr__(self) -> str:
        return f"<AuditModel {self.field_name}: {self.previous_value} → {self.new_value}>"
