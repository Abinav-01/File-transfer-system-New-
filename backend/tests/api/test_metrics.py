import uuid


def counter(text: str, name: str) -> int:
    return int(
        next(
            line.split()[1] for line in text.splitlines() if line.startswith(name + " ")
        )
    )


def test_metrics_increment_and_request_id(client, upload_factory):
    before = counter(client.get("/metrics").text, "dropvault_uploads_total")
    data = upload_factory()
    response = client.get(f"/api/uploads/{data['share_token']}")
    assert response.status_code == 200
    uuid.UUID(response.headers["x-request-id"])
    after = counter(client.get("/metrics").text, "dropvault_uploads_total")
    assert after == before + 1
