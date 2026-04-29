"""
ABC: InteractionRepository — contract for interaction data access.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.interaction import Interaction


class InteractionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, interaction_id: UUID) -> Interaction | None: ...

    @abstractmethod
    async def list_interactions(
        self,
        *,
        client_id: UUID | None = None,
        agent_id: UUID | None = None,
        type_filter: list[str] | None = None,
        channel_filter: list[str] | None = None,
        status_filter: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "interaction_date",
        order_dir: str = "desc",
    ) -> tuple[list[Interaction], int]:
        """Return (items, total_count)."""
        ...

    @abstractmethod
    async def list_by_client(
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
        """Return (items, total_count) for a specific client."""
        ...

    @abstractmethod
    async def create(self, interaction: Interaction) -> Interaction: ...

    @abstractmethod
    async def update(self, interaction: Interaction) -> Interaction: ...

    @abstractmethod
    async def soft_delete(self, interaction_id: UUID) -> Interaction: ...

    @abstractmethod
    async def get_client_summary(
        self, client_id: UUID, *, agent_id: UUID | None = None
    ) -> dict: ...

    @abstractmethod
    async def get_metrics(self, *, agent_id: UUID | None = None) -> dict: ...

    @abstractmethod
    async def get_pending_follow_ups(
        self, agent_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]: ...

    @abstractmethod
    async def get_overdue_follow_ups(
        self, agent_id: UUID | None = None, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]: ...
