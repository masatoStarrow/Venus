"""
ABC: FileStorage — contract for external file storage (S3, local, etc.).
"""

from abc import ABC, abstractmethod


class FileStorage(ABC):

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload file and return the storage key."""
        ...

    @abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a file from storage."""
        ...
