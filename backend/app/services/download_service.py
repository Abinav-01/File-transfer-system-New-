"""Authorize and reserve downloads with a PostgreSQL row lock."""

from datetime import datetime, timezone
from urllib.parse import quote
from werkzeug.utils import secure_filename

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.upload import Upload, UploadStatus
from app.services.minio_service import get_file_from_minio
from app.services.security_service import verify_password
from app.services.rules import limit_reached
from app.core.rate_limit import (
    check_password_lock,
    record_password_failure,
    clear_password_failures,
)
from app.core.logging import domain_event
from app.core.telemetry import increment


def download_file(
    db: Session, share_token: str, password: str | None, client_ip: str
) -> StreamingResponse:
    # The lock remains held through object retrieval and the count update. PostgreSQL
    # serializes competing downloads and deletion of the same upload row.
    upload = None
    try:
        upload = db.execute(
            select(Upload).where(Upload.share_token == share_token).with_for_update()
        ).scalar_one_or_none()
        if upload is None:
            raise HTTPException(404, detail="Invalid link")
        if upload.status == UploadStatus.DELETED or upload.deleted_at is not None:
            raise HTTPException(410, detail="File deleted")
        if upload.expires_at <= datetime.now(timezone.utc):
            if upload.status != UploadStatus.EXPIRED:
                upload.status = UploadStatus.EXPIRED
                db.commit()
                increment("files_expired_total")
                domain_event("FILE_EXPIRED", upload_id=str(upload.id))
            raise HTTPException(410, detail="File expired")
        if upload.status == UploadStatus.EXPIRED:
            raise HTTPException(410, detail="File expired")
        if upload.status == UploadStatus.DOWNLOAD_LIMIT_REACHED or (
            limit_reached(upload.download_count, upload.max_downloads)
        ):
            if upload.status != UploadStatus.DOWNLOAD_LIMIT_REACHED:
                upload.status = UploadStatus.DOWNLOAD_LIMIT_REACHED
                db.commit()
            raise HTTPException(410, detail="Download limit reached")
        if upload.status != UploadStatus.ACTIVE:
            raise HTTPException(410, detail="File unavailable")
        if upload.password_hash:
            password_identity = f"{client_ip}:{share_token}"
            check_password_lock(password_identity)
            if password is None or not verify_password(password, upload.password_hash):
                record_password_failure(password_identity)
                raise HTTPException(401, detail="Incorrect password")

        if upload.password_hash:
            clear_password_failures(password_identity)

        try:
            object_response = get_file_from_minio(upload.storage_key)
        except Exception:
            raise HTTPException(503, detail="Storage unavailable") from None

        upload.download_count += 1
        if limit_reached(upload.download_count, upload.max_downloads):
            upload.status = UploadStatus.DOWNLOAD_LIMIT_REACHED
        try:
            db.commit()
        except Exception:
            object_response["Body"].close()
            raise

        increment("downloads_success_total")
        domain_event("DOWNLOAD_SUCCESS", upload_id=str(upload.id))

        # Use only the sanitized basename in headers; the RFC 5987 form supports UTF-8.
        filename = secure_filename(upload.original_filename) or "download"
        disposition = (
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
        )
        body = object_response["Body"]

        def chunks():
            try:
                for chunk in body.iter_chunks(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                body.close()

        return StreamingResponse(
            chunks(),
            media_type=upload.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": disposition,
                "Content-Length": str(upload.size_bytes),
                "X-Content-Type-Options": "nosniff",
            },
        )
    except HTTPException as error:
        db.rollback()
        increment("downloads_rejected_total")
        domain_event(
            "DOWNLOAD_REJECTED",
            upload_id=str(upload.id) if upload else None,
            reason=str(error.detail),
        )
        raise
    except Exception as error:
        db.rollback()
        increment("downloads_rejected_total")
        domain_event(
            "DOWNLOAD_REJECTED",
            upload_id=str(upload.id) if upload else None,
            reason="internal_error",
            error_type=type(error).__name__,
        )
        raise
