"""
FastAPI dependencies: extract internal headers from Gateway.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, status

from src.domain.value_objects.user_role import UserRole


@dataclass
class UserContext:
    user_id: UUID
    role: UserRole
    request_id: str


async def get_current_user_context(
    x_user_id: str = Header(..., description="UUID del usuario autenticado"),
    x_user_role: str = Header(..., description="Rol del usuario"),
    x_request_id: str = Header(default="", description="ID de correlación del request"),
) -> UserContext:
    """Extract user context from internal headers injected by the Gateway."""
    try:
        user_id = UUID(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "X-User-Id header must be a valid UUID",
                },
            },
        )

    try:
        role = UserRole(x_user_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Invalid role: {x_user_role}",
                },
            },
        )

    return UserContext(user_id=user_id, role=role, request_id=x_request_id)
