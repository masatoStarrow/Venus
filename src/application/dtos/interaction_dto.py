"""
DTOs for Interaction operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class CreateInteractionDTO:
    client_id: UUID
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


@dataclass
class UpdateInteractionDTO:
    type: str | None = None
    channel: str | None = None
    status: str | None = None
    subject: str | None = None
    notes: str | None = None
    internal_notes: str | None = None
    outcome: str | None = None
    follow_up_date: datetime | None = None
    duration_minutes: int | None = None


@dataclass
class CloseInteractionDTO:
    outcome: str | None = None
