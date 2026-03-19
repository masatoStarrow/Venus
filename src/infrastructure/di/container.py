"""
Dependency injection container.
Assembles use cases with real repository implementations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.outbound.persistence.interaction_pg_repository import InteractionPgRepository
from src.adapters.outbound.persistence.audit_pg_repository import AuditPgRepository
from src.adapters.outbound.persistence.attachment_pg_repository import AttachmentPgRepository
from src.application.use_cases.create_interaction import CreateInteraction
from src.application.use_cases.get_interaction import GetInteraction
from src.application.use_cases.list_interactions import ListInteractions
from src.application.use_cases.list_by_client import ListByClient
from src.application.use_cases.update_interaction import UpdateInteraction
from src.application.use_cases.close_interaction import CloseInteraction
from src.application.use_cases.soft_delete_interaction import SoftDeleteInteraction
from src.application.use_cases.get_client_summary import GetClientSummary
from src.application.use_cases.get_metrics import GetMetrics
from src.application.use_cases.list_follow_ups import ListPendingFollowUps, ListOverdueFollowUps
from src.application.use_cases.get_audit_log import GetAuditLog
from src.application.use_cases.upload_attachment import UploadAttachment
from src.application.use_cases.list_attachments import ListAttachments
from src.application.use_cases.download_attachment import DownloadAttachment
from src.application.use_cases.delete_attachment import DeleteAttachment
from src.domain.ports.file_storage import FileStorage


# ── Interaction use case factories ───────────────────────────────────────

def get_create_interaction_use_case(db: AsyncSession) -> CreateInteraction:
    return CreateInteraction(interaction_repository=InteractionPgRepository(db))


def get_get_interaction_use_case(db: AsyncSession) -> GetInteraction:
    return GetInteraction(interaction_repository=InteractionPgRepository(db))


def get_list_interactions_use_case(db: AsyncSession) -> ListInteractions:
    return ListInteractions(interaction_repository=InteractionPgRepository(db))


def get_list_by_client_use_case(db: AsyncSession) -> ListByClient:
    return ListByClient(interaction_repository=InteractionPgRepository(db))


def get_update_interaction_use_case(db: AsyncSession) -> UpdateInteraction:
    return UpdateInteraction(
        interaction_repository=InteractionPgRepository(db),
        audit_repository=AuditPgRepository(db),
    )


def get_close_interaction_use_case(db: AsyncSession) -> CloseInteraction:
    return CloseInteraction(interaction_repository=InteractionPgRepository(db))


def get_soft_delete_interaction_use_case(db: AsyncSession) -> SoftDeleteInteraction:
    return SoftDeleteInteraction(interaction_repository=InteractionPgRepository(db))


def get_get_client_summary_use_case(db: AsyncSession) -> GetClientSummary:
    return GetClientSummary(interaction_repository=InteractionPgRepository(db))


def get_get_metrics_use_case(db: AsyncSession) -> GetMetrics:
    return GetMetrics(interaction_repository=InteractionPgRepository(db))


def get_list_pending_follow_ups_use_case(db: AsyncSession) -> ListPendingFollowUps:
    return ListPendingFollowUps(interaction_repository=InteractionPgRepository(db))


def get_list_overdue_follow_ups_use_case(db: AsyncSession) -> ListOverdueFollowUps:
    return ListOverdueFollowUps(interaction_repository=InteractionPgRepository(db))


def get_get_audit_log_use_case(db: AsyncSession) -> GetAuditLog:
    return GetAuditLog(audit_repository=AuditPgRepository(db))


# ── File storage singleton ───────────────────────────────────────────────

_file_storage_instance: FileStorage | None = None


def set_file_storage(storage: FileStorage) -> None:
    """Override the file storage (used in tests)."""
    global _file_storage_instance
    _file_storage_instance = storage


def _get_file_storage() -> FileStorage:
    global _file_storage_instance
    if _file_storage_instance is None:
        from src.adapters.outbound.storage.s3_storage import S3Storage
        _file_storage_instance = S3Storage()
    return _file_storage_instance


# ── Attachment use case factories ────────────────────────────────────────

def get_upload_attachment_use_case(db: AsyncSession) -> UploadAttachment:
    return UploadAttachment(
        interaction_repository=InteractionPgRepository(db),
        attachment_repository=AttachmentPgRepository(db),
        file_storage=_get_file_storage(),
    )


def get_list_attachments_use_case(db: AsyncSession) -> ListAttachments:
    return ListAttachments(
        interaction_repository=InteractionPgRepository(db),
        attachment_repository=AttachmentPgRepository(db),
    )


def get_download_attachment_use_case(db: AsyncSession) -> DownloadAttachment:
    return DownloadAttachment(
        interaction_repository=InteractionPgRepository(db),
        attachment_repository=AttachmentPgRepository(db),
        file_storage=_get_file_storage(),
    )


def get_delete_attachment_use_case(db: AsyncSession) -> DeleteAttachment:
    return DeleteAttachment(
        interaction_repository=InteractionPgRepository(db),
        attachment_repository=AttachmentPgRepository(db),
        file_storage=_get_file_storage(),
    )
