"""
Use case: Get aggregated summary for a client's interactions.
Returns: total, last 30 days count, by_type, by_status, completion_rate, etc.
"""

from uuid import UUID

from src.domain.ports.interaction_repository import InteractionRepository


class GetClientSummary:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(self, client_id: UUID, *, agent_id: UUID | None = None) -> dict:
        return await self._repo.get_client_summary(client_id, agent_id=agent_id)
