"""
Integration tests for attachment CRUD endpoints.
POST   /{id}/attachments/
GET    /{id}/attachments/
GET    /{id}/attachments/{att_id}/download
DELETE /{id}/attachments/{att_id}
"""

import io
import uuid

import pytest

from tests.conftest import ADMIN_ID, CLIENT_A_ID, INTERNAL_HEADERS_ADMIN


BASE = "/api/v1/interactions"


async def _create_interaction(client) -> str:
    """Create an interaction and return its ID."""
    payload = {
        "client_id": str(CLIENT_A_ID),
        "type": "call",
        "channel": "phone",
        "subject": "Llamada de prueba para adjuntos",
        "interaction_date": "2026-03-01T10:00:00Z",
    }
    resp = await client.post(f"{BASE}/", json=payload, headers=INTERNAL_HEADERS_ADMIN)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _upload_file(client, interaction_id: str, filename="test.pdf", content_type="application/pdf"):
    """Upload a tiny file and return the response."""
    file_data = b"%PDF-1.4 fake content"
    return await client.post(
        f"{BASE}/{interaction_id}/attachments/?context=internal_note",
        files={"file": (filename, io.BytesIO(file_data), content_type)},
        headers=INTERNAL_HEADERS_ADMIN,
    )


# ── Upload ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_attachment(client):
    iid = await _create_interaction(client)
    resp = await _upload_file(client, iid)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    att = body["data"]
    assert att["interaction_id"] == iid
    assert att["file_name"] == "test.pdf"
    assert att["content_type"] == "application/pdf"
    assert att["context"] == "internal_note"
    assert att["file_size"] > 0


@pytest.mark.asyncio
async def test_upload_attachment_invalid_type(client):
    iid = await _create_interaction(client)
    resp = await client.post(
        f"{BASE}/{iid}/attachments/",
        files={"file": ("malware.exe", io.BytesIO(b"bad"), "application/x-msdownload")},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_attachment_interaction_not_found(client):
    fake_id = str(uuid.uuid4())
    resp = await _upload_file(client, fake_id)
    assert resp.status_code == 404


# ── List ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_attachments(client):
    iid = await _create_interaction(client)
    await _upload_file(client, iid, "file1.pdf")
    await _upload_file(client, iid, "file2.pdf")

    resp = await client.get(
        f"{BASE}/{iid}/attachments/", headers=INTERNAL_HEADERS_ADMIN
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_attachments_empty(client):
    iid = await _create_interaction(client)
    resp = await client.get(
        f"{BASE}/{iid}/attachments/", headers=INTERNAL_HEADERS_ADMIN
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ── Download ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_attachment(client):
    iid = await _create_interaction(client)
    upload_resp = await _upload_file(client, iid)
    att_id = upload_resp.json()["data"]["id"]

    resp = await client.get(
        f"{BASE}/{iid}/attachments/{att_id}/download",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "url" in data
    assert "fake-s3.test" in data["url"]
    assert data["file_name"] == "test.pdf"


@pytest.mark.asyncio
async def test_download_attachment_not_found(client):
    iid = await _create_interaction(client)
    fake_att_id = str(uuid.uuid4())
    resp = await client.get(
        f"{BASE}/{iid}/attachments/{fake_att_id}/download",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_attachment(client):
    iid = await _create_interaction(client)
    upload_resp = await _upload_file(client, iid)
    att_id = upload_resp.json()["data"]["id"]

    del_resp = await client.delete(
        f"{BASE}/{iid}/attachments/{att_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify gone
    list_resp = await client.get(
        f"{BASE}/{iid}/attachments/", headers=INTERNAL_HEADERS_ADMIN
    )
    assert len(list_resp.json()["data"]) == 0


@pytest.mark.asyncio
async def test_delete_attachment_not_found(client):
    iid = await _create_interaction(client)
    fake_att_id = str(uuid.uuid4())
    resp = await client.delete(
        f"{BASE}/{iid}/attachments/{fake_att_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert resp.status_code == 404
