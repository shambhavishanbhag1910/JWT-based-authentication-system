import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test_only_" + "x" * 60)

import database  # noqa: E402
from main import JWT_ALGORITHM, JWT_SECRET, app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Each test gets a fresh SQLite file; lifespan creates its tables.
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "users.db")
    with TestClient(app) as api:
        yield api


def register(client):
    return client.post(
        "/register",
        json={"username": "alex", "password": "CorrectHorseBattery99!", "full_name": "Alex"},
    )


def login(client, password="CorrectHorseBattery99!"):
    return client.post("/login", data={"username": "alex", "password": password})


def test_register_login_profile(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {"username": "alex", "full_name": "Alex"}
    saved = database.get_user("alex")
    assert saved is not None
    assert saved["password_hash"] != "CorrectHorseBattery99!"
    assert saved["password_hash"].startswith("$argon2id$")
    result = login(client)
    assert result.status_code == 200
    token = result.json()["access_token"]
    profile = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["username"] == "alex"


def test_duplicate_username(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_invalid_password(client):
    register(client)
    assert login(client, "incorrect_pass").status_code == 401


def test_unknown_user(client):
    result = client.post("/login", data={"username": "missing", "password": "some-pass"})
    assert result.status_code == 401


def test_route_requires_token(client):
    assert client.get("/me").status_code == 401


def test_expired_token_rejected(client):
    register(client)
    token = jwt.encode(
        {"sub": "alex", "exp": datetime.now(timezone.utc) - timedelta(seconds=3)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_wrong_signature_rejected(client):
    register(client)
    token = jwt.encode(
        {"sub": "alex", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        "a-completely-different-secret-key-over-32-chars",
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_short_password_rejected(client):
    assert client.post("/register", json={"username": "alex", "password": "abc"}).status_code == 422
