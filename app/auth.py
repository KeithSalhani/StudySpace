import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, status

from app.config import SESSION_COOKIE_NAME, SESSION_TTL_DAYS
from app.db.repository import DatabaseRepository

PBKDF2_ITERATIONS = 310000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")


@dataclass
class AuthenticatedUser:
    username: str


def validate_username(username: str) -> str:
    normalized = username.strip()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must be 3-32 characters using letters, numbers, or underscores")
    return normalized


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 256:
        raise ValueError("Password is too long")
    return password


def hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return derived.hex()


def create_password_record(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return hash_password(password, salt), salt


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


def _build_session_value(session_id: str, session_secret: str) -> str:
    return f"{session_id}.{session_secret}"


def _parse_session_value(session_value: Optional[str]) -> Optional[tuple[str, str]]:
    if not session_value or "." not in session_value:
        return None
    session_id, session_secret = session_value.split(".", 1)
    if not session_id or not session_secret:
        return None
    return session_id, session_secret


def create_session_for_user(db: DatabaseRepository, username: str) -> tuple[str, datetime]:
    session_id = secrets.token_urlsafe(24)
    session_secret = secrets.token_urlsafe(32)
    session_hash = hashlib.sha256(session_secret.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    db.create_session(
        username=username,
        session_id=session_id,
        session_hash=session_hash,
        expires_at=expires_at.isoformat(),
    )
    return _build_session_value(session_id, session_secret), expires_at


def get_current_user(request: Request) -> AuthenticatedUser:
    db: DatabaseRepository = request.app.state.db
    parsed = _parse_session_value(request.cookies.get(SESSION_COOKIE_NAME))
    if not parsed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session_id, session_secret = parsed
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
    except (KeyError, TypeError, ValueError):
        db.delete_session(session_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
        db.delete_session(session_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if expires_at <= datetime.now(timezone.utc):
        db.delete_session(session_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    expected_hash = session.get("hash", "")
    actual_hash = hashlib.sha256(session_secret.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual_hash, expected_hash):
        db.delete_session(session_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return AuthenticatedUser(username=session["username"])
