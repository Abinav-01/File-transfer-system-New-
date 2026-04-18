import uuid
from app.models.upload import Upload
from app.services.security_service import verify_password


def test_upload_success_and_metadata_persisted(client, db):
    response = client.post(
        "/api/uploads",
        data={"expires_in": "60", "max_downloads": "5"},
        files={"file": ("../my report.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "my_report.txt"
    assert data["size_bytes"] == 5
    assert data["max_downloads"] == 5
    assert "x-request-id" in response.headers
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row is not None and row.storage_key and row.status.value == "ACTIVE"
    assert verify_password(data["management_token"], row.management_token_hash)
    assert row.management_token_hash not in response.text


def test_upload_missing_file(client):
    response = client.post("/api/uploads", data={"expires_in": "60"})
    assert response.status_code == 422


def test_upload_empty_file(client):
    response = client.post(
        "/api/uploads",
        data={"expires_in": "60"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file uploaded"


def test_upload_oversized_file(client, monkeypatch):
    from app.services import upload_service

    monkeypatch.setattr(upload_service.settings, "MAX_UPLOAD_SIZE_BYTES", 4)
    response = client.post(
        "/api/uploads",
        data={"expires_in": "60"},
        files={"file": ("big.txt", b"12345", "text/plain")},
    )
    assert response.status_code == 413


def test_upload_invalid_expiration(client):
    for value in ("0", "-1"):
        response = client.post(
            "/api/uploads",
            data={"expires_in": value},
            files={"file": ("sample.txt", b"x", "text/plain")},
        )
        assert response.status_code == 400
    response = client.post(
        "/api/uploads",
        data={"expires_in": "not-a-number"},
        files={"file": ("sample.txt", b"x", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_invalid_download_limit(client):
    for value in ("0", "-2"):
        response = client.post(
            "/api/uploads",
            data={"expires_in": "60", "max_downloads": value},
            files={"file": ("sample.txt", b"x", "text/plain")},
        )
        assert response.status_code == 400


def test_password_protected_upload(upload_factory, db):
    data = upload_factory(password="private-passphrase")
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row.password_hash != "private-passphrase"
    assert verify_password("private-passphrase", row.password_hash)
    assert "password_hash" not in data
    assert "private-passphrase" not in str(data)


def test_upload_rate_limit_uses_redis(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_RATE_LIMIT", 1)
    first = client.post(
        "/api/uploads",
        data={"expires_in": "60"},
        files={"file": ("a.txt", b"a", "text/plain")},
    )
    second = client.post(
        "/api/uploads",
        data={"expires_in": "60"},
        files={"file": ("b.txt", b"b", "text/plain")},
    )
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["retry-after"] == str(settings.UPLOAD_RATE_WINDOW_SECONDS)
