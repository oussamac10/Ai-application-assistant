from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.models import AuthSession, User
from app.auth.security import hash_auth_token, hash_password, normalize_email
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()


def _register(
    email: str = "user@example.com", password: str = "correct-horse-battery"
) -> object:
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "passwordConfirmation": password,
        },
    )


def test_register_success_sets_cookies_and_hashes_password() -> None:
    response = _register()
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "password" not in data
    assert "passwordHash" not in data

    assert "auth_session" in response.cookies
    assert "csrf_token" in response.cookies

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter_by(normalized_email=normalize_email("user@example.com"))
            .first()
        )
        assert user is not None
        assert user.password_hash != "correct-horse-battery"
        assert user.password_hash.startswith("$argon2")
    finally:
        db.close()


def test_register_rejects_mismatched_confirmation() -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "correct-horse-battery",
            "passwordConfirmation": "different-password",
        },
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "password_mismatch"


def test_register_rejects_weak_password() -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "short",
            "passwordConfirmation": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "weak_password"


def test_register_duplicate_email_is_generic_conflict() -> None:
    _register()
    response = _register()
    assert response.status_code == 409
    # Must not reveal a distinguishable "already exists" message shape.
    assert response.json() == {"detail": "Unable to complete registration."}


def test_register_duplicate_email_case_insensitive() -> None:
    _register(email="User@Example.com")
    response = _register(email="user@example.com")
    assert response.status_code == 409


def test_login_success_and_wrong_password_generic() -> None:
    _register()

    ok = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-horse-battery"},
    )
    assert ok.status_code == 200
    assert "auth_session" in ok.cookies

    wrong = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Authentication required."

    unknown = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever12345"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_me_requires_valid_session() -> None:
    anon = client.get("/api/auth/me")
    assert anon.status_code == 401

    _register()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_logout_requires_csrf_and_revokes_session() -> None:
    _register()

    # Missing CSRF header is rejected.
    no_csrf = client.post("/api/auth/logout")
    assert no_csrf.status_code == 401

    csrf_token = client.cookies.get("csrf_token")
    assert csrf_token
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 204

    # The session cookie is now invalid server-side even if resent.
    me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_refresh_rotates_token() -> None:
    _register()
    old_token = client.cookies.get("auth_session")
    csrf_token = client.cookies.get("csrf_token")

    refreshed = client.post("/api/auth/refresh", headers={"X-CSRF-Token": csrf_token})
    assert refreshed.status_code == 200
    new_token = client.cookies.get("auth_session")
    assert new_token != old_token

    db = SessionLocal()
    try:
        old_hash = hash_auth_token(old_token)
        old_session = db.query(AuthSession).filter_by(token_hash=old_hash).first()
        assert old_session is not None
        assert old_session.revoked_at is not None
    finally:
        db.close()


def test_password_hash_never_reversible_and_verifies() -> None:
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    from app.auth.security import verify_password

    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)
