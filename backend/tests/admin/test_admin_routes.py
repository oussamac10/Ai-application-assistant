from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.execute(text("TRUNCATE TABLE ai_usage_events CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_admin_overview_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 401


def test_admin_overview_forbidden_for_regular_user(
    client: TestClient, db_session: Session
) -> None:
    reg_user = client.post(
        "/api/auth/register",
        json={
            "email": "regular@agency.com",
            "password": "Password123!",
            "passwordConfirmation": "Password123!",
        },
    )
    assert reg_user.status_code == 201

    resp = client.get("/api/admin/overview")
    assert resp.status_code == 403


def test_admin_overview_success_for_platform_admin(
    client: TestClient, db_session: Session
) -> None:
    settings.ADMIN_EMAILS = "founder@platform.com"
    reg_admin = client.post(
        "/api/auth/register",
        json={
            "email": "founder@platform.com",
            "password": "Password123!",
            "passwordConfirmation": "Password123!",
        },
    )
    assert reg_admin.status_code == 201

    resp = client.get("/api/admin/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "firewall" in data
    assert "organizations" in data
    assert data["kpis"]["total_users"] >= 1
    assert data["firewall"]["max_session_cost_eur"] == 0.25
