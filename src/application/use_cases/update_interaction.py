"""
Use case: Update an existing interaction.
Tracks field-level changes in the audit log.
"""

import uuid
from uuid import UUID

from src.application.dtos.interaction_dto import UpdateInteractionDTO
from src.domain.entities.audit import AuditEntry
from src.domain.entities.interaction import Interaction
from src.domain.exceptions import InteractionNotFoundError
from src.domain.ports.audit_repository import AuditRepository
from src.domain.ports.interaction_repository import InteractionRepository


AUDITABLE_FIELDS = [
    "type", "channel", "status", "subject", "notes",
    "internal_notes", "outcome", "duration_minutes",
]


class UpdateInteraction:
    def __init__(
        self,
        interaction_repository: InteractionRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self._repo = interaction_repository
        self._audit_repo = audit_repository

    async def execute(
        self, interaction_id: UUID, dto: UpdateInteractionDTO, editor_id: UUID
    ) -> Interaction:
        current = await self._repo.get_by_id(interaction_id)
        if current is None or current.is_deleted:
            raise InteractionNotFoundError()

        # Detect field-level changes for audit
        audit_entries: list[AuditEntry] = []
        for field_name in AUDITABLE_FIELDS:
            new_value = getattr(dto, field_name, None)
            if new_value is not None:
                previous_value = getattr(current, field_name)
                if str(previous_value) != str(new_value):
                    audit_entries.append(
                        AuditEntry(
                            id=uuid.uuid4(),
                            interaction_id=interaction_id,
                            edited_by=editor_id,
                            field_name=field_name,
                            previous_value=str(previous_value) if previous_value is not None else None,
                            new_value=str(new_value),
                        )
                    )

        # Check follow_up_date change
        if dto.follow_up_date is not None and dto.follow_up_date != current.follow_up_date:
            audit_entries.append(
                AuditEntry(
                    id=uuid.uuid4(),
                    interaction_id=interaction_id,
                    edited_by=editor_id,
                    field_name="follow_up_date",
                    previous_value=str(current.follow_up_date) if current.follow_up_date else None,
                    new_value=str(dto.follow_up_date),
                )
            )

        # Apply updates
        if dto.type is not None:
            current.type = dto.type
        if dto.channel is not None:
            current.channel = dto.channel
        if dto.status is not None:
            current.status = dto.status
        if dto.subject is not None:
            current.subject = dto.subject.strip()
        if dto.notes is not None:
            current.notes = dto.notes
        if dto.internal_notes is not None:
            current.internal_notes = dto.internal_notes
        if dto.outcome is not None:
            current.outcome = dto.outcome
        if dto.follow_up_date is not None:
            current.follow_up_date = dto.follow_up_date
        if dto.duration_minutes is not None:
            current.duration_minutes = dto.duration_minutes

        current.last_edited_by = editor_id

        updated = await self._repo.update(current)

        if audit_entries:
            await self._audit_repo.bulk_save(audit_entries)

        return updated
