from datetime import datetime, timedelta, timezone
import uuid
from app.models.upload import Upload, UploadStatus


def download(client, token, password=None):
    return client.post(f"/api/files/{token}/download", json={"password": password})


def test_successful_download(client, upload_factory, db):
    data = upload_factory(content=b"file body")
    response = download(client, data["share_token"])
    assert response.status_code == 200
    assert response.content == b"file body"
    assert "sample.txt" in response.headers["content-disposition"]
    assert response.headers["content-type"].startswith("text/plain")
    assert db.get(Upload, uuid.UUID(data["id"])).download_count == 1


def test_password_protected_download(client, upload_factory):
    data = upload_factory(password="secret")
    assert download(client, data["share_token"]).status_code == 401
    assert download(client, data["share_token"], "secret").status_code == 200


def test_incorrect_password_does_not_consume_download(client, upload_factory, db):
    data = upload_factory(password="secret", max_downloads=1)
    response = download(client, data["share_token"], "wrong")
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect password"
    assert db.get(Upload, uuid.UUID(data["id"])).download_count == 0


def test_expired_download_transitions_status(client, upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    response = download(client, data["share_token"])
    assert response.status_code == 410
    db.refresh(row)
    assert row.status == UploadStatus.EXPIRED


def test_deleted_download(client, upload_factory, db):
    data = upload_factory()
    row = db.get(Upload, uuid.UUID(data["id"]))
    row.status = UploadStatus.DELETED
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    response = download(client, data["share_token"])
    assert response.status_code == 410
    assert response.json()["detail"] == "File deleted"


def test_limit_reached_and_repeated_download(client, upload_factory, db):
    data = upload_factory(max_downloads=1)
    assert download(client, data["share_token"]).status_code == 200
    for _ in range(2):
        response = download(client, data["share_token"])
        assert response.status_code == 410
        assert response.json()["detail"] == "Download limit reached"
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row.download_count == 1
    assert row.status == UploadStatus.DOWNLOAD_LIMIT_REACHED


def test_invalid_download_token(client):
    response = download(client, "invalid-token")
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid link"


def test_repeated_unlimited_downloads_succeed(client, upload_factory, db):
    data = upload_factory(max_downloads=None)
    assert download(client, data["share_token"]).status_code == 200
    assert download(client, data["share_token"]).status_code == 200
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row.download_count == 2
    assert row.status == UploadStatus.ACTIVE
