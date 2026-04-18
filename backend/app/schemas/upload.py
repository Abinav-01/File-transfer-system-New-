from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.upload import UploadStatus
import uuid


class UploadBase(BaseModel):
    pass


class UploadCreateResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    size_bytes: int
    expires_at: datetime
    max_downloads: Optional[int]
    share_token: str
    management_token: str

    model_config = ConfigDict(from_attributes=True)


class FilePublicMetadata(BaseModel):
    filename: str
    size_bytes: int
    expires_at: datetime
    password_required: bool
    status: UploadStatus
    max_downloads: Optional[int]
    download_count: int

    model_config = ConfigDict(from_attributes=True)


class UploadManagementResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    size_bytes: int
    expires_at: datetime
    max_downloads: Optional[int]
    download_count: int
    status: UploadStatus
    share_token: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
