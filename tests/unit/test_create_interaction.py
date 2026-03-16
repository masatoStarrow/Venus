"""
Unit tests for CreateInteraction use case.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.interaction_dto import CreateInteractionDTO
from src.application.use_cases.create_interaction import CreateInteraction
from src.domain.entities.interaction import Interaction


@pytest.mark.asyncio
async def test_create_interaction_success():
    repo = AsyncMock()
    repo.create.side_effect = lambda i: i

    use_case = CreateInteraction(interaction_repository=repo)
    dto = CreateInteractionDTO(
        client_id=uuid.uuid4(),
        type="call",
        channel="phone",
        subject="Llamada de seguimiento",
        interaction_date=datetime.now(timezone.utc),
    )
    agent_id = uuid.uuid4()
    result = await use_case.execute(dto, agent_id=agent_id)

    assert result.agent_id == agent_id
    assert result.type == "call"
    assert result.channel == "phone"
    assert result.subject == "Llamada de seguimiento"
    assert result.status == "pending"
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_interaction_assigns_uuid():
    repo = AsyncMock()
    repo.create.side_effect = lambda i: i

    use_case = CreateInteraction(interaction_repository=repo)
    dto = CreateInteractionDTO(
        client_id=uuid.uuid4(),
        type="meeting",
        channel="in_person",
        subject="Reunión presencial",
        interaction_date=datetime.now(timezone.utc),
    )
    result = await use_case.execute(dto, agent_id=uuid.uuid4())

    assert result.id is not None


@pytest.mark.asyncio
async def test_create_interaction_strips_subject():
    repo = AsyncMock()
    repo.create.side_effect = lambda i: i

    use_case = CreateInteraction(interaction_repository=repo)
    dto = CreateInteractionDTO(
        client_id=uuid.uuid4(),
        type="note",
        channel="platform",
        subject="  Nota con espacios  ",
        interaction_date=datetime.now(timezone.utc),
    )
    result = await use_case.execute(dto, agent_id=uuid.uuid4())

    assert result.subject == "Nota con espacios"


@pytest.mark.asyncio
async def test_create_interaction_default_status_pending():
    repo = AsyncMock()
    repo.create.side_effect = lambda i: i

    use_case = CreateInteraction(interaction_repository=repo)
    dto = CreateInteractionDTO(
        client_id=uuid.uuid4(),
        type="ticket",
        channel="platform",
        subject="Ticket de soporte",
        interaction_date=datetime.now(timezone.utc),
    )
    result = await use_case.execute(dto, agent_id=uuid.uuid4())

    assert result.status == "pending"


@pytest.mark.asyncio
async def test_create_interaction_with_all_optional_fields():
    repo = AsyncMock()
    repo.create.side_effect = lambda i: i
    follow_up = datetime(2026, 4, 1, tzinfo=timezone.utc)

    use_case = CreateInteraction(interaction_repository=repo)
    dto = CreateInteractionDTO(
        client_id=uuid.uuid4(),
        type="call",
        channel="phone",
        subject="Llamada completa",
        status="in_progress",
        notes="Notas detalladas",
        internal_notes="Solo para agentes",
        outcome="Pendiente de respuesta",
        interaction_date=datetime.now(timezone.utc),
        follow_up_date=follow_up,
        duration_minutes=30,
    )
    result = await use_case.execute(dto, agent_id=uuid.uuid4())

    assert result.status == "in_progress"
    assert result.notes == "Notas detalladas"
    assert result.internal_notes == "Solo para agentes"
    assert result.outcome == "Pendiente de respuesta"
    assert result.follow_up_date == follow_up
    assert result.duration_minutes == 30
