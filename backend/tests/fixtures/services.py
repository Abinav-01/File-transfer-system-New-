"""Real-service isolation for API and integration tests."""

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.core.minio import get_minio_client
from app.core.redis import get_redis_client


@pytest.fixture(autouse=True)
def isolated_state(request):
    if "unit" in request.node.path.parts:
        yield
        return
    if (
        "dropvault_test" not in settings.DATABASE_URL
        or "minio-test" not in settings.MINIO_ENDPOINT
    ):
        pytest.fail(
            "API and integration tests require the isolated Compose test services"
        )
    minio = get_minio_client()
    try:
        minio.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
    except ClientError as error:
        if error.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            raise
        minio.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)

    def clean():
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE uploads RESTART IDENTITY CASCADE"))
        redis = get_redis_client()
        redis.flushdb()
        listing = minio.list_objects_v2(Bucket=settings.MINIO_BUCKET_NAME)
        for item in listing.get("Contents", []):
            minio.delete_object(Bucket=settings.MINIO_BUCKET_NAME, Key=item["Key"])

    clean()
    yield
    clean()
