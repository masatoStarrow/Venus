"""
Use case: List interactions by client with filters and pagination.
"""

from datetime import datetime
from uuid import UUID

from src.domain.entities.interaction import Interaction
from src.domain.ports.interaction_repository import InteractionRepository


class ListByClient:
    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self._repo = interaction_repository

    async def execute(
        self,
        client_id: UUID,
        *,
        agent_id: UUID | None = None,
        type_filter: list[str] | None = None,
        status_filter: list[str] | None = None,
        agent_id_filter: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "interaction_date",
        order_dir: str = "desc",
    ) -> tuple[list[Interaction], int]:
        return await self._repo.list_by_client(
            client_id=client_id,
            agent_id=agent_id,
            type_filter=type_filter,
            status_filter=status_filter,
            agent_id_filter=agent_id_filter,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_dir=order_dir,
        )
