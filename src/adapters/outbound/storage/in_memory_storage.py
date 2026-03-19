"""
In-memory implementation of FileStorage for testing.
"""

from src.domain.ports.file_storage import FileStorage


class InMemoryStorage(FileStorage):
    def __init__(self) -> None:
        self._files: dict[str, tuple[bytes, str]] = {}

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        self._files[key] = (data, content_type)
        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        if key not in self._files:
            raise FileNotFoundError(f"Key not found: {key}")
        return f"https://fake-s3.test/{key}?expires={expires_in}"

    async def delete(self, key: str) -> None:
        self._files.pop(key, None)
