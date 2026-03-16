"""
Use case: Delete an attachment (S3 object + DB row).
"""

from uuid import UUID

from src.domain.exceptions import AttachmentNotFoundError, InteractionNotFoundError
from src.domain.ports.attachment_repository import AttachmentRepository
from src.domain.ports.file_storage import FileStorage
from src.domain.ports.interaction_repository import InteractionRepository


class DeleteAttachment:
    def __init__(
        self,
        interaction_repository: InteractionRepository,
        attachment_repository: AttachmentRepository,
        file_storage: FileStorage,
    ) -> None:
        self._interaction_repo = interaction_repository
        self._attachment_repo = attachment_repository
        self._file_storage = file_storage

    async def execute(self, interaction_id: UUID, attachment_id: UUID) -> None:
        interaction = await self._interaction_repo.get_by_id(interaction_id)
        if interaction is None or interaction.is_deleted:
            raise InteractionNotFoundError()

        attachment = await self._attachment_repo.get_by_id(attachment_id)
        if attachment is None or attachment.interaction_id != interaction_id:
            raise AttachmentNotFoundError()

        await self._file_storage.delete(attachment.file_key)
        await self._attachment_repo.delete(attachment_id)
