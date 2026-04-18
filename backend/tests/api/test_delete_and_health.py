import uuid
from app.models.upload import Upload, UploadStatus


def test_delete_with_valid_management_token(client, upload_factory, db):
    data = upload_factory()
    response = client.delete(
        f"/api/uploads/{data['id']}",
        headers={"X-Management-Token": data["management_token"]},
    )
    assert response.status_code == 204
    row = db.get(Upload, uuid.UUID(data["id"]))
    assert row.status == UploadStatus.DELETED
    assert row.deleted_at is not None and row.object_deleted_at is not None


def test_delete_with_invalid_management_token(client, upload_factory, db):
    data = upload_factory()
    response = client.delete(
        f"/api/uploads/{data['id']}", headers={"X-Management-Token": "wrong"}
    )
    assert response.status_code == 401
    assert db.get(Upload, uuid.UUID(data["id"])).status == UploadStatus.ACTIVE


def test_repeated_deletion_is_idempotent(client, upload_factory):
    data = upload_factory()
    headers = {"X-Management-Token": data["management_token"]}
    assert (
        client.delete(f"/api/uploads/{data['id']}", headers=headers).status_code == 204
    )
    assert (
        client.delete(f"/api/uploads/{data['id']}", headers=headers).status_code == 204
    )
    assert (
        client.post(f"/api/files/{data['share_token']}/download", json={}).status_code
        == 410
    )


def test_health_reports_dependencies(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "postgres": "up",
        "redis": "up",
        "minio": "up",
    }
    uuid.UUID(response.headers["x-request-id"])
