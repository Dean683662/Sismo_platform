from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.core.security import hash_password
from backend.database.models import Role, User
from backend.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    with test_session.begin() as db:
        administrator = Role(name="administrator", description="Administración")
        analyst_role = Role(name="analyst", description="Análisis")
        read_only_role = Role(name="read_only", description="Consulta")
        db.add_all([administrator, analyst_role, read_only_role])
        db.flush()
        db.add_all(
            [
                User(
                    full_name="Admin de prueba",
                    email="admin@example.com",
                    password_hash=hash_password("UnaClaveSegura-123"),
                    roles=[administrator],
                ),
                User(
                    full_name="Usuario de lectura",
                    email="reader@example.com",
                    password_hash=hash_password("OtraClaveSegura-123"),
                    roles=[read_only_role],
                ),
            ]
        )

    def override_get_db() -> Generator:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_session_is_required_and_login_returns_current_user(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "UnaClaveSegura-123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["roles"] == ["administrator"]
    assert "sismo_session" in response.cookies
    assert "sismo_csrf" in response.cookies
    assert client.get("/api/v1/auth/me").json()["user"]["email"] == "admin@example.com"


def test_role_permissions_and_csrf_protect_user_management(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "reader@example.com", "password": "OtraClaveSegura-123"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/admin/users").status_code == 403

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": client.cookies.get("sismo_csrf", "")})
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "UnaClaveSegura-123"},
    )
    body = {
        "full_name": "Analista nueva",
        "email": "analyst@example.com",
        "password": "ClaveNueva-Segura-123",
        "roles": ["analyst"],
    }

    assert client.post("/api/v1/admin/users", json=body).status_code == 403
    csrf_token = client.cookies.get("sismo_csrf", "")
    created = client.post("/api/v1/admin/users", json=body, headers={"X-CSRF-Token": csrf_token})

    assert created.status_code == 201
    assert created.json()["email"] == "analyst@example.com"
    audit = client.get("/api/v1/admin/audit-logs").json()
    assert any(entry["action"] == "admin.user_created" for entry in audit)


def test_last_active_administrator_cannot_be_disabled(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "UnaClaveSegura-123"},
    )
    user_id = client.get("/api/v1/auth/me").json()["user"]["id"]
    csrf_token = client.cookies.get("sismo_csrf", "")

    response = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 409


def test_logout_revokes_the_signed_session(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "UnaClaveSegura-123"},
    )
    old_session = client.cookies.get("sismo_session")
    csrf_token = client.cookies.get("sismo_csrf", "")

    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert response.status_code == 204

    client.cookies.set("sismo_session", old_session)
    assert client.get("/api/v1/auth/me").status_code == 401