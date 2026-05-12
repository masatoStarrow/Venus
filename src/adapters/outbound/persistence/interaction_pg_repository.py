"""
PostgreSQL implementation of InteractionRepository using SQLAlchemy async.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.interaction import Interaction
from src.domain.ports.interaction_repository import InteractionRepository
from src.adapters.outbound.persistence.models.interaction_model import InteractionModel


class InteractionPgRepository(InteractionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: InteractionModel) -> Interaction:
        return Interaction(
            id=model.id,
            client_id=model.client_id,
            agent_id=model.agent_id,
            type=model.type,
            channel=model.channel,
            status=model.status,
            subject=model.subject,
            notes=model.notes,
            internal_notes=model.internal_notes,
            outcome=model.outcome,
            interaction_date=model.interaction_date,
            follow_up_date=model.follow_up_date,
            duration_minutes=model.duration_minutes,
            is_deleted=model.is_deleted,
            last_edited_by=model.last_edited_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def _base_filters(self, stmt, *, include_deleted: bool = False):
        """Apply soft-delete filter."""
        if not include_deleted:
            stmt = stmt.where(InteractionModel.is_deleted == False)  # noqa: E712
        return stmt

    def _apply_list_filters(
        self,
        stmt,
        *,
        client_id=None,
        agent_id=None,
        client_ids=None,
        type_filter=None,
        channel_filter=None,
        status_filter=None,
        date_from=None,
        date_to=None,
    ):
        if client_id is not None:
            stmt = stmt.where(InteractionModel.client_id == client_id)
        if agent_id is not None:
            stmt = stmt.where(InteractionModel.agent_id == agent_id)
        if client_ids is not None:
            stmt = stmt.where(InteractionModel.client_id.in_(client_ids))
        if type_filter:
            stmt = stmt.where(InteractionModel.type.in_(type_filter))
        if channel_filter:
            stmt = stmt.where(InteractionModel.channel.in_(channel_filter))
        if status_filter:
            stmt = stmt.where(InteractionModel.status.in_(status_filter))
        if date_from is not None:
            stmt = stmt.where(InteractionModel.interaction_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(InteractionModel.interaction_date <= date_to)
        return stmt

    def _apply_ordering(
        self, stmt, order_by: str = "interaction_date", order_dir: str = "desc"
    ):
        column_map = {
            "interaction_date": InteractionModel.interaction_date,
            "created_at": InteractionModel.created_at,
            "updated_at": InteractionModel.updated_at,
        }
        col = column_map.get(order_by, InteractionModel.interaction_date)
        return stmt.order_by(col.desc() if order_dir == "desc" else col.asc())

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def get_by_id(self, interaction_id: UUID) -> Interaction | None:
        result = await self._session.get(InteractionModel, interaction_id)
        return self._to_entity(result) if result else None

    async def get_owned_client_ids(self, agent_id: UUID) -> list[UUID]:
        stmt = (
            select(InteractionModel.client_id.distinct())
            .where(
                InteractionModel.agent_id == agent_id,
                InteractionModel.is_deleted == False,  # noqa: E712
            )
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def list_interactions(
        self,
        *,
        client_id=None,
        agent_id=None,
        client_ids=None,
        type_filter=None,
        channel_filter=None,
        status_filter=None,
        date_from=None,
        date_to=None,
        tags=None,
        page=1,
        page_size=20,
        order_by="interaction_date",
        order_dir="desc",
    ) -> tuple[list[Interaction], int]:
        base = self._base_filters(select(InteractionModel))
        base = self._apply_list_filters(
            base,
            client_id=client_id,
            agent_id=agent_id,
            client_ids=client_ids,
            type_filter=type_filter,
            channel_filter=channel_filter,
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to,
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = self._apply_ordering(base, order_by, order_dir)
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def list_by_client(
        self,
        client_id: UUID,
        *,
        agent_id=None,
        type_filter=None,
        status_filter=None,
        agent_id_filter=None,
        date_from=None,
        date_to=None,
        page=1,
        page_size=20,
        order_by="interaction_date",
        order_dir="desc",
    ) -> tuple[list[Interaction], int]:
        base = self._base_filters(select(InteractionModel))
        base = base.where(InteractionModel.client_id == client_id)

        if agent_id is not None:
            base = base.where(InteractionModel.agent_id == agent_id)
        if type_filter:
            base = base.where(InteractionModel.type.in_(type_filter))
        if status_filter:
            base = base.where(InteractionModel.status.in_(status_filter))
        if agent_id_filter:
            base = base.where(InteractionModel.agent_id.in_(agent_id_filter))
        if date_from is not None:
            base = base.where(InteractionModel.interaction_date >= date_from)
        if date_to is not None:
            base = base.where(InteractionModel.interaction_date <= date_to)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = self._apply_ordering(base, order_by, order_dir)
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def create(self, interaction: Interaction) -> Interaction:
        model = InteractionModel(
            id=interaction.id,
            client_id=interaction.client_id,
            agent_id=interaction.agent_id,
            type=interaction.type,
            channel=interaction.channel,
            status=interaction.status,
            subject=interaction.subject,
            notes=interaction.notes,
            internal_notes=interaction.internal_notes,
            outcome=interaction.outcome,
            interaction_date=interaction.interaction_date,
            follow_up_date=interaction.follow_up_date,
            duration_minutes=interaction.duration_minutes,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, interaction: Interaction) -> Interaction:
        model = await self._session.get(InteractionModel, interaction.id)
        if model is None:
            raise ValueError(f"Interaction {interaction.id} not found")

        model.type = interaction.type
        model.channel = interaction.channel
        model.status = interaction.status
        model.subject = interaction.subject
        model.notes = interaction.notes
        model.internal_notes = interaction.internal_notes
        model.outcome = interaction.outcome
        model.follow_up_date = interaction.follow_up_date
        model.duration_minutes = interaction.duration_minutes
        model.last_edited_by = interaction.last_edited_by
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, interaction_id: UUID) -> Interaction:
        model = await self._session.get(InteractionModel, interaction_id)
        if model is None:
            raise ValueError(f"Interaction {interaction_id} not found")

        model.is_deleted = True
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    # ── Aggregations ─────────────────────────────────────────────────────

    async def get_client_summary(
        self, client_id: UUID, *, agent_id: UUID | None = None
    ) -> dict:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        base_where = and_(
            InteractionModel.client_id == client_id,
            InteractionModel.is_deleted == False,  # noqa: E712
        )
        if agent_id is not None:
            base_where = and_(base_where, InteractionModel.agent_id == agent_id)

        stmt = select(
            func.count().label("total_interactions"),
            func.sum(
                case((InteractionModel.interaction_date >= thirty_days_ago, 1), else_=0)
            ).label("interactions_last_30_days"),
            # by type
            func.sum(case((InteractionModel.type == "call", 1), else_=0)).label(
                "type_call"
            ),
            func.sum(case((InteractionModel.type == "email", 1), else_=0)).label(
                "type_email"
            ),
            func.sum(case((InteractionModel.type == "meeting", 1), else_=0)).label(
                "type_meeting"
            ),
            func.sum(case((InteractionModel.type == "ticket", 1), else_=0)).label(
                "type_ticket"
            ),
            func.sum(case((InteractionModel.type == "note", 1), else_=0)).label(
                "type_note"
            ),
            # by status
            func.sum(case((InteractionModel.status == "pending", 1), else_=0)).label(
                "status_pending"
            ),
            func.sum(
                case((InteractionModel.status == "in_progress", 1), else_=0)
            ).label("status_in_progress"),
            func.sum(case((InteractionModel.status == "resolved", 1), else_=0)).label(
                "status_resolved"
            ),
            func.sum(case((InteractionModel.status == "closed", 1), else_=0)).label(
                "status_closed"
            ),
            # dates
            func.max(InteractionModel.interaction_date).label("last_interaction_date"),
            func.min(
                case(
                    (
                        and_(
                            InteractionModel.follow_up_date > now,
                            InteractionModel.status.not_in(["resolved", "closed"]),
                        ),
                        InteractionModel.follow_up_date,
                    ),
                    else_=None,
                )
            ).label("next_follow_up_date"),
            # open tickets
            func.sum(
                case(
                    (
                        and_(
                            InteractionModel.type == "ticket",
                            InteractionModel.status.in_(["pending", "in_progress"]),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("open_tickets"),
        ).where(base_where)

        result = await self._session.execute(stmt)
        row = result.one()

        total = row.total_interactions or 0
        resolved_closed = (row.status_resolved or 0) + (row.status_closed or 0)
        completion_rate = (
            round(resolved_closed * 100.0 / total, 2) if total > 0 else 0.0
        )

        return {
            "client_id": str(client_id),
            "total_interactions": total,
            "interactions_last_30_days": row.interactions_last_30_days or 0,
            "by_type": {
                "call": row.type_call or 0,
                "email": row.type_email or 0,
                "meeting": row.type_meeting or 0,
                "ticket": row.type_ticket or 0,
                "note": row.type_note or 0,
            },
            "by_status": {
                "pending": row.status_pending or 0,
                "in_progress": row.status_in_progress or 0,
                "resolved": row.status_resolved or 0,
                "closed": row.status_closed or 0,
            },
            "completion_rate": completion_rate,
            "last_interaction_date": row.last_interaction_date,
            "next_follow_up_date": row.next_follow_up_date,
            "open_tickets": row.open_tickets or 0,
        }

    async def get_metrics(self, *, agent_id: UUID | None = None, client_ids: list[UUID] | None = None) -> dict:
        base_where = InteractionModel.is_deleted == False  # noqa: E712
        if agent_id is not None:
            base_where = and_(base_where, InteractionModel.agent_id == agent_id)
        if client_ids is not None:
            base_where = and_(base_where, InteractionModel.client_id.in_(client_ids))

        # Global aggregates
        stmt = select(
            func.count(InteractionModel.client_id.distinct()).label("total_clients"),
            func.count().label("total_interactions"),
        ).where(base_where)

        result = await self._session.execute(stmt)
        row = result.one()

        total_clients = row.total_clients or 0
        total_interactions = row.total_interactions or 0
        avg = round(total_interactions / total_clients, 2) if total_clients > 0 else 0.0

        # Per-client breakdown
        per_client_stmt = (
            select(
                InteractionModel.client_id,
                func.count().label("interaction_count"),
                func.max(InteractionModel.interaction_date).label(
                    "last_interaction_date"
                ),
            )
            .where(base_where)
            .group_by(InteractionModel.client_id)
            .order_by(func.count().desc())
        )
        per_client_result = await self._session.execute(per_client_stmt)
        per_client = [
            {
                "client_id": str(r.client_id),
                "interaction_count": r.interaction_count,
                "last_interaction_date": r.last_interaction_date,
            }
            for r in per_client_result.all()
        ]

        return {
            "total_clients": total_clients,
            "total_interactions": total_interactions,
            "avg_interactions_per_client": avg,
            "per_client": per_client,
        }

    # ── Follow-ups ───────────────────────────────────────────────────────

    async def get_pending_follow_ups(
        self, agent_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]:
        now = datetime.now(timezone.utc)
        base = select(InteractionModel).where(
            InteractionModel.is_deleted == False,  # noqa: E712
            InteractionModel.agent_id == agent_id,
            InteractionModel.follow_up_date > now,
            InteractionModel.status.not_in(["closed"]),
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = base.order_by(InteractionModel.follow_up_date.asc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def get_overdue_follow_ups(
        self, agent_id: UUID | None = None, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Interaction], int]:
        now = datetime.now(timezone.utc)
        base = select(InteractionModel).where(
            InteractionModel.is_deleted == False,  # noqa: E712
            InteractionModel.follow_up_date != None,  # noqa: E711
            InteractionModel.follow_up_date < now,
            InteractionModel.status.not_in(["closed"]),
        )
        # Filtrar por agent_id si se proporciona (para comercial)
        if agent_id is not None:
            base = base.where(InteractionModel.agent_id == agent_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = base.order_by(InteractionModel.follow_up_date.asc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total
