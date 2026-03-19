"""
Domain entity: Interaction — pure Python dataclass, no framework imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Interaction:
    id: UUID
    client_id: UUID
    agent_id: UUID
    type: str
    channel: str
    subject: str
    status: str = "pending"
    notes: str | None = None
    internal_notes: str | None = None
    outcome: str | None = None
    interaction_date: datetime | None = None
    follow_up_date: datetime | None = None
    duration_minutes: int | None = None
    is_deleted: bool = False
    last_edited_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
