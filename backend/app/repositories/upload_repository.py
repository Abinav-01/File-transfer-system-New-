from sqlalchemy.orm import Session
from app.models.upload import Upload
import uuid


class UploadRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, upload_data: Upload) -> Upload:
        self.db.add(upload_data)
        self.db.commit()
        self.db.refresh(upload_data)
        return upload_data

    def get_by_share_token(self, share_token: str) -> Upload | None:
        return self.db.query(Upload).filter(Upload.share_token == share_token).first()

    def get_by_id(self, upload_id: uuid.UUID) -> Upload | None:
        return self.db.query(Upload).filter(Upload.id == upload_id).first()

    def update(self, upload: Upload) -> Upload:
        self.db.commit()
        self.db.refresh(upload)
        return upload
