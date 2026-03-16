"""
Value object: InteractionType enum.
"""

from enum import Enum


class InteractionType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TICKET = "ticket"
    NOTE = "note"
