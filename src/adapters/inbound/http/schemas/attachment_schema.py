"""
Pydantic v2 schemas for Attachment request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: UUID
    interaction_id: UUID
    uploaded_by: UUID
    file_name: str
    file_key: str
    content_type: str
    file_size: int
    context: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentDownloadResponse(BaseModel):
    url: str
    file_name: str
    content_type: str
