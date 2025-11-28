from __future__ import annotations

import asyncio
from functools import lru_cache
from io import BytesIO
from typing import BinaryIO

from minio import Minio

from app.config.settings import get_settings


class AsyncMinioClient:
    """Thin async wrapper around the MinIO SDK using thread executors."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    async def ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(
            self._client.bucket_exists,
            bucket_name=self.bucket,
        )
        if not exists:
            await asyncio.to_thread(self._client.make_bucket, bucket_name=self.bucket)

    async def upload(self, object_name: str, data: bytes, content_type: str) -> None:
        await self.ensure_bucket()
        stream = BytesIO(data)
        await asyncio.to_thread(
            self._client.put_object,
            bucket_name=self.bucket,
            object_name=object_name,
            data=stream,
            length=len(data),
            content_type=content_type,
        )

    async def download(self, object_name: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object,
            bucket_name=self.bucket,
            object_name=object_name,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def upload_stream(self, object_name: str, stream: BinaryIO, content_type: str) -> None:
        data = stream.read()
        await self.upload(object_name, data, content_type)


@lru_cache
def get_minio_client() -> AsyncMinioClient:
    return AsyncMinioClient()

