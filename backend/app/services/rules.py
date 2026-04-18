"""Pure upload lifecycle rules shared by HTTP handlers and cleanup."""

from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from app.models.upload import UploadStatus


def sanitize_filename(filename: str) -> str:
    return secure_filename(filename) or "unnamed_file"


def validate_expiration(minutes: int, maximum_minutes: int) -> int:
    if minutes <= 0:
        raise ValueError("expires_in must be positive")
    return min(minutes, maximum_minutes)


def calculate_expiration(now: datetime, minutes: int) -> datetime:
    return now + timedelta(minutes=minutes)


def validate_download_limit(limit: int | None) -> None:
    if limit is not None and limit <= 0:
        raise ValueError("max_downloads must be a positive integer or null")


def validate_file_size(size: int, maximum_size: int) -> None:
    if size <= 0:
        raise ValueError("Empty file uploaded")
    if size > maximum_size:
        raise OverflowError("File too large")


def limit_reached(download_count: int, max_downloads: int | None) -> bool:
    return max_downloads is not None and download_count >= max_downloads


def effective_status(upload, now: datetime) -> UploadStatus:
    if upload.status == UploadStatus.DELETED or upload.deleted_at is not None:
        return UploadStatus.DELETED
    if upload.expires_at <= now or upload.status == UploadStatus.EXPIRED:
        return UploadStatus.EXPIRED
    if upload.status == UploadStatus.DOWNLOAD_LIMIT_REACHED or limit_reached(
        upload.download_count, upload.max_downloads
    ):
        return UploadStatus.DOWNLOAD_LIMIT_REACHED
    return upload.status


def should_cleanup(upload, now: datetime) -> bool:
    if upload.object_deleted_at is not None or upload.status == UploadStatus.DELETED:
        return False
    return upload.status in (
        UploadStatus.EXPIRED,
        UploadStatus.DOWNLOAD_LIMIT_REACHED,
    ) or (upload.status == UploadStatus.ACTIVE and upload.expires_at <= now)
