from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.download_service import download_file
from app.core.config import settings
from app.core.rate_limit import check_limit, client_identity
from app.core.telemetry import increment

router = APIRouter()


class DownloadRequest(BaseModel):
    password: str | None = None


@router.post("/{share_token}/download")
def download(
    share_token: str,
    http_request: Request,
    request: DownloadRequest | None = None,
    db: Session = Depends(get_db),
):
    identity = client_identity(http_request)
    try:
        check_limit(
            "download",
            identity,
            settings.DOWNLOAD_RATE_LIMIT,
            settings.DOWNLOAD_RATE_WINDOW_SECONDS,
        )
    except HTTPException as error:
        if error.status_code == 429:
            increment("downloads_rejected_total")
        raise
    return download_file(
        db, share_token, request.password if request else None, identity
    )
