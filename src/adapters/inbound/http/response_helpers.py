"""
Helper to build standard envelope responses.
"""

import math
from typing import Any


def success_response(data: Any, message: str = "OK") -> dict:
    return {"success": True, "data": data, "message": message}


def paginated_response(
    items: list[dict],
    total: int,
    page: int,
    page_size: int,
) -> dict:
    pages = math.ceil(total / page_size) if page_size > 0 else 0
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        },
    }


def error_response(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
