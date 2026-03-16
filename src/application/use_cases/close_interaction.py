"""
Use case: Close an interaction (set status to closed).
"""

from uuid import UUID

from src.application.dtos.interaction_dto import CloseInteractionDTO
from src.domain.entities.interaction import Interaction
from src.domain.exceptions import InteractionAlreadyClosedError, InteractionNotFoundError
from src.domain.ports.interaction_repository import InteractionRepository


class CloseInteraction:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(
        self, interaction_id: UUID, dto: CloseInteractionDTO, editor_id: UUID
    ) -> Interaction:
        interaction = await self._repo.get_by_id(interaction_id)
        if interaction is None or interaction.is_deleted:
            raise InteractionNotFoundError()

        if interaction.status == "closed":
            raise InteractionAlreadyClosedError()

        interaction.status = "closed"
        interaction.last_edited_by = editor_id
        if dto.outcome is not None:
            interaction.outcome = dto.outcome

        return await self._repo.update(interaction)
