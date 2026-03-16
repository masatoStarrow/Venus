"""
Domain entity: AuditEntry — tracks field-level changes on interactions.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class AuditEntry:
    id: UUID
    interaction_id: UUID
    edited_by: UUID
    field_name: str
    previous_value: str | None = None
    new_value: str | None = None
    edited_at: datetime | None = None
