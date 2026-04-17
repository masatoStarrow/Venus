"""
FastAPI router for /api/v1/interactions endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.http.dependencies import UserContext, get_current_user_context
from src.adapters.inbound.http.schemas.interaction_schema import (
    CreateInteractionRequest,
    UpdateInteractionRequest,
    CloseInteractionRequest,
    InteractionResponse,
    AuditEntryResponse,
    ClientSummaryResponse,
    MetricsResponse,
)
from src.adapters.inbound.http.response_helpers import (
    success_response,
    paginated_response,
    error_response,
)
from src.application.dtos.interaction_dto import (
    CreateInteractionDTO,
    UpdateInteractionDTO,
    CloseInteractionDTO,
)
from src.domain.exceptions import (
    InteractionNotFoundError,
    InteractionAlreadyClosedError,
    ForbiddenError,
)
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.database.connection import get_db
from src.infrastructure.di.container import (
    get_create_interaction_use_case,
    get_get_interaction_use_case,
    get_list_interactions_use_case,
    get_list_by_client_use_case,
    get_update_interaction_use_case,
    get_close_interaction_use_case,
    get_soft_delete_interaction_use_case,
    get_get_client_summary_use_case,
    get_get_metrics_use_case,
    get_list_pending_follow_ups_use_case,
    get_list_overdue_follow_ups_use_case,
    get_get_audit_log_use_case,
)

router = APIRouter(prefix="/api/v1/interactions", tags=["Interactions"])


# ── Helpers ───────────────────────────────────────────────────────────────


def _split_csv(value: str | None) -> list[str] | None:
    """Split a comma-separated query parameter into a list."""
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _interaction_json(entity) -> dict:
    return InteractionResponse.model_validate(entity.__dict__).model_dump(mode="json")


# ── GET /metrics ──────────────────────────────────────────────────────────


@router.get(
    "/metrics",
    summary="Métricas globales de interacciones",
    description=(
        "Retorna total de clientes, total de interacciones y promedio "
        "de interacciones por cliente. Comercial solo ve sus propias."
    ),
)
async def get_metrics(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_get_metrics_use_case(db)
    agent_id = context.user_id if context.role == UserRole.COMERCIAL else None
    result = await use_case.execute(agent_id=agent_id)
    data = MetricsResponse(**result).model_dump()
    return success_response(data)


# ── GET /follow-ups/pending ───────────────────────────────────────────────


@router.get(
    "/follow-ups/pending",
    summary="Seguimientos pendientes del agente",
    description="Interacciones con follow_up_date futuro asignadas al agente autenticado.",
)
async def list_pending_follow_ups(
    context: UserContext = Depends(get_current_user_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_pending_follow_ups_use_case(db)
    items, total = await use_case.execute(
        context.user_id, page=page, page_size=page_size
    )
    data = [_interaction_json(i) for i in items]
    return paginated_response(items=data, total=total, page=page, page_size=page_size)


# ── GET /follow-ups/overdue ──────────────────────────────────────────────


@router.get(
    "/follow-ups/overdue",
    summary="Seguimientos vencidos",
    description="Interacciones con follow_up_date pasado y estado != closed.",
)
async def list_overdue_follow_ups(
    context: UserContext = Depends(get_current_user_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_overdue_follow_ups_use_case(db)
    items, total = await use_case.execute(page=page, page_size=page_size)
    data = [_interaction_json(i) for i in items]
    return paginated_response(items=data, total=total, page=page, page_size=page_size)


# ── GET /client/{client_id} ──────────────────────────────────────────────


@router.get(
    "/client/{client_id}",
    summary="Historial de interacciones de un cliente",
    description="Lista paginada de interacciones para un client_id determinado.",
)
async def list_by_client(
    client_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    type: str | None = Query(None, description="Filtrar por tipo (csv)"),
    client_status: str | None = Query(
        None, alias="status", description="Filtrar por estado (csv)"
    ),
    agent_id: str | None = Query(None, description="Filtrar por agente (csv UUIDs)"),
    date_from: datetime | None = Query(None, description="Fecha inicio (ISO 8601)"),
    date_to: datetime | None = Query(None, description="Fecha fin (ISO 8601)"),
    order_by: str = Query("interaction_date", description="Campo de ordenamiento"),
    order_dir: str = Query("desc", description="Dirección (asc/desc)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_by_client_use_case(db)
    forced_agent = context.user_id if context.role == UserRole.COMERCIAL else None
    items, total = await use_case.execute(
        client_id,
        agent_id=forced_agent,
        type_filter=_split_csv(type),
        status_filter=_split_csv(client_status),
        agent_id_filter=_split_csv(agent_id) if forced_agent is None else None,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_dir=order_dir,
    )
    data = [_interaction_json(i) for i in items]
    return paginated_response(items=data, total=total, page=page, page_size=page_size)


# ── GET /client/{client_id}/summary ───────────────────────────────────────


@router.get(
    "/client/{client_id}/summary",
    summary="Resumen de interacciones de un cliente",
    description=(
        "Estadísticas agregadas: total, últimos 30 días, por tipo/estado, "
        "tasa de resolución, tickets abiertos, etc."
    ),
)
async def get_client_summary(
    client_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_get_client_summary_use_case(db)
    agent_id = context.user_id if context.role == UserRole.COMERCIAL else None
    result = await use_case.execute(client_id, agent_id=agent_id)
    data = ClientSummaryResponse(**result).model_dump(mode="json")
    return success_response(data)


# ── GET / ─────────────────────────────────────────────────────────────────


@router.get(
    "/",
    summary="Listar interacciones",
    description=(
        "Lista paginada con filtros por tipo, canal, estado, "
        "fecha. Comercial ve solo sus propias interacciones."
    ),
)
async def list_interactions(
    context: UserContext = Depends(get_current_user_context),
    type: str | None = Query(None, description="Tipo(s) separados por coma"),
    channel: str | None = Query(None, description="Canal(es) separados por coma"),
    client_status: str | None = Query(
        None, alias="status", description="Estado(s) separados por coma"
    ),
    client_id: UUID | None = Query(None, description="Filtrar por ID de cliente"),
    date_from: datetime | None = Query(None, description="Fecha inicio (ISO 8601)"),
    date_to: datetime | None = Query(None, description="Fecha fin (ISO 8601)"),
    order_by: str = Query("interaction_date", description="Campo de ordenamiento"),
    order_dir: str = Query("desc", description="Dirección (asc/desc)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_interactions_use_case(db)
    forced_agent = context.user_id if context.role == UserRole.COMERCIAL else None
    items, total = await use_case.execute(
        client_id=client_id,
        agent_id=forced_agent,
        type_filter=_split_csv(type),
        channel_filter=_split_csv(channel),
        status_filter=_split_csv(client_status),
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_dir=order_dir,
    )
    data = [_interaction_json(i) for i in items]
    return paginated_response(items=data, total=total, page=page, page_size=page_size)


# ── POST / ────────────────────────────────────────────────────────────────


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear interacción",
    description="Registra una nueva interacción. Todos los roles pueden crear.",
    responses={403: {"description": "Forbidden"}},
)
async def create_interaction(
    body: CreateInteractionRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = CreateInteractionDTO(
        client_id=body.client_id,
        type=body.type.value,
        channel=body.channel.value,
        subject=body.subject,
        status=body.status.value,
        notes=body.notes,
        internal_notes=body.internal_notes,
        outcome=body.outcome,
        interaction_date=body.interaction_date,
        follow_up_date=body.follow_up_date,
        duration_minutes=body.duration_minutes,
    )
    use_case = get_create_interaction_use_case(db)
    interaction = await use_case.execute(dto, agent_id=context.user_id)
    data = _interaction_json(interaction)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success_response(data, "Interacción creada exitosamente"),
    )


# ── GET /{interaction_id} ────────────────────────────────────────────────


@router.get(
    "/{interaction_id}",
    summary="Obtener interacción por ID",
    responses={404: {"description": "Not found"}},
)
async def get_interaction(
    interaction_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_get_interaction_use_case(db)
    try:
        interaction = await use_case.execute(interaction_id)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    # Verificar ownership para comercial
    if context.role == UserRole.COMERCIAL and interaction.agent_id != context.user_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response(
                "FORBIDDEN", "Comercial solo puede ver sus propias interacciones"
            ),
        )

    data = _interaction_json(interaction)
    return success_response(data)


# ── PUT /{interaction_id} ────────────────────────────────────────────────


@router.put(
    "/{interaction_id}",
    summary="Actualizar interacción",
    description="Actualiza campos de una interacción. Admin/Soporte: todas. Comercial: solo sus propias.",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def update_interaction(
    interaction_id: UUID,
    body: UpdateInteractionRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    # Verificar ownership para comercial
    if context.role == UserRole.COMERCIAL:
        get_uc = get_get_interaction_use_case(db)
        try:
            interaction = await get_uc.execute(interaction_id)
            if interaction.agent_id != context.user_id:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content=error_response(
                        "FORBIDDEN",
                        "Comercial solo puede editar sus propias interacciones",
                    ),
                )
        except InteractionNotFoundError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Interacción no encontrada"),
            )

    dto = UpdateInteractionDTO(
        type=body.type.value if body.type else None,
        channel=body.channel.value if body.channel else None,
        status=body.status.value if body.status else None,
        subject=body.subject,
        notes=body.notes,
        internal_notes=body.internal_notes,
        outcome=body.outcome,
        follow_up_date=body.follow_up_date,
        duration_minutes=body.duration_minutes,
    )
    use_case = get_update_interaction_use_case(db)

    try:
        interaction = await use_case.execute(
            interaction_id, dto, editor_id=context.user_id
        )
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = _interaction_json(interaction)
    return success_response(data)


# ── DELETE /{interaction_id} ──────────────────────────────────────────────


@router.delete(
    "/{interaction_id}",
    summary="Eliminar interacción (soft delete)",
    description="Solo admin puede eliminar (soft delete).",
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def delete_interaction(
    interaction_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if context.role != UserRole.ADMIN:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response(
                "FORBIDDEN", "Solo admin puede eliminar interacciones"
            ),
        )

    use_case = get_soft_delete_interaction_use_case(db)
    try:
        interaction = await use_case.execute(interaction_id)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = _interaction_json(interaction)
    return success_response(data)


# ── PATCH /{interaction_id}/close ─────────────────────────────────────────


@router.patch(
    "/{interaction_id}/close",
    summary="Cerrar interacción",
    description="Cambia status a 'closed'. Admin/Soporte: todas. Comercial: solo sus propias.",
    responses={
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
        409: {"description": "Already closed"},
    },
)
async def close_interaction(
    interaction_id: UUID,
    body: CloseInteractionRequest | None = None,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    # Verificar ownership para comercial
    if context.role == UserRole.COMERCIAL:
        get_uc = get_get_interaction_use_case(db)
        try:
            interaction = await get_uc.execute(interaction_id)
            if interaction.agent_id != context.user_id:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content=error_response(
                        "FORBIDDEN",
                        "Comercial solo puede cerrar sus propias interacciones",
                    ),
                )
        except InteractionNotFoundError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Interacción no encontrada"),
            )

    dto = CloseInteractionDTO(outcome=body.outcome if body else None)
    use_case = get_close_interaction_use_case(db)

    try:
        interaction = await use_case.execute(
            interaction_id, dto, editor_id=context.user_id
        )
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except InteractionAlreadyClosedError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(e.code, e.message),
        )

    data = _interaction_json(interaction)
    return success_response(data)


# ── GET /{interaction_id}/audit ───────────────────────────────────────────


@router.get(
    "/{interaction_id}/audit",
    summary="Historial de cambios de una interacción",
    description="Retorna las entradas de auditoría (campo, valor anterior, valor nuevo).",
    responses={404: {"description": "Not found"}},
)
async def get_audit_log(
    interaction_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    # Verify interaction exists
    get_uc = get_get_interaction_use_case(db)
    try:
        await get_uc.execute(interaction_id)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    audit_uc = get_get_audit_log_use_case(db)
    entries = await audit_uc.execute(interaction_id)
    data = [
        AuditEntryResponse.model_validate(e.__dict__).model_dump(mode="json")
        for e in entries
    ]
    return success_response(data)
