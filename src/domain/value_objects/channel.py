"""
Value object: Channel enum.
"""

from enum import Enum


class Channel(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    IN_PERSON = "in_person"
    PLATFORM = "platform"
