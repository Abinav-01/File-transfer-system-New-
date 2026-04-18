from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import pytest

from app.models.upload import UploadStatus
from app.services.rules import (
    calculate_expiration,
    effective_status,
    limit_reached,
    sanitize_filename,
    should_cleanup,
    validate_download_limit,
    validate_expiration,
    validate_file_size,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass
class FileState:
    status: UploadStatus = UploadStatus.ACTIVE
    expires_at: datetime = NOW + timedelta(hours=1)
    download_count: int = 0
    max_downloads: int | None = None
    deleted_at: datetime | None = None
    object_deleted_at: datetime | None = None


def test_expiration_is_bounded_and_calculated():
    assert validate_expiration(120, 60) == 60
    assert calculate_expiration(NOW, 60) == NOW + timedelta(hours=1)
    with pytest.raises(ValueError):
        validate_expiration(0, 60)
    with pytest.raises(ValueError):
        validate_expiration(-5, 60)


def test_filename_sanitization_removes_paths_and_unsafe_chars():
    assert sanitize_filename("../../private report.txt") == "private_report.txt"
    assert sanitize_filename("////") == "unnamed_file"


def test_upload_validation():
    validate_download_limit(None)
    validate_download_limit(5)
    with pytest.raises(ValueError):
        validate_download_limit(0)
    validate_file_size(1, 10)
    with pytest.raises(ValueError):
        validate_file_size(0, 10)
    with pytest.raises(OverflowError):
        validate_file_size(11, 10)


def test_effective_status_prioritizes_deletion_and_expiration():
    assert effective_status(FileState(), NOW) == UploadStatus.ACTIVE
    assert effective_status(FileState(expires_at=NOW), NOW) == UploadStatus.EXPIRED
    assert (
        effective_status(FileState(download_count=1, max_downloads=1), NOW)
        == UploadStatus.DOWNLOAD_LIMIT_REACHED
    )
    assert (
        effective_status(FileState(status=UploadStatus.DELETED, expires_at=NOW), NOW)
        == UploadStatus.DELETED
    )
    assert effective_status(FileState(deleted_at=NOW), NOW) == UploadStatus.DELETED


def test_download_limit_rule():
    assert not limit_reached(99, None)
    assert not limit_reached(0, 1)
    assert limit_reached(1, 1)
    assert limit_reached(2, 1)


def test_cleanup_decisions_ignore_already_removed_objects():
    assert not should_cleanup(FileState(), NOW)
    assert should_cleanup(FileState(expires_at=NOW), NOW)
    assert should_cleanup(FileState(status=UploadStatus.EXPIRED), NOW)
    assert should_cleanup(FileState(status=UploadStatus.DOWNLOAD_LIMIT_REACHED), NOW)
    assert not should_cleanup(FileState(status=UploadStatus.DELETED), NOW)
    assert not should_cleanup(
        FileState(status=UploadStatus.EXPIRED, object_deleted_at=NOW), NOW
    )
