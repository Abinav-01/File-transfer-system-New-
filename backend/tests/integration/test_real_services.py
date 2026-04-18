"""End-to-end lifecycle checks with dedicated PostgreSQL, Redis, and MinIO containers."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.minio import get_minio_client
from app.core.redis import get_redis_client
from app.main import app
from app.models.upload import Upload, UploadStatus
from app.workers.tasks import cleanup_expired_uploads


def test_upload_postgres_minio_download_counter(client, upload_factory, db):
    data = upload_factory(content=b"real integration bytes")
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row is not None
    response = get_minio_client().get_object(
        Bucket=settings.MINIO_BUCKET_NAME, Key=row.storage_key
    )
    try:
        assert response["Body"].read() == b"real integration bytes"
    finally:
        response["Body"].close()
    download = client.post(f"/api/files/{data['share_token']}/download", json={})
    assert download.status_code == 200
    assert download.content == b"real integration bytes"
    db.refresh(row)
    assert row.download_count == 1


def test_expire_cleanup_removes_object_once(upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    key = row.storage_key
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert cleanup_expired_uploads() == {"processed": 1, "failed": 0}
    assert cleanup_expired_uploads() == {"processed": 0, "failed": 0}
    db.refresh(row)
    assert row.status == UploadStatus.EXPIRED
    assert row.object_deleted_at is not None
    with pytest.raises(ClientError) as error:
        get_minio_client().head_object(Bucket=settings.MINIO_BUCKET_NAME, Key=key)
    assert error.value.response["Error"]["Code"] in ("404", "NoSuchKey")


@pytest.mark.asyncio
async def test_concurrent_last_download_exactly_one_wins(upload_factory, db):
    data = upload_factory(max_downloads=1)
    release = asyncio.Event()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:

        async def attempt():
            await release.wait()
            return (
                await client.post(f"/api/files/{data['share_token']}/download", json={})
            ).status_code

        tasks = [asyncio.create_task(attempt()) for _ in range(8)]
        release.set()
        results = await asyncio.gather(*tasks)
    assert results.count(200) == 1
    assert results.count(410) == 7
    row = db.get(Upload, uuid.UUID(data["id"]))
    db.refresh(row)
    assert row.download_count == 1
    assert row.status == UploadStatus.DOWNLOAD_LIMIT_REACHED


def test_password_failures_lock_then_redis_reset(client, upload_factory, db):
    data = upload_factory(password="correct")
    path = f"/api/files/{data['share_token']}/download"
    for _ in range(settings.PASSWORD_FAILURE_LIMIT):
        assert client.post(path, json={"password": "wrong"}).status_code == 401
    assert client.post(path, json={"password": "correct"}).status_code == 429
    assert db.get(Upload, uuid.UUID(data["id"])).download_count == 0
    redis = get_redis_client()
    password_keys = list(redis.scan_iter("dropvault:rate:password:*"))
    assert len(password_keys) == 1
    assert redis.ttl(password_keys[0]) > 0
    redis.delete(password_keys[0])
    assert client.post(path, json={"password": "correct"}).status_code == 200


def test_storage_unavailable_does_not_consume_download(client, upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    get_minio_client().delete_object(
        Bucket=settings.MINIO_BUCKET_NAME, Key=row.storage_key
    )
    response = client.post(f"/api/files/{data['share_token']}/download", json={})
    assert response.status_code == 503
    db.refresh(row)
    assert row.download_count == 0


def test_cleanup_failure_does_not_block_other_files(upload_factory, db, monkeypatch):
    from app.workers import tasks

    first = upload_factory(filename="first.txt")
    second = upload_factory(filename="second.txt")
    first_row = db.get(Upload, uuid.UUID(first["id"]))
    second_row = db.get(Upload, uuid.UUID(second["id"]))
    first_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    second_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    original_delete = tasks.delete_file_from_minio

    def delete_one(key):
        if key == first_row.storage_key:
            raise RuntimeError("simulated MinIO outage for one object")
        return original_delete(key)

    monkeypatch.setattr(tasks, "delete_file_from_minio", delete_one)
    result = cleanup_expired_uploads()
    assert result == {"processed": 1, "failed": 1}
    db.refresh(first_row)
    db.refresh(second_row)
    assert (
        first_row.status == UploadStatus.ACTIVE and first_row.object_deleted_at is None
    )
    assert (
        second_row.status == UploadStatus.EXPIRED
        and second_row.object_deleted_at is not None
    )
    monkeypatch.setattr(tasks, "delete_file_from_minio", original_delete)
    assert cleanup_expired_uploads() == {"processed": 1, "failed": 0}
