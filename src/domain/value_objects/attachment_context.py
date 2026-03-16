"""
Value object: AttachmentContext — where the attachment belongs.
"""

from enum import StrEnum


class AttachmentContext(StrEnum):
    INTERNAL_NOTE = "internal_note"
    NOTE = "note"
