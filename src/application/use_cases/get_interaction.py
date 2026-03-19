"""
Use case: Get an interaction by ID.
"""

from uuid import UUID

from src.domain.entities.interaction import Interaction
from src.domain.exceptions import InteractionNotFoundError
from src.domain.ports.interaction_repository import InteractionRepository


class GetInteraction:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(self, interaction_id: UUID) -> Interaction:
        interaction = await self._repo.get_by_id(interaction_id)
        if interaction is None or interaction.is_deleted:
            raise InteractionNotFoundError()
        return interaction
