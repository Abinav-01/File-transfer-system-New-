from app.core.minio import get_minio_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def ensure_bucket_exists():
    client = get_minio_client()
    try:
        if not client.head_bucket(Bucket=settings.MINIO_BUCKET_NAME):
            client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
    except client.exceptions.ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            logger.info(
                f"Bucket {settings.MINIO_BUCKET_NAME} does not exist. Creating it."
            )
            client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
        else:
            raise e
    except Exception as error:
        logger.error("BUCKET_CHECK_FAILURE", extra={"error_type": type(error).__name__})
        # Boto3 might raise a different exception if bucket doesn't exist depending on the operation,
        # fallback for creating bucket
        try:
            client.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
        except Exception:
            pass  # ignore if it already exists


def upload_file_to_minio(file_obj, object_name: str, content_type: str):
    client = get_minio_client()
    ensure_bucket_exists()
    client.upload_fileobj(
        file_obj,
        settings.MINIO_BUCKET_NAME,
        object_name,
        ExtraArgs={"ContentType": content_type},
    )


def get_file_from_minio(object_name: str):
    return get_minio_client().get_object(
        Bucket=settings.MINIO_BUCKET_NAME, Key=object_name
    )


def delete_file_from_minio(object_name: str):
    client = get_minio_client()
    try:
        client.delete_object(Bucket=settings.MINIO_BUCKET_NAME, Key=object_name)
    except Exception:
        logger.error("Failed to delete object from MinIO")
        raise
