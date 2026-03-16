"""
Value object: UserRole enum (mirrored from users-service for header validation).
"""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    SOPORTE = "soporte"
    COMERCIAL = "comercial"
