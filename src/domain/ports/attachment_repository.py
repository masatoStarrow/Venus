"""
ABC: AttachmentRepository — contract for attachment metadata access.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.attachment import Attachment


class AttachmentRepository(ABC):

    @abstractmethod
    async def save(self, attachment: Attachment) -> Attachment:
        ...

    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> Attachment | None:
        ...

    @abstractmethod
    async def list_by_interaction(self, interaction_id: UUID) -> list[Attachment]:
        ...

    @abstractmethod
    async def delete(self, attachment_id: UUID) -> None:
        ...
