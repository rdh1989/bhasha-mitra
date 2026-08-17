from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.authentication import AuthenticationMiddleware, SESSION_COOKIE
from app.security import (
    INTERNAL_API_HEADER,
    INTERNAL_API_TOKEN,
    SQLiteAuthRepository,
)


def test_default_admin_and_database_session(tmp_path: Path):
    repository = SQLiteAuthRepository(tmp_path)

    admin = repository.authenticate("admin", "admin")

    assert admin is not None
    assert admin.role == "admin"
    assert repository.authenticate("admin", "wrong") is None
    assert repository.get_session_user(
        repository.create_session(admin.id)
    ) == admin


def test_role_authorization(tmp_path: Path):
    repository = SQLiteAuthRepository(tmp_path)
    app = FastAPI()
    app.add_middleware(AuthenticationMiddleware, repository=repository)
    app.add_api_route("/dashboard", lambda: {"ok": True})
    app.add_api_route("/users/1/role", lambda: {"ok": True}, methods=["POST"])
    app.add_api_route(
        "/api/v1/jobs/1/start",
        lambda: {"ok": True},
        methods=["POST"],
    )
    app.add_api_route(
        "/api/ai/translate",
        lambda: {"ok": True},
        methods=["POST"],
    )
    client = TestClient(app)

    assert client.get("/dashboard", follow_redirects=False).status_code == 303
    assert client.post("/api/ai/translate").status_code == 401
    assert client.post(
        "/api/ai/translate",
        headers={INTERNAL_API_HEADER: INTERNAL_API_TOKEN},
    ).status_code == 200

    repository.create_user("operator1", "password1", "operator")
    operator = repository.authenticate("operator1", "password1")
    assert operator is not None
    client.cookies.set(SESSION_COOKIE, repository.create_session(operator.id))
    assert client.post("/api/v1/jobs/1/start").status_code == 200
    assert client.post("/api/ai/translate").status_code == 403
    assert client.post("/users/1/role", follow_redirects=False).status_code == 303

    repository.create_user("reader1", "password1", "user")
    reader = repository.authenticate("reader1", "password1")
    assert reader is not None
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, repository.create_session(reader.id))
    assert client.post("/api/v1/jobs/1/start").status_code == 403