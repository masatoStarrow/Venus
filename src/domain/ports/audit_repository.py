"""
ABC: AuditRepository — contract for interaction audit data access.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.audit import AuditEntry


class AuditRepository(ABC):

    @abstractmethod
    async def bulk_save(self, entries: list[AuditEntry]) -> None:
        ...

    @abstractmethod
    async def get_by_interaction(self, interaction_id: UUID) -> list[AuditEntry]:
        ...
