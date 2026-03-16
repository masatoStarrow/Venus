"""
Domain entity: Attachment — metadata for files uploaded to S3.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Attachment:
    id: UUID
    interaction_id: UUID
    uploaded_by: UUID
    file_name: str
    file_key: str
    content_type: str
    file_size: int
    context: str = "internal_note"
    created_at: datetime | None = None
