"""Periodic object cleanup. Safe to run from Celery or the manual CLI."""

import logging
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.upload import Upload, UploadStatus
from app.services.minio_service import delete_file_from_minio
from app.services.rules import should_cleanup
from app.core.logging import domain_event
from app.core.telemetry import increment

logger = logging.getLogger(__name__)


def cleanup_expired_uploads() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        ids = db.scalars(
            select(Upload.id).where(
                Upload.object_deleted_at.is_(None),
                or_(
                    (Upload.status == UploadStatus.ACTIVE) & (Upload.expires_at <= now),
                    Upload.status == UploadStatus.EXPIRED,
                    Upload.status == UploadStatus.DOWNLOAD_LIMIT_REACHED,
                ),
            )
        ).all()
    result = {"processed": 0, "failed": 0}
    for upload_id in ids:
        with SessionLocal() as db:
            try:
                upload = db.scalar(
                    select(Upload).where(Upload.id == upload_id).with_for_update()
                )
                if upload is None or not should_cleanup(
                    upload, datetime.now(timezone.utc)
                ):
                    continue
                # S3 deletion succeeds when the key is already absent, which makes retries safe.
                delete_file_from_minio(upload.storage_key)
                upload.object_deleted_at = datetime.now(timezone.utc)
                transitioned = upload.status == UploadStatus.ACTIVE
                if transitioned:
                    upload.status = UploadStatus.EXPIRED
                db.commit()
                if transitioned:
                    increment("files_expired_total")
                    domain_event("FILE_EXPIRED", upload_id=str(upload_id))
                result["processed"] += 1
                domain_event("CLEANUP_SUCCESS", upload_id=str(upload_id))
            except Exception as error:
                db.rollback()
                result["failed"] += 1
                increment("cleanup_failures_total")
                domain_event(
                    "CLEANUP_FAILURE",
                    upload_id=str(upload_id),
                    error_type=type(error).__name__,
                )
    logger.info(
        "Cleanup complete processed=%s failed=%s", result["processed"], result["failed"]
    )
    return result


@celery_app.task(name="app.workers.tasks.cleanup_expired_uploads")
def cleanup_expired_uploads_task() -> dict[str, int]:
    return cleanup_expired_uploads()
