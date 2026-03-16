"""
Unit tests for GetClientSummary use case.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.get_client_summary import GetClientSummary


@pytest.mark.asyncio
async def test_get_client_summary_success():
    client_id = uuid.uuid4()
    summary_data = {
        "client_id": str(client_id),
        "total_interactions": 15,
        "interactions_last_30_days": 4,
        "by_type": {"call": 5, "email": 4, "meeting": 3, "ticket": 2, "note": 1},
        "by_status": {"pending": 3, "in_progress": 5, "resolved": 4, "closed": 3},
        "completion_rate": 46.67,
        "last_interaction_date": "2026-03-01T10:00:00Z",
        "next_follow_up_date": "2026-04-01T10:00:00Z",
        "open_tickets": 1,
    }
    repo = AsyncMock()
    repo.get_client_summary.return_value = summary_data

    use_case = GetClientSummary(interaction_repository=repo)
    result = await use_case.execute(client_id)

    assert result["total_interactions"] == 15
    assert result["interactions_last_30_days"] == 4
    assert result["by_type"]["call"] == 5
    assert result["completion_rate"] == 46.67
    repo.get_client_summary.assert_called_once_with(client_id, agent_id=None)


@pytest.mark.asyncio
async def test_get_client_summary_comercial_filtered():
    """Comercial should pass agent_id to filter only their interactions."""
    client_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    repo = AsyncMock()
    repo.get_client_summary.return_value = {
        "client_id": str(client_id),
        "total_interactions": 3,
        "interactions_last_30_days": 1,
        "by_type": {"call": 3},
        "by_status": {"pending": 1, "resolved": 2},
        "completion_rate": 66.67,
        "last_interaction_date": None,
        "next_follow_up_date": None,
        "open_tickets": 0,
    }

    use_case = GetClientSummary(interaction_repository=repo)
    result = await use_case.execute(client_id, agent_id=agent_id)

    assert result["total_interactions"] == 3
    repo.get_client_summary.assert_called_once_with(client_id, agent_id=agent_id)


@pytest.mark.asyncio
async def test_get_client_summary_empty_client():
    """Client with zero interactions should return zero counts."""
    client_id = uuid.uuid4()
    repo = AsyncMock()
    repo.get_client_summary.return_value = {
        "client_id": str(client_id),
        "total_interactions": 0,
        "interactions_last_30_days": 0,
        "by_type": {"call": 0, "email": 0, "meeting": 0, "ticket": 0, "note": 0},
        "by_status": {"pending": 0, "in_progress": 0, "resolved": 0, "closed": 0},
        "completion_rate": 0.0,
        "last_interaction_date": None,
        "next_follow_up_date": None,
        "open_tickets": 0,
    }

    use_case = GetClientSummary(interaction_repository=repo)
    result = await use_case.execute(client_id)

    assert result["total_interactions"] == 0
    assert result["completion_rate"] == 0.0
