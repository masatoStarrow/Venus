"""
PostgreSQL implementation of AttachmentRepository using SQLAlchemy async.
"""

from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.attachment import Attachment
from src.domain.ports.attachment_repository import AttachmentRepository
from src.adapters.outbound.persistence.models.attachment_model import AttachmentModel


class AttachmentPgRepository(AttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: AttachmentModel) -> Attachment:
        return Attachment(
            id=model.id,
            interaction_id=model.interaction_id,
            uploaded_by=model.uploaded_by,
            file_name=model.file_name,
            file_key=model.file_key,
            content_type=model.content_type,
            file_size=model.file_size,
            context=model.context,
            created_at=model.created_at,
        )

    async def save(self, attachment: Attachment) -> Attachment:
        model = AttachmentModel(
            id=attachment.id,
            interaction_id=attachment.interaction_id,
            uploaded_by=attachment.uploaded_by,
            file_name=attachment.file_name,
            file_key=attachment.file_key,
            content_type=attachment.content_type,
            file_size=attachment.file_size,
            context=attachment.context,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, attachment_id: UUID) -> Attachment | None:
        result = await self._session.get(AttachmentModel, attachment_id)
        return self._to_entity(result) if result else None

    async def list_by_interaction(self, interaction_id: UUID) -> list[Attachment]:
        stmt = (
            select(AttachmentModel)
            .where(AttachmentModel.interaction_id == interaction_id)
            .order_by(AttachmentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, attachment_id: UUID) -> None:
        stmt = delete(AttachmentModel).where(AttachmentModel.id == attachment_id)
        await self._session.execute(stmt)
        await self._session.flush()
