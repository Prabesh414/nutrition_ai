"""Shared test fixtures.

Every test runs against a throwaway SQLite database created per test session.
The previous suite ran against the live Supabase instance -- it created and
deleted real users, and `seed_food_items` could drop and rebuild the live
`food_items` table.
"""
import os
import tempfile
from pathlib import Path

import pytest

# Must be set before backend.config is imported anywhere.
_TMP_DB = Path(tempfile.gettempdir()) / "nutrition_ai_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-only-secret-not-used-outside-the-suite"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from backend.database import Base, SessionLocal, engine  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Create a clean schema for the session and remove the file afterwards."""
    if _TMP_DB.exists():
        _TMP_DB.unlink()
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if _TMP_DB.exists():
        try:
            _TMP_DB.unlink()
        except PermissionError:
            pass  # Windows may still hold the handle; harmless for a temp file.


@pytest.fixture(autouse=True)
def _clean_user_tables():
    """Truncate user-owned tables between tests; the food catalogue persists."""
    from backend.database import MealLog, Profile, User

    yield
    db = SessionLocal()
    try:
        db.query(MealLog).delete()
        db.query(Profile).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def client():
    """TestClient with lifespan run, so the food catalogue is seeded once."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def register_user(client):
    """Register a user and return `(headers, payload)` for authenticated calls."""
    counter = {"n": 0}

    def _register(email: str | None = None, password: str = "a-strong-test-password"):
        counter["n"] += 1
        address = email or f"user{counter['n']}@example.com"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Test",
                "last_name": f"User{counter['n']}",
                "email": address,
                "password": password,
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, {
            "email": address,
            "password": password,
            "id": body["user"]["id"],
        }

    return _register


@pytest.fixture
def authed(register_user):
    """Headers for a single registered user with a completed profile."""
    headers, payload = register_user()
    return headers, payload
