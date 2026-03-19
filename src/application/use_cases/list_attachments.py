"""
Use case: List attachments for an interaction.
"""

from uuid import UUID

from src.domain.entities.attachment import Attachment
from src.domain.exceptions import InteractionNotFoundError
from src.domain.ports.attachment_repository import AttachmentRepository
from src.domain.ports.interaction_repository import InteractionRepository


class ListAttachments:
    def __init__(
        self,
        interaction_repository: InteractionRepository,
        attachment_repository: AttachmentRepository,
    ) -> None:
        self._interaction_repo = interaction_repository
        self._attachment_repo = attachment_repository

    async def execute(self, interaction_id: UUID) -> list[Attachment]:
        interaction = await self._interaction_repo.get_by_id(interaction_id)
        if interaction is None or interaction.is_deleted:
            raise InteractionNotFoundError()

        return await self._attachment_repo.list_by_interaction(interaction_id)
