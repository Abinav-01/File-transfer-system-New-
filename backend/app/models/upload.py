import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, UUID
from sqlalchemy.sql import func
from app.core.database import Base


class UploadStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DOWNLOAD_LIMIT_REACHED = "DOWNLOAD_LIMIT_REACHED"
    DELETED = "DELETED"


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, unique=True, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)

    share_token = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)

    max_downloads = Column(Integer, nullable=True)
    download_count = Column(Integer, default=0, nullable=False)

    expires_at = Column(DateTime(timezone=True), index=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    object_deleted_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        Enum(UploadStatus), default=UploadStatus.ACTIVE, nullable=False, index=True
    )
    management_token_hash = Column(String, nullable=False)
