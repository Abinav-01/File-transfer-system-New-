"""Fixtures only connect to the dedicated Compose test services."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app


pytest_plugins = ["tests.fixtures.services"]


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def upload_factory(client):
    def create(
        *,
        content=b"test content",
        filename="sample.txt",
        expires_in=60,
        max_downloads=None,
        password=None,
    ):
        data = {"expires_in": str(expires_in)}
        if max_downloads is not None:
            data["max_downloads"] = str(max_downloads)
        if password is not None:
            data["password"] = password
        response = client.post(
            "/api/uploads", data=data, files={"file": (filename, content, "text/plain")}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return create
