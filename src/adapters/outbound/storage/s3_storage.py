"""
AWS S3 implementation of the FileStorage port using boto3.
"""

import boto3
from botocore.exceptions import ClientError

from src.domain.ports.file_storage import FileStorage
from config.settings import settings


class S3Storage(FileStorage):
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._bucket = settings.s3_bucket

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            url: str = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            raise RuntimeError(f"Error generating presigned URL: {e}") from e
        return url

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
