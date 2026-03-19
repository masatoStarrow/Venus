"""
Unit tests for attachment use cases.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.upload_attachment import UploadAttachment
from src.application.use_cases.list_attachments import ListAttachments
from src.application.use_cases.download_attachment import DownloadAttachment
from src.application.use_cases.delete_attachment import DeleteAttachment
from src.domain.entities.attachment import Attachment
from src.domain.entities.interaction import Interaction
from src.domain.exceptions import (
    InteractionNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
    AttachmentNotFoundError,
)


def _make_interaction(**overrides) -> Interaction:
    defaults = dict(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        type="call",
        channel="phone",
        subject="Test",
        status="pending",
        interaction_date=datetime.now(timezone.utc),
        is_deleted=False,
    )
    defaults.update(overrides)
    return Interaction(**defaults)


def _make_attachment(**overrides) -> Attachment:
    defaults = dict(
        id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        uploaded_by=uuid.uuid4(),
        file_name="report.pdf",
        file_key="attachments/x/y/report.pdf",
        content_type="application/pdf",
        file_size=1024,
        context="internal_note",
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Attachment(**defaults)


# ── UploadAttachment ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_attachment_success():
    interaction = _make_interaction()
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.save.side_effect = lambda a: a
    storage = AsyncMock()
    storage.upload.return_value = "key"

    uc = UploadAttachment(
        interaction_repository=int_repo,
        attachment_repository=att_repo,
        file_storage=storage,
    )
    result = await uc.execute(
        interaction_id=interaction.id,
        uploaded_by=uuid.uuid4(),
        file_name="doc.pdf",
        content_type="application/pdf",
        file_data=b"fake pdf content",
    )

    assert result.file_name == "doc.pdf"
    storage.upload.assert_called_once()
    att_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_upload_attachment_interaction_not_found():
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = None

    uc = UploadAttachment(
        interaction_repository=int_repo,
        attachment_repository=AsyncMock(),
        file_storage=AsyncMock(),
    )

    with pytest.raises(InteractionNotFoundError):
        await uc.execute(
            interaction_id=uuid.uuid4(),
            uploaded_by=uuid.uuid4(),
            file_name="doc.pdf",
            content_type="application/pdf",
            file_data=b"data",
        )


@pytest.mark.asyncio
async def test_upload_attachment_file_too_large():
    interaction = _make_interaction()
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction

    uc = UploadAttachment(
        interaction_repository=int_repo,
        attachment_repository=AsyncMock(),
        file_storage=AsyncMock(),
    )

    big_data = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        await uc.execute(
            interaction_id=interaction.id,
            uploaded_by=uuid.uuid4(),
            file_name="big.pdf",
            content_type="application/pdf",
            file_data=big_data,
        )


@pytest.mark.asyncio
async def test_upload_attachment_invalid_type():
    interaction = _make_interaction()
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction

    uc = UploadAttachment(
        interaction_repository=int_repo,
        attachment_repository=AsyncMock(),
        file_storage=AsyncMock(),
    )

    with pytest.raises(InvalidFileTypeError):
        await uc.execute(
            interaction_id=interaction.id,
            uploaded_by=uuid.uuid4(),
            file_name="bad.exe",
            content_type="application/x-msdownload",
            file_data=b"data",
        )


# ── ListAttachments ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_attachments_success():
    interaction = _make_interaction()
    att1 = _make_attachment(interaction_id=interaction.id)
    att2 = _make_attachment(interaction_id=interaction.id)

    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.list_by_interaction.return_value = [att1, att2]

    uc = ListAttachments(interaction_repository=int_repo, attachment_repository=att_repo)
    result = await uc.execute(interaction.id)

    assert len(result) == 2


# ── DownloadAttachment ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_attachment_success():
    interaction = _make_interaction()
    att = _make_attachment(interaction_id=interaction.id)

    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.get_by_id.return_value = att
    storage = AsyncMock()
    storage.get_presigned_url.return_value = "https://s3.example.com/signed"

    uc = DownloadAttachment(
        interaction_repository=int_repo,
        attachment_repository=att_repo,
        file_storage=storage,
    )
    url = await uc.execute(interaction.id, att.id)
    assert url == "https://s3.example.com/signed"


@pytest.mark.asyncio
async def test_download_attachment_not_found():
    interaction = _make_interaction()
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.get_by_id.return_value = None

    uc = DownloadAttachment(
        interaction_repository=int_repo,
        attachment_repository=att_repo,
        file_storage=AsyncMock(),
    )
    with pytest.raises(AttachmentNotFoundError):
        await uc.execute(interaction.id, uuid.uuid4())


# ── DeleteAttachment ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_attachment_success():
    interaction = _make_interaction()
    att = _make_attachment(interaction_id=interaction.id)

    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.get_by_id.return_value = att
    storage = AsyncMock()

    uc = DeleteAttachment(
        interaction_repository=int_repo,
        attachment_repository=att_repo,
        file_storage=storage,
    )
    await uc.execute(interaction.id, att.id)
    storage.delete.assert_called_once_with(att.file_key)
    att_repo.delete.assert_called_once_with(att.id)


@pytest.mark.asyncio
async def test_delete_attachment_not_found():
    interaction = _make_interaction()
    int_repo = AsyncMock()
    int_repo.get_by_id.return_value = interaction
    att_repo = AsyncMock()
    att_repo.get_by_id.return_value = None

    uc = DeleteAttachment(
        interaction_repository=int_repo,
        attachment_repository=att_repo,
        file_storage=AsyncMock(),
    )
    with pytest.raises(AttachmentNotFoundError):
        await uc.execute(interaction.id, uuid.uuid4())
