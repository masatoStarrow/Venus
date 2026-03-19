"""
Use case: Create a new interaction.
"""

import uuid

from src.application.dtos.interaction_dto import CreateInteractionDTO
from src.domain.entities.interaction import Interaction
from src.domain.ports.interaction_repository import InteractionRepository


class CreateInteraction:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(self, dto: CreateInteractionDTO, agent_id: uuid.UUID) -> Interaction:
        interaction = Interaction(
            id=uuid.uuid4(),
            client_id=dto.client_id,
            agent_id=agent_id,
            type=dto.type,
            channel=dto.channel,
            status=dto.status,
            subject=dto.subject.strip(),
            notes=dto.notes,
            internal_notes=dto.internal_notes,
            outcome=dto.outcome,
            interaction_date=dto.interaction_date,
            follow_up_date=dto.follow_up_date,
            duration_minutes=dto.duration_minutes,
        )
        return await self._repo.create(interaction)
