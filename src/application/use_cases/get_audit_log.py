"""
Use case: Get audit log entries for an interaction.
"""

from uuid import UUID

from src.domain.entities.audit import AuditEntry
from src.domain.ports.audit_repository import AuditRepository


class GetAuditLog:
    def __init__(self, audit_repository: AuditRepository) -> None:
        self._audit_repo = audit_repository

    async def execute(self, interaction_id: UUID) -> list[AuditEntry]:
        return await self._audit_repo.get_by_interaction(interaction_id)
