"""Authentication, password hashing and access control."""
import pytest

from backend.security import hash_password, needs_rehash, verify_password

API = "/api/v1"


def test_register_returns_token_and_user(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "first_name": "Asha",
            "middle_name": "Kumari",
            "last_name": "Gurung",
            "email": "asha@example.com",
            "password": "a-strong-test-password",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["middle_name"] == "Kumari"


def test_register_never_leaks_password(client):
    body = client.post(
        f"{API}/auth/register",
        json={"first_name": "A", "last_name": "B", "email": "leak@example.com",
              "password": "a-strong-test-password"},
    ).json()
    assert "password" not in str(body).lower().replace("a-strong-test-password", "")
    assert "password_hash" not in str(body)


def test_duplicate_registration_conflicts(client, register_user):
    _, payload = register_user("dupe@example.com")
    response = client.post(
        f"{API}/auth/register",
        json={"first_name": "A", "last_name": "B", "email": payload["email"],
              "password": "another-strong-password"},
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"first_name": "A", "last_name": "B", "email": "not-an-email", "password": "longenoughpw"},
        {"first_name": "A", "last_name": "B", "email": "x@example.com", "password": "short"},
        {"first_name": "", "last_name": "B", "email": "y@example.com", "password": "longenoughpw"},
        {"last_name": "B", "email": "z@example.com", "password": "longenoughpw"},
    ],
    ids=["bad-email", "short-password", "blank-first-name", "missing-first-name"],
)
def test_registration_validation_rejects_bad_input(client, payload):
    assert client.post(f"{API}/auth/register", json=payload).status_code == 422


def test_login_succeeds_and_wrong_password_fails(client, register_user):
    _, payload = register_user("login@example.com")

    ok = client.post(f"{API}/auth/login",
                     json={"email": payload["email"], "password": payload["password"]})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(f"{API}/auth/login",
                      json={"email": payload["email"], "password": "wrong-password"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Invalid credentials"


def test_login_does_not_reveal_whether_an_email_is_registered(client, register_user):
    _, payload = register_user("known@example.com")

    known = client.post(f"{API}/auth/login",
                        json={"email": payload["email"], "password": "wrong-password"})
    unknown = client.post(f"{API}/auth/login",
                          json={"email": "nobody@example.com", "password": "wrong-password"})

    assert known.status_code == unknown.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


@pytest.mark.parametrize("headers", [None, {"Authorization": "Bearer not-a-token"},
                                     {"Authorization": "Basic abc"}],
                         ids=["absent", "garbage-token", "wrong-scheme"])
def test_protected_endpoints_require_a_valid_token(client, headers):
    assert client.get(f"{API}/auth/me", headers=headers or {}).status_code == 401
    assert client.get(f"{API}/meals", headers=headers or {}).status_code == 401
    assert client.get(f"{API}/recommendations", headers=headers or {}).status_code == 401


def test_me_returns_the_token_holder(client, register_user):
    headers, payload = register_user("me@example.com")
    body = client.get(f"{API}/auth/me", headers=headers).json()
    assert body["email"] == payload["email"]


def test_removed_user_listing_endpoint_is_gone(client):
    """The old GET /users dumped every registered email address."""
    assert client.get(f"{API}/users").status_code == 404


# -- password hashing -------------------------------------------------------

def test_bcrypt_round_trip():
    stored = hash_password("correct horse battery staple")
    assert stored != "correct horse battery staple"
    assert verify_password("correct horse battery staple", stored)
    assert not verify_password("wrong", stored)


def test_hash_is_salted():
    assert hash_password("same-password") != hash_password("same-password")


def test_long_passwords_are_not_truncated_at_72_bytes():
    """bcrypt truncates at 72 bytes; pre-hashing must prevent a collision."""
    base = "x" * 72
    stored = hash_password(base + "AAAA")
    assert verify_password(base + "AAAA", stored)
    assert not verify_password(base + "BBBB", stored)


def test_legacy_sha256_hash_still_verifies_and_is_flagged():
    import hashlib

    legacy = hashlib.sha256(b"legacy-password").hexdigest()
    assert verify_password("legacy-password", legacy)
    assert not verify_password("nope", legacy)
    assert needs_rehash(legacy)
    assert not needs_rehash(hash_password("legacy-password"))


def test_legacy_hash_is_upgraded_on_login(client, db):
    """An existing SHA-256 account must keep working and migrate to bcrypt."""
    import hashlib

    from backend.database import User

    session = db
    user = User(
        first_name="Legacy", last_name="User", email="legacy@example.com",
        password_hash=hashlib.sha256(b"legacy-password").hexdigest(),
    )
    session.add(user)
    session.commit()

    response = client.post(f"{API}/auth/login",
                           json={"email": "legacy@example.com", "password": "legacy-password"})
    assert response.status_code == 200

    session.expire_all()
    refreshed = session.query(User).filter(User.email == "legacy@example.com").first()
    assert not needs_rehash(refreshed.password_hash)
    assert verify_password("legacy-password", refreshed.password_hash)
