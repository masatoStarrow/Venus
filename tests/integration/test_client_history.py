"""
Integration tests: Client history and summary endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    INTERNAL_HEADERS_ADMIN,
    INTERNAL_HEADERS_COMERCIAL,
    ADMIN_ID,
    COMERCIAL_ID,
    CLIENT_A_ID,
    CLIENT_B_ID,
    _interaction_payload,
)


async def _seed_interactions(client: AsyncClient) -> None:
    """Create diverse interactions for CLIENT_A and CLIENT_B."""
    # 3 interactions for CLIENT_A (by admin)
    for i, typ in enumerate(["call", "email", "meeting"]):
        await client.post(
            "/api/v1/interactions/",
            json=_interaction_payload(
                client_id=str(CLIENT_A_ID),
                type=typ,
                channel="phone" if typ == "call" else "email" if typ == "email" else "in_person",
                subject=f"Interaction A-{i}",
                status="resolved" if i == 2 else "pending",
            ),
            headers=INTERNAL_HEADERS_ADMIN,
        )
    # 1 interaction for CLIENT_B
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            client_id=str(CLIENT_B_ID),
            type="ticket",
            channel="platform",
            subject="Ticket B-0",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )


# ── GET /api/v1/interactions/client/{client_id} ──────────────────────────

@pytest.mark.asyncio
async def test_list_by_client_returns_only_client(client: AsyncClient):
    await _seed_interactions(client)

    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 3
    assert all(i["client_id"] == str(CLIENT_A_ID) for i in items)


@pytest.mark.asyncio
async def test_list_by_client_filter_by_type(client: AsyncClient):
    await _seed_interactions(client)

    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}?type=call",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    items = response.json()["data"]["items"]
    assert all(i["type"] == "call" for i in items)


@pytest.mark.asyncio
async def test_list_by_client_filter_by_status(client: AsyncClient):
    await _seed_interactions(client)

    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}?status=resolved",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["status"] == "resolved"


@pytest.mark.asyncio
async def test_list_by_client_empty(client: AsyncClient):
    response = await client.get(
        f"/api/v1/interactions/client/{uuid.uuid4()}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0


# ── GET /api/v1/interactions/client/{client_id}/summary ───────────────────

@pytest.mark.asyncio
async def test_client_summary_returns_totals(client: AsyncClient):
    await _seed_interactions(client)

    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}/summary",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_interactions"] == 3
    assert data["client_id"] == str(CLIENT_A_ID)
    assert "by_type" in data
    assert "by_status" in data
    assert "completion_rate" in data


@pytest.mark.asyncio
async def test_client_summary_empty_client(client: AsyncClient):
    response = await client.get(
        f"/api/v1/interactions/client/{uuid.uuid4()}/summary",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_interactions"] == 0
    assert data["completion_rate"] == 0.0


# ── Comercial owned-client access tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_list_by_client_comercial_shows_all_for_owned_client(client: AsyncClient):
    """Comercial sees all interactions for a client they own, not just their own."""
    # Comercial creates interaction for CLIENT_A
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Comercial interaction for CLIENT_A"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Admin creates 2 more interactions for CLIENT_A
    for i in range(2):
        await client.post(
            "/api/v1/interactions/",
            json=_interaction_payload(subject=f"Admin interaction {i} for CLIENT_A"),
            headers=INTERNAL_HEADERS_ADMIN,
        )

    # Comercial lists CLIENT_A → sees all 3
    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_by_client_comercial_empty_for_unowned_client(client: AsyncClient):
    """Comercial sees empty result for a client they don't own."""
    # Comercial creates interaction for CLIENT_A (not CLIENT_B)
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Comercial for CLIENT_A"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Admin creates interactions for CLIENT_B
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            client_id=str(CLIENT_B_ID),
            subject="Admin for CLIENT_B",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    # Comercial lists CLIENT_B → empty (no ownership)
    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_B_ID}",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_client_summary_comercial_can_see_owned_client(client: AsyncClient):
    """Comercial can see full summary for an owned client (no agent_id filter)."""
    # Comercial creates interaction for CLIENT_A
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Comercial interaction"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Admin creates 2 more interactions for CLIENT_A
    for i in range(2):
        await client.post(
            "/api/v1/interactions/",
            json=_interaction_payload(subject=f"Admin interaction {i}"),
            headers=INTERNAL_HEADERS_ADMIN,
        )

    # Comercial sees summary with ALL 3 interactions
    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_A_ID}/summary",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_interactions"] == 3


@pytest.mark.asyncio
async def test_client_summary_comercial_forbidden_for_unowned_client(client: AsyncClient):
    """Comercial gets 403 for client summary when they don't own the client."""
    # Comercial creates interaction for CLIENT_A (not CLIENT_B)
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(subject="Comercial for CLIENT_A"),
        headers=INTERNAL_HEADERS_COMERCIAL,
    )

    # Admin creates interaction for CLIENT_B
    await client.post(
        "/api/v1/interactions/",
        json=_interaction_payload(
            client_id=str(CLIENT_B_ID),
            subject="Admin for CLIENT_B",
        ),
        headers=INTERNAL_HEADERS_ADMIN,
    )

    # Comercial tries CLIENT_B summary → 403
    response = await client.get(
        f"/api/v1/interactions/client/{CLIENT_B_ID}/summary",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 403
