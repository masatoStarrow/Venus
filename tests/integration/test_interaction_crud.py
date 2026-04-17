"""
Integration tests: CRUD completo de interacciones via HTTP endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    INTERNAL_HEADERS_ADMIN,
    INTERNAL_HEADERS_SOPORTE,
    INTERNAL_HEADERS_COMERCIAL,
    CLIENT_A_ID,
    COMERCIAL_ID,
    _interaction_payload,
)


# ── POST /api/v1/interactions/ ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_interaction_success(client: AsyncClient):
    payload = _interaction_payload()
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_ADMIN
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["type"] == "call"
    assert data["channel"] == "phone"
    assert data["subject"] == "Llamada de seguimiento"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_interaction_comercial_allowed(client: AsyncClient):
    """Comercial can create interactions (assigned to themselves)."""
    payload = _interaction_payload(subject="Comercial crea su propia interacción")
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_COMERCIAL
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["agent_id"] == str(COMERCIAL_ID)  # Assigned to creator


@pytest.mark.asyncio
async def test_create_interaction_soporte_allowed(client: AsyncClient):
    payload = _interaction_payload(subject="Soporte puede crear")
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_SOPORTE
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_interaction_missing_subject_422(client: AsyncClient):
    payload = _interaction_payload()
    del payload["subject"]
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_interaction_invalid_type_422(client: AsyncClient):
    payload = _interaction_payload(type="invalid_type")
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_interaction_with_all_fields(client: AsyncClient):
    payload = _interaction_payload(
        type="email",
        channel="email",
        status="in_progress",
        notes="Notas detalladas",
        internal_notes="Solo agentes",
        outcome="Pendiente",
        follow_up_date="2026-04-01T10:00:00Z",
        duration_minutes=45,
    )
    response = await client.post(
        "/api/v1/interactions/", json=payload, headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["type"] == "email"
    assert data["internal_notes"] == "Solo agentes"
    assert data["duration_minutes"] == 45


# ── GET /api/v1/interactions/ ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_interactions_empty(client: AsyncClient):
    response = await client.get("/api/v1/interactions/", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_interactions_returns_created(client: AsyncClient):
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    response = await client.get("/api/v1/interactions/", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_list_interactions_filter_by_type(client: AsyncClient):
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(type="call"),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(type="email", channel="email"),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/interactions/?type=call", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(i["type"] == "call" for i in items)


@pytest.mark.asyncio
async def test_list_interactions_pagination(client: AsyncClient):
    for i in range(5):
        await client.post(
            "/api/v1/interactions/",
            json=_interaction_payload(subject=f"Interaction {i}"),
            headers=INTERNAL_HEADERS_ADMIN,
        )

    response = await client.get(
        "/api/v1/interactions/?page=1&page_size=2", headers=INTERNAL_HEADERS_ADMIN
    )
    d = response.json()["data"]
    assert d["total"] == 5
    assert len(d["items"]) == 2
    assert d["pages"] == 3


# ── GET /api/v1/interactions/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_interaction_by_id(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == interaction_id


@pytest.mark.asyncio
async def test_get_interaction_not_found_404(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/interactions/{fake_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INTERACTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_interaction_by_id_comercial_forbidden_if_not_own(
    client: AsyncClient,
):
    """Comercial cannot view an interaction created by another user."""
    # Create as admin
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Interacción de admin"),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Comercial tries to view it → 403
    response = await client.get(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_COMERCIAL
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_interaction_by_id_comercial_own_allowed(client: AsyncClient):
    """Comercial can view their own interaction by ID."""
    # Create as comercial
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Mi interacción"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Comercial views own → 200
    response = await client.get(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_COMERCIAL
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == interaction_id


# ── PUT /api/v1/interactions/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_interaction_success(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Asunto actualizado", "status": "in_progress"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["subject"] == "Asunto actualizado"
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_interaction_comercial_forbidden(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Intento comercial"},
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_interaction_not_found_404(client: AsyncClient):
    response = await client.put(
        f"/api/v1/interactions/{uuid.uuid4()}",
        json={"subject": "No existe"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_interaction_comercial_own_allowed(client: AsyncClient):
    """Comercial can update their own interactions."""
    # Create as comercial
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Mi interacción"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Update as comercial (should succeed)
    response = await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Actualizado por mí", "status": "in_progress"},
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["subject"] == "Actualizado por mí"
    assert data["status"] == "in_progress"


# ── DELETE /api/v1/interactions/{id} ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_interaction_admin_only(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Soporte can't delete
    response = await client.delete(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_SOPORTE
    )
    assert response.status_code == 403

    # Admin can delete
    response = await client.delete(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_deleted"] is True


@pytest.mark.asyncio
async def test_deleted_interaction_not_visible(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    await client.delete(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_ADMIN
    )

    response = await client.get(
        f"/api/v1/interactions/{interaction_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 404


# ── PATCH /api/v1/interactions/{id}/close ──────────────────────────────────


@pytest.mark.asyncio
async def test_close_interaction_success(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        json={"outcome": "Resuelto satisfactoriamente"},
        headers=INTERNAL_HEADERS_SOPORTE,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "closed"
    assert data["outcome"] == "Resuelto satisfactoriamente"


@pytest.mark.asyncio
async def test_close_interaction_already_closed_409(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    response = await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INTERACTION_ALREADY_CLOSED"


@pytest.mark.asyncio
async def test_close_interaction_comercial_forbidden(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_close_interaction_comercial_own_allowed(client: AsyncClient):
    """Comercial can close their own interactions."""
    # Create as comercial
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Mi interacción a cerrar"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Close as comercial (should succeed)
    response = await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        json={"outcome": "Cerrado por el comercial"},
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "closed"
    assert data["outcome"] == "Cerrado por el comercial"


# ── GET /{interaction_id}/audit ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_comercial_forbidden_if_not_own(client: AsyncClient):
    """Comercial cannot view audit of other user's interactions."""
    # Create as admin
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Interacción de admin"),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Comercial tries to get audit → 403
    response = await client.get(
        f"/api/v1/interactions/{interaction_id}/audit",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_comercial_own_allowed(client: AsyncClient):
    """Comercial can view audit of their own interactions."""
    # Create as comercial
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Mi interacción"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Update it as comercial (the owner) to create audit entry
    await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Actualizada por comercial", "status": "in_progress"},
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Comercial views own audit → 200
    response = await client.get(
        f"/api/v1/interactions/{interaction_id}/audit",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    # Should have audit entries (subject and status changed)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_audit_log_records_changes_from_comercial_update(client: AsyncClient):
    """Verify audit entries are created when comercial updates their own interaction."""
    # Create as comercial
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Original"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    interaction_id = create_r.json()["data"]["id"]

    # Update as comercial
    await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Modificado por comercial", "status": "in_progress"},
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Verify audit has entries from comercial
    audit_r = await client.get(
        f"/api/v1/interactions/{interaction_id}/audit",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    entries = audit_r.json()["data"]
    # Should have entries for subject and status changes
    assert len(entries) >= 2
    # Check that edited_by matches comercial's user_id
    comercial_user_id = INTERNAL_HEADERS_COMERCIAL["X-User-Id"]
    for entry in entries:
        assert entry["edited_by"] == comercial_user_id
