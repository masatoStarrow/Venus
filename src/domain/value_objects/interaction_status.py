"""
Value object: InteractionStatus enum.
"""

from enum import Enum


class InteractionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
