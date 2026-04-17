"""
Use cases: List pending and overdue follow-ups.
"""

from uuid import UUID

from src.domain.entities.interaction import Interaction
from src.domain.ports.interaction_repository import InteractionRepository


class ListPendingFollowUps:
    """Follow-ups with future date for the authenticated agent."""

    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(
        self, agent_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]:
        return await self._repo.get_pending_follow_ups(
            agent_id, page=page, page_size=page_size
        )


class ListOverdueFollowUps:
    """Follow-ups with past date and status != closed."""

    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(
        self, agent_id: UUID | None = None, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]:
        return await self._repo.get_overdue_follow_ups(
            agent_id=agent_id, page=page, page_size=page_size
        )
