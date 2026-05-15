"""
Pydantic v2 schemas for Interaction request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects.channel import Channel
from src.domain.value_objects.interaction_status import InteractionStatus
from src.domain.value_objects.interaction_type import InteractionType


# ── Request schemas ──────────────────────────────────────────────────────

class CreateInteractionRequest(BaseModel):
    client_id: UUID
    type: InteractionType
    channel: Channel
    subject: str = Field(..., min_length=3, max_length=200, description="Asunto o título")
    status: InteractionStatus = InteractionStatus.PENDING
    notes: str | None = None
    internal_notes: str | None = None
    outcome: str | None = Field(None, max_length=255)
    interaction_date: datetime
    follow_up_date: datetime | None = None
    duration_minutes: int | None = Field(None, ge=1, le=600)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("El asunto no puede tener más de 200 caracteres")
        if len(v.strip()) < 3:
            raise ValueError("El asunto debe tener al menos 3 caracteres")
        return v


class UpdateInteractionRequest(BaseModel):
    type: InteractionType | None = None
    channel: Channel | None = None
    status: InteractionStatus | None = None
    subject: str | None = Field(None, min_length=3, max_length=200)
    notes: str | None = None
    internal_notes: str | None = None
    outcome: str | None = Field(None, max_length=255)
    follow_up_date: datetime | None = None
    duration_minutes: int | None = Field(None, ge=1, le=600)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 200:
                raise ValueError("El asunto no puede tener más de 200 caracteres")
            if len(v.strip()) < 3:
                raise ValueError("El asunto debe tener al menos 3 caracteres")
        return v


class CloseInteractionRequest(BaseModel):
    outcome: str | None = Field(None, max_length=255)


# ── Response schemas ─────────────────────────────────────────────────────

class InteractionResponse(BaseModel):
    id: UUID
    client_id: UUID
    agent_id: UUID
    type: str
    channel: str
    status: str
    subject: str
    notes: str | None
    internal_notes: str | None
    outcome: str | None
    interaction_date: datetime
    follow_up_date: datetime | None
    duration_minutes: int | None
    is_deleted: bool
    last_edited_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditEntryResponse(BaseModel):
    id: UUID
    interaction_id: UUID
    edited_by: UUID
    edited_at: datetime
    field_name: str
    previous_value: str | None
    new_value: str | None

    model_config = {"from_attributes": True}


class ClientSummaryResponse(BaseModel):
    client_id: str
    total_interactions: int
    interactions_last_30_days: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    completion_rate: float
    last_interaction_date: datetime | None
    next_follow_up_date: datetime | None
    open_tickets: int


class ClientMetricItem(BaseModel):
    client_id: str
    interaction_count: int
    last_interaction_date: datetime | None


class MetricsResponse(BaseModel):
    total_clients: int
    total_interactions: int
    avg_interactions_per_client: float
    per_client: list[ClientMetricItem]
