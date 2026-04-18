import logging
from datetime import datetime, timezone
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    Form,
    HTTPException,
    Header,
    Request,
    status,
)
from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.core.database import get_db
from app.schemas.upload import (
    UploadCreateResponse,
    FilePublicMetadata,
    UploadManagementResponse,
)
from app.services.upload_service import UploadService
from app.services.rules import effective_status
from app.repositories.upload_repository import UploadRepository
from app.services.security_service import verify_password
from app.models.upload import UploadStatus
from app.core.config import settings
from app.core.rate_limit import check_limit, client_identity
from app.core.logging import domain_event
from app.core.telemetry import increment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED
)
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    expires_in: int = Form(...),
    password: Optional[str] = Form(None),
    max_downloads: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a file and create a temporary shareable link.
    """
    check_limit(
        "upload",
        client_identity(request),
        settings.UPLOAD_RATE_LIMIT,
        settings.UPLOAD_RATE_WINDOW_SECONDS,
    )
    upload_service = UploadService(db)
    return upload_service.process_upload(
        file=file,
        expires_in_minutes=expires_in,
        password=password,
        max_downloads=max_downloads,
    )


@router.get("/{share_token}", response_model=FilePublicMetadata)
def get_public_file_metadata(share_token: str, db: Session = Depends(get_db)):
    """
    Retrieve public metadata for a shared file.
    """
    repo = UploadRepository(db)
    upload = repo.get_by_share_token(share_token)

    if not upload:
        raise HTTPException(status_code=404, detail="File not found")

    return FilePublicMetadata(
        filename=upload.original_filename,
        size_bytes=upload.size_bytes,
        expires_at=upload.expires_at,
        password_required=upload.password_hash is not None,
        status=effective_status(upload, datetime.now(timezone.utc)),
        max_downloads=upload.max_downloads,
        download_count=upload.download_count,
    )


@router.get("/manage/{upload_id}", response_model=UploadManagementResponse)
def get_management_info(
    upload_id: uuid.UUID,
    x_management_token: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Retrieve management details for an upload using the management token.
    """
    repo = UploadRepository(db)
    upload = repo.get_by_id(upload_id)

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    if not verify_password(x_management_token, upload.management_token_hash):
        raise HTTPException(status_code=401, detail="Invalid management token")

    return UploadManagementResponse(
        id=upload.id,
        original_filename=upload.original_filename,
        size_bytes=upload.size_bytes,
        expires_at=upload.expires_at,
        max_downloads=upload.max_downloads,
        download_count=upload.download_count,
        status=upload.status,
        share_token=upload.share_token,
        created_at=upload.created_at,
    )


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: uuid.UUID,
    x_management_token: str = Header(...),
    db: Session = Depends(get_db),
):
    """Delete an upload using its private management token."""
    from sqlalchemy import select
    from datetime import datetime, timezone
    from app.models.upload import Upload
    from app.services.minio_service import delete_file_from_minio

    try:
        upload = db.execute(
            select(Upload).where(Upload.id == upload_id).with_for_update()
        ).scalar_one_or_none()
        if upload is None:
            raise HTTPException(status_code=404, detail="Upload not found")
        if not verify_password(x_management_token, upload.management_token_hash):
            raise HTTPException(status_code=401, detail="Invalid management token")
        if upload.status == UploadStatus.DELETED:
            return None
        try:
            delete_file_from_minio(upload.storage_key)
        except Exception as error:
            logger.error(
                "DELETE_STORAGE_FAILURE",
                extra={"upload_id": str(upload.id), "error_type": type(error).__name__},
            )
            raise HTTPException(status_code=503, detail="Storage unavailable") from None
        upload.status = UploadStatus.DELETED
        upload.deleted_at = datetime.now(timezone.utc)
        upload.object_deleted_at = upload.deleted_at
        db.commit()
        increment("files_deleted_total")
        domain_event("FILE_DELETED", upload_id=str(upload.id))
        return None
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
