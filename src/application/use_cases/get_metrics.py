"""
Use case: Get global interaction metrics.
Returns: total_clients, total_interactions, avg_interactions_per_client.
"""

from uuid import UUID

from src.domain.ports.interaction_repository import InteractionRepository


class GetMetrics:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(self, *, agent_id: UUID | None = None) -> dict:
        return await self._repo.get_metrics(agent_id=agent_id)
