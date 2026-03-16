"""
Unit tests for ListPendingFollowUps and ListOverdueFollowUps use cases.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.list_follow_ups import (
    ListPendingFollowUps,
    ListOverdueFollowUps,
)
from src.domain.entities.interaction import Interaction


def _make_interaction(**kwargs) -> Interaction:
    defaults = {
        "id": uuid.uuid4(),
        "client_id": uuid.uuid4(),
        "agent_id": uuid.uuid4(),
        "type": "call",
        "channel": "phone",
        "status": "pending",
        "subject": "Follow-up test",
        "interaction_date": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Interaction(**defaults)


# ── ListPendingFollowUps ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_follow_ups_returns_future():
    agent_id = uuid.uuid4()
    future = datetime.now(timezone.utc) + timedelta(days=7)
    interactions = [
        _make_interaction(agent_id=agent_id, follow_up_date=future),
    ]
    repo = AsyncMock()
    repo.get_pending_follow_ups.return_value = (interactions, 1)

    use_case = ListPendingFollowUps(interaction_repository=repo)
    items, total = await use_case.execute(agent_id)

    assert total == 1
    assert len(items) == 1
    repo.get_pending_follow_ups.assert_called_once_with(
        agent_id, page=1, page_size=20
    )


@pytest.mark.asyncio
async def test_pending_follow_ups_pagination():
    agent_id = uuid.uuid4()
    repo = AsyncMock()
    repo.get_pending_follow_ups.return_value = ([], 0)

    use_case = ListPendingFollowUps(interaction_repository=repo)
    await use_case.execute(agent_id, page=2, page_size=5)

    repo.get_pending_follow_ups.assert_called_once_with(
        agent_id, page=2, page_size=5
    )


@pytest.mark.asyncio
async def test_pending_follow_ups_empty():
    agent_id = uuid.uuid4()
    repo = AsyncMock()
    repo.get_pending_follow_ups.return_value = ([], 0)

    use_case = ListPendingFollowUps(interaction_repository=repo)
    items, total = await use_case.execute(agent_id)

    assert total == 0
    assert items == []


# ── ListOverdueFollowUps ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_overdue_follow_ups_returns_past():
    past = datetime.now(timezone.utc) - timedelta(days=3)
    interactions = [
        _make_interaction(follow_up_date=past, status="pending"),
        _make_interaction(follow_up_date=past, status="in_progress"),
    ]
    repo = AsyncMock()
    repo.get_overdue_follow_ups.return_value = (interactions, 2)

    use_case = ListOverdueFollowUps(interaction_repository=repo)
    items, total = await use_case.execute()

    assert total == 2
    repo.get_overdue_follow_ups.assert_called_once_with(page=1, page_size=20)


@pytest.mark.asyncio
async def test_overdue_follow_ups_pagination():
    repo = AsyncMock()
    repo.get_overdue_follow_ups.return_value = ([], 0)

    use_case = ListOverdueFollowUps(interaction_repository=repo)
    await use_case.execute(page=3, page_size=10)

    repo.get_overdue_follow_ups.assert_called_once_with(page=3, page_size=10)
