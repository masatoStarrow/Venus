"""
Shared test fixtures.
Uses SQLite async in-memory database for tests (no PostgreSQL needed).
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.infrastructure.database.connection import Base, get_db
from src.adapters.outbound.persistence.models.interaction_model import InteractionModel  # noqa: F401
from src.adapters.outbound.persistence.models.audit_model import AuditModel  # noqa: F401
from src.adapters.outbound.persistence.models.attachment_model import AttachmentModel  # noqa: F401
from src.adapters.outbound.storage.in_memory_storage import InMemoryStorage
from src.infrastructure.di.container import set_file_storage


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    set_file_storage(InMemoryStorage())
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provide a test DB session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide an HTTPX AsyncClient with DB dependency overridden."""
    from main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Seed fixtures ────────────────────────────────────────────────────────

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SOPORTE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
COMERCIAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
CLIENT_A_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
CLIENT_B_ID = uuid.UUID("00000000-0000-0000-0000-0000000000b2")

INTERNAL_HEADERS_ADMIN = {
    "X-User-Id": str(ADMIN_ID),
    "X-User-Role": "admin",
    "X-Request-Id": "test-req-001",
}

INTERNAL_HEADERS_SOPORTE = {
    "X-User-Id": str(SOPORTE_ID),
    "X-User-Role": "soporte",
    "X-Request-Id": "test-req-002",
}

INTERNAL_HEADERS_COMERCIAL = {
    "X-User-Id": str(COMERCIAL_ID),
    "X-User-Role": "comercial",
    "X-Request-Id": "test-req-003",
}


def _interaction_payload(**overrides) -> dict:
    """Generate a valid interaction request payload."""
    base = {
        "client_id": str(CLIENT_A_ID),
        "type": "call",
        "channel": "phone",
        "subject": "Llamada de seguimiento",
        "interaction_date": "2026-03-01T10:00:00Z",
        "notes": "Se habló sobre la propuesta",
    }
    base.update(overrides)
    return base
