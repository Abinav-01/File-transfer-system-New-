from datetime import datetime, timedelta, timezone
import uuid
from app.models.upload import Upload, UploadStatus


def test_valid_active_metadata(client, upload_factory):
    data = upload_factory(password="secret", max_downloads=5)
    response = client.get(f"/api/uploads/{data['share_token']}")
    assert response.status_code == 200
    metadata = response.json()
    assert metadata["filename"] == "sample.txt"
    assert metadata["status"] == "ACTIVE"
    assert metadata["password_required"] is True
    assert metadata["download_count"] == 0
    assert "password_hash" not in response.text
    assert "management_token" not in response.text


def test_invalid_metadata_token(client):
    assert client.get("/api/uploads/invalid-token").status_code == 404


def test_expired_metadata_even_before_cleanup(client, upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    response = client.get(f"/api/uploads/{data['share_token']}")
    assert response.status_code == 200
    assert response.json()["status"] == "EXPIRED"


def test_deleted_metadata(client, upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    row.status = UploadStatus.DELETED
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    response = client.get(f"/api/uploads/{data['share_token']}")
    assert response.status_code == 200
    assert response.json()["status"] == "DELETED"
