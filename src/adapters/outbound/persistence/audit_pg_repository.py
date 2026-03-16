"""
PostgreSQL implementation of AuditRepository using SQLAlchemy async.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.audit import AuditEntry
from src.domain.ports.audit_repository import AuditRepository
from src.adapters.outbound.persistence.models.audit_model import AuditModel


class AuditPgRepository(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: AuditModel) -> AuditEntry:
        return AuditEntry(
            id=model.id,
            interaction_id=model.interaction_id,
            edited_by=model.edited_by,
            field_name=model.field_name,
            previous_value=model.previous_value,
            new_value=model.new_value,
            edited_at=model.edited_at,
        )

    async def bulk_save(self, entries: list[AuditEntry]) -> None:
        for entry in entries:
            model = AuditModel(
                id=entry.id,
                interaction_id=entry.interaction_id,
                edited_by=entry.edited_by,
                field_name=entry.field_name,
                previous_value=entry.previous_value,
                new_value=entry.new_value,
            )
            self._session.add(model)
        await self._session.flush()

    async def get_by_interaction(self, interaction_id: UUID) -> list[AuditEntry]:
        stmt = (
            select(AuditModel)
            .where(AuditModel.interaction_id == interaction_id)
            .order_by(AuditModel.edited_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
