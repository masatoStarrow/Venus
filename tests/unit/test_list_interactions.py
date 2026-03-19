"""
Unit tests for ListInteractions use case — filters and pagination.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.list_interactions import ListInteractions
from src.domain.entities.interaction import Interaction


def _make_interaction(**kwargs) -> Interaction:
    defaults = {
        "id": uuid.uuid4(),
        "client_id": uuid.uuid4(),
        "agent_id": uuid.uuid4(),
        "type": "call",
        "channel": "phone",
        "status": "pending",
        "subject": "Test interaction",
        "interaction_date": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Interaction(**defaults)


@pytest.mark.asyncio
async def test_list_interactions_no_filters():
    interactions = [_make_interaction() for _ in range(3)]
    repo = AsyncMock()
    repo.list_interactions.return_value = (interactions, 3)

    use_case = ListInteractions(interaction_repository=repo)
    items, total = await use_case.execute()

    assert total == 3
    assert len(items) == 3
    repo.list_interactions.assert_called_once()


@pytest.mark.asyncio
async def test_list_interactions_filter_by_type():
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 0)

    use_case = ListInteractions(interaction_repository=repo)
    await use_case.execute(type_filter=["call", "email"])

    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["type_filter"] == ["call", "email"]


@pytest.mark.asyncio
async def test_list_interactions_filter_by_status():
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 0)

    use_case = ListInteractions(interaction_repository=repo)
    await use_case.execute(status_filter=["pending", "in_progress"])

    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["status_filter"] == ["pending", "in_progress"]


@pytest.mark.asyncio
async def test_list_interactions_pagination():
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 50)

    use_case = ListInteractions(interaction_repository=repo)
    _, total = await use_case.execute(page=3, page_size=5)

    assert total == 50
    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["page"] == 3
    assert call_kwargs["page_size"] == 5


@pytest.mark.asyncio
async def test_list_interactions_agent_filter():
    """Comercial user passes agent_id to only see own interactions."""
    agent = uuid.uuid4()
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 0)

    use_case = ListInteractions(interaction_repository=repo)
    await use_case.execute(agent_id=agent)

    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["agent_id"] == agent


@pytest.mark.asyncio
async def test_list_interactions_date_range():
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 0)
    d_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    d_to = datetime(2026, 12, 31, tzinfo=timezone.utc)

    use_case = ListInteractions(interaction_repository=repo)
    await use_case.execute(date_from=d_from, date_to=d_to)

    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["date_from"] == d_from
    assert call_kwargs["date_to"] == d_to


@pytest.mark.asyncio
async def test_list_interactions_ordering():
    repo = AsyncMock()
    repo.list_interactions.return_value = ([], 0)

    use_case = ListInteractions(interaction_repository=repo)
    await use_case.execute(order_by="created_at", order_dir="asc")

    call_kwargs = repo.list_interactions.call_args[1]
    assert call_kwargs["order_by"] == "created_at"
    assert call_kwargs["order_dir"] == "asc"
