"""
Integration tests: Follow-up and metrics endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import (
    INTERNAL_HEADERS_ADMIN,
    INTERNAL_HEADERS_SOPORTE,
    INTERNAL_HEADERS_COMERCIAL,
    CLIENT_A_ID,
    _interaction_payload,
)


# ── GET /api/v1/interactions/follow-ups/pending ───────────────────────────

@pytest.mark.asyncio
async def test_pending_follow_ups_empty(client: AsyncClient):
    response = await client.get(
        "/api/v1/interactions/follow-ups/pending",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_pending_follow_ups_returns_future(client: AsyncClient):
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            subject="Con follow-up futuro",
            follow_up_date="2099-12-01T10:00:00Z",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Sin follow-up"),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/interactions/follow-ups/pending",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["subject"] == "Con follow-up futuro"


# ── GET /api/v1/interactions/follow-ups/overdue ───────────────────────────

@pytest.mark.asyncio
async def test_overdue_follow_ups_returns_past(client: AsyncClient):
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            subject="Follow-up vencido",
            follow_up_date="2020-01-01T10:00:00Z",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/interactions/follow-ups/overdue",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["subject"] == "Follow-up vencido"


@pytest.mark.asyncio
async def test_overdue_does_not_include_closed(client: AsyncClient):
    """Closed interactions should not appear as overdue."""
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            subject="Cerrada con follow-up pasado",
            follow_up_date="2020-01-01T10:00:00Z",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    await client.patch(
        f"/api/v1/interactions/{interaction_id}/close",
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/interactions/follow-ups/overdue",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.json()["data"]["total"] == 0


# ── GET /api/v1/interactions/metrics ──────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_empty(client: AsyncClient):
    response = await client.get(
        "/api/v1/interactions/metrics", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_clients"] == 0
    assert data["total_interactions"] == 0
    assert data["avg_interactions_per_client"] == 0.0
    assert data["per_client"] == []


@pytest.mark.asyncio
async def test_metrics_with_data(client: AsyncClient):
    # Create 3 interactions for 2 clients
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(client_id=str(CLIENT_A_ID)),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(client_id=str(CLIENT_A_ID), type="email", channel="email"),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    from tests.conftest import CLIENT_B_ID
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(client_id=str(CLIENT_B_ID), type="meeting", channel="in_person"),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/interactions/metrics", headers=INTERNAL_HEADERS_ADMIN
    )
    data = response.json()["data"]
    assert data["total_clients"] == 2
    assert data["total_interactions"] == 3
    assert data["avg_interactions_per_client"] == 1.5
    # per_client breakdown
    assert len(data["per_client"]) == 2
    client_a_stat = next(c for c in data["per_client"] if c["client_id"] == str(CLIENT_A_ID))
    assert client_a_stat["interaction_count"] == 2
    assert client_a_stat["last_interaction_date"] is not None


# ── GET /api/v1/interactions/{id}/audit ───────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_after_update(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    await client.put(
        f"/api/v1/interactions/{interaction_id}",
        json={"subject": "Asunto modificado", "status": "in_progress"},
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        f"/api/v1/interactions/{interaction_id}/audit",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    entries = response.json()["data"]
    assert len(entries) >= 2
    field_names = {e["field_name"] for e in entries}
    assert "subject" in field_names
    assert "status" in field_names


@pytest.mark.asyncio
async def test_audit_log_empty_when_no_updates(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(),
        headers=INTERNAL_HEADERS_ADMIN,
    )
    interaction_id = create_r.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/interactions/{interaction_id}/audit",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_audit_log_not_found_404(client: AsyncClient):
    import uuid
    response = await client.get(
        f"/api/v1/interactions/{uuid.uuid4()}/audit",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404


# ── Health check ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["service"] == "crm-interactions-service"
    assert data["status"] == "running"
