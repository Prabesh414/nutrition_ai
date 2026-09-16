"""Password hashing and JWT issuing/verification.

Uses the `bcrypt` package directly rather than `passlib`: passlib 1.7.4 is
incompatible with bcrypt >= 4.1 (it reads the removed `bcrypt.__about__`) and
outright fails on bcrypt 5.x.

Passwords are SHA-256 pre-hashed and base64-encoded before bcrypt so that
inputs longer than bcrypt's 72-byte limit are not silently truncated.
"""
import base64
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from backend.database import User, get_db

BCRYPT_ROUNDS = 12
_LEGACY_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

bearer_scheme = HTTPBearer(auto_error=False)


def _prepare(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify against a bcrypt hash, or a legacy unsalted SHA-256 hash."""
    if not stored_hash:
        return False

    if _LEGACY_SHA256_RE.match(stored_hash):
        # Constant-time compare so legacy accounts are not timing-distinguishable.
        return hmac.compare_digest(_legacy_sha256(password), stored_hash)

    try:
        return bcrypt.checkpw(_prepare(password), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when a stored hash uses the deprecated SHA-256 scheme."""
    return bool(_LEGACY_SHA256_RE.match(stored_hash or ""))


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expires_delta = timedelta(minutes=expires_minutes or JWT_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token, or reject the request."""
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_ERROR

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise _CREDENTIALS_ERROR

    email = payload.get("sub")
    if not email:
        raise _CREDENTIALS_ERROR

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise _CREDENTIALS_ERROR
    return user
