from jose import jwt

from app.config import settings
from tests.conftest import auth_headers, register_user


def test_healthcheck(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_returns_bearer_token_and_persists_user(client):
    response = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = jwt.decode(body["access_token"], settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "alice"


def test_register_duplicate_username_is_rejected(client):
    register_user(client, "alice")
    response = client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Пользователь уже существует"


def test_register_validation_errors(client):
    assert client.post("/api/auth/register", json={"username": "алиса", "password": "password123"}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "alice", "password": "short"}).status_code == 422


def test_login_success_and_wrong_password(client):
    register_user(client, "alice", "password123")

    response = client.post("/api/auth/login", data={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

    bad_response = client.post("/api/auth/login", data={"username": "alice", "password": "bad-password"})
    assert bad_response.status_code == 401
    assert bad_response.headers["www-authenticate"] == "Bearer"


def test_protected_tasks_require_token(client):
    response = client.get("/api/tasks/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_invalid_token_rejected(client):
    response = client.get("/api/tasks/", headers={"Authorization": "Bearer broken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Не удалось проверить учетные данные"


def test_authorization_cookie_is_converted_to_bearer_header(client):
    token = register_user(client, "alice")
    client.cookies.set("access_token", f"Bearer {token}")
    response = client.get("/api/tasks/")
    assert response.status_code == 200
    assert response.json() == []


def test_explicit_authorization_header_wins_over_cookie(client):
    valid_token = register_user(client, "alice")
    register_user(client, "bob")
    client.cookies.set("access_token", f"Bearer {valid_token}")
    response = client.get("/api/tasks/", headers={"Authorization": "Bearer broken"})
    assert response.status_code == 401


def test_auth_headers_helper(token):
    assert auth_headers(token) == {"Authorization": f"Bearer {token}"}
