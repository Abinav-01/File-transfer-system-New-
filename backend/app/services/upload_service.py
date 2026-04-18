import uuid
import logging
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.upload import Upload, UploadStatus
from app.repositories.upload_repository import UploadRepository
from app.schemas.upload import UploadCreateResponse
from app.services.security_service import generate_secure_token, get_password_hash
from app.services.minio_service import upload_file_to_minio, delete_file_from_minio
from app.core.config import settings
from app.core.logging import domain_event
from app.core.telemetry import increment
from app.services.rules import (
    sanitize_filename,
    validate_expiration,
    calculate_expiration,
    validate_file_size,
    validate_download_limit,
)

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, db: Session):
        self.repository = UploadRepository(db)

    def process_upload(
        self,
        file: UploadFile,
        expires_in_minutes: int,
        password: str | None = None,
        max_downloads: int | None = None,
    ) -> UploadCreateResponse:
        # Validate file size (can't easily do it with UploadFile before reading, but we can check if it's empty)
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename missing")

        # Secure filename and validate upload options.
        safe_filename = sanitize_filename(file.filename)
        try:
            validate_download_limit(max_downloads)
            expires_in_minutes = validate_expiration(
                expires_in_minutes, settings.MAX_EXPIRATION_MINUTES
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

        # Generate tokens and keys
        upload_id = uuid.uuid4()
        storage_key = str(uuid.uuid4())
        share_token = generate_secure_token(16)
        management_token = generate_secure_token(32)
        management_token_hash = get_password_hash(management_token)

        # Hash password if provided
        hashed_password = get_password_hash(password) if password else None

        # Expiration logic
        expires_at = calculate_expiration(
            datetime.now(timezone.utc), expires_in_minutes
        )

        # We need size. We'll seek to end, tell, and seek back
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)

        try:
            validate_file_size(size_bytes, settings.MAX_UPLOAD_SIZE_BYTES)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        except OverflowError as error:
            raise HTTPException(status_code=413, detail=str(error)) from None

        # Create DB record (in memory first)
        new_upload = Upload(
            id=upload_id,
            original_filename=safe_filename,
            storage_key=storage_key,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            share_token=share_token,
            password_hash=hashed_password,
            max_downloads=max_downloads,
            expires_at=expires_at,
            management_token_hash=management_token_hash,
            status=UploadStatus.ACTIVE,
        )

        try:
            # Upload to MinIO first
            upload_file_to_minio(file.file, storage_key, new_upload.content_type)
        except Exception as error:
            logger.error(
                "UPLOAD_STORAGE_FAILURE",
                extra={"upload_id": str(upload_id), "error_type": type(error).__name__},
            )
            raise HTTPException(
                status_code=500, detail="Failed to upload file to storage"
            ) from None

        try:
            # Save to DB
            self.repository.create(new_upload)
        except Exception as error:
            logger.error(
                "UPLOAD_METADATA_FAILURE",
                extra={"upload_id": str(upload_id), "error_type": type(error).__name__},
            )
            try:
                delete_file_from_minio(storage_key)
            except Exception as cleanup_error:
                logger.error(
                    "UPLOAD_ROLLBACK_FAILURE",
                    extra={
                        "upload_id": str(upload_id),
                        "error_type": type(cleanup_error).__name__,
                    },
                )
            raise HTTPException(
                status_code=500, detail="Failed to save upload metadata"
            ) from None

        increment("uploads_total")
        domain_event("UPLOAD_CREATED", upload_id=str(new_upload.id))
        return UploadCreateResponse(
            id=new_upload.id,
            original_filename=new_upload.original_filename,
            size_bytes=new_upload.size_bytes,
            expires_at=new_upload.expires_at,
            max_downloads=new_upload.max_downloads,
            share_token=new_upload.share_token,
            management_token=management_token,
        )
