"""
FastAPI router for attachment endpoints under /api/v1/interactions/{interaction_id}/attachments.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.http.dependencies import UserContext, get_current_user_context
from src.adapters.inbound.http.schemas.attachment_schema import (
    AttachmentResponse,
    AttachmentDownloadResponse,
)
from src.adapters.inbound.http.response_helpers import success_response, error_response
from src.domain.exceptions import (
    InteractionNotFoundError,
    AttachmentNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from src.infrastructure.database.connection import get_db
from src.infrastructure.di.container import (
    get_upload_attachment_use_case,
    get_list_attachments_use_case,
    get_download_attachment_use_case,
    get_delete_attachment_use_case,
)

router = APIRouter(
    prefix="/api/v1/interactions/{interaction_id}/attachments",
    tags=["Attachments"],
)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Subir adjunto a una interacción",
    description="Sube un archivo al almacenamiento S3 y guarda los metadatos.",
)
async def upload_attachment(
    interaction_id: UUID,
    file: UploadFile = File(...),
    context_field: str = Query("internal_note", alias="context", description="Contexto: internal_note | note"),
    user: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_upload_attachment_use_case(db)
    file_data = await file.read()

    try:
        attachment = await use_case.execute(
            interaction_id=interaction_id,
            uploaded_by=user.user_id,
            file_name=file.filename or "unnamed",
            content_type=file.content_type or "application/octet-stream",
            file_data=file_data,
            context=context_field,
        )
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except FileTooLargeError as e:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=error_response(e.code, e.message),
        )
    except InvalidFileTypeError as e:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=error_response(e.code, e.message),
        )

    data = AttachmentResponse.model_validate(attachment.__dict__).model_dump(mode="json")
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success_response(data, "Adjunto subido exitosamente"),
    )


@router.get(
    "/",
    summary="Listar adjuntos de una interacción",
)
async def list_attachments(
    interaction_id: UUID,
    user: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_attachments_use_case(db)
    try:
        items = await use_case.execute(interaction_id)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = [
        AttachmentResponse.model_validate(a.__dict__).model_dump(mode="json")
        for a in items
    ]
    return success_response(data)


@router.get(
    "/{attachment_id}/download",
    summary="Obtener URL de descarga de un adjunto",
)
async def download_attachment(
    interaction_id: UUID,
    attachment_id: UUID,
    expires_in: int = Query(3600, ge=60, le=86400, description="Segundos de validez del enlace"),
    user: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_download_attachment_use_case(db)
    try:
        url = await use_case.execute(interaction_id, attachment_id, expires_in)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except AttachmentNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    attachment_uc = get_list_attachments_use_case(db)
    attachments = await attachment_uc.execute(interaction_id)
    match = next((a for a in attachments if a.id == attachment_id), None)
    data = AttachmentDownloadResponse(
        url=url,
        file_name=match.file_name if match else "",
        content_type=match.content_type if match else "",
    ).model_dump()
    return success_response(data)


@router.delete(
    "/{attachment_id}",
    summary="Eliminar adjunto",
    description="Elimina el archivo de S3 y su registro en la BD.",
)
async def delete_attachment(
    interaction_id: UUID,
    attachment_id: UUID,
    user: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_delete_attachment_use_case(db)
    try:
        await use_case.execute(interaction_id, attachment_id)
    except InteractionNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except AttachmentNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    return success_response(None, "Adjunto eliminado exitosamente")
