"""
Use case: Upload an attachment for an interaction.
Validates file, uploads to S3, saves metadata in DB.
"""

import uuid
from uuid import UUID

from src.domain.entities.attachment import Attachment
from src.domain.exceptions import (
    InteractionNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from src.domain.ports.attachment_repository import AttachmentRepository
from src.domain.ports.file_storage import FileStorage
from src.domain.ports.interaction_repository import InteractionRepository

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.ms-excel",
}


class UploadAttachment:
    def __init__(
        self,
        interaction_repository: InteractionRepository,
        attachment_repository: AttachmentRepository,
        file_storage: FileStorage,
    ) -> None:
        self._interaction_repo = interaction_repository
        self._attachment_repo = attachment_repository
        self._storage = file_storage

    async def execute(
        self,
        *,
        interaction_id: UUID,
        uploaded_by: UUID,
        file_name: str,
        content_type: str,
        file_data: bytes,
        context: str = "internal_note",
    ) -> Attachment:
        interaction = await self._interaction_repo.get_by_id(interaction_id)
        if interaction is None or interaction.is_deleted:
            raise InteractionNotFoundError()

        if len(file_data) > MAX_FILE_SIZE:
            raise FileTooLargeError()

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise InvalidFileTypeError()

        attachment_id = uuid.uuid4()
        file_key = f"attachments/{interaction_id}/{attachment_id}/{file_name}"

        await self._storage.upload(file_key, file_data, content_type)

        attachment = Attachment(
            id=attachment_id,
            interaction_id=interaction_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_key=file_key,
            content_type=content_type,
            file_size=len(file_data),
            context=context,
        )
        return await self._attachment_repo.save(attachment)
