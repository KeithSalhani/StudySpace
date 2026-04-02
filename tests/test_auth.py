from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth import (
    _build_session_value,
    _parse_session_value,
    create_password_record,
    create_session_for_user,
    get_current_user,
    validate_password,
    validate_username,
    verify_password,
)
from app.config import SESSION_COOKIE_NAME
from app.db.metadata import JSONDatabase


@pytest.fixture
def db(tmp_path):
    database = JSONDatabase(str(tmp_path / "auth_db.json"))
    database.create_user("alice", "stored-hash", "stored-salt")
    return database


def make_request(db, session_value=None):
    cookies = {}
    if session_value is not None:
        cookies[SESSION_COOKIE_NAME] = session_value
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)), cookies=cookies)


def test_validate_username_trims_valid_input():
    assert validate_username("  alice_123  ") == "alice_123"


@pytest.mark.parametrize("username", ["ab", "bad name", "a" * 33, "semi-colon;"])
def test_validate_username_rejects_invalid_values(username):
    with pytest.raises(ValueError):
        validate_username(username)


def test_validate_password_enforces_bounds():
    assert validate_password("password123") == "password123"

    with pytest.raises(ValueError):
        validate_password("short")

    with pytest.raises(ValueError):
        validate_password("x" * 257)


def test_password_record_round_trip_verifies():
    password_hash, salt = create_password_record("password123")

    assert verify_password("password123", password_hash, salt) is True
    assert verify_password("wrong-password", password_hash, salt) is False


def test_session_value_parser_handles_invalid_input():
    assert _build_session_value("session-id", "secret") == "session-id.secret"
    assert _parse_session_value(None) is None
    assert _parse_session_value("missing-delimiter") is None
    assert _parse_session_value("only-id.") is None
    assert _parse_session_value(".only-secret") is None
    assert _parse_session_value("session-id.secret") == ("session-id", "secret")


def test_get_current_user_accepts_valid_session(db):
    session_value, _expires_at = create_session_for_user(db, "alice")

    user = get_current_user(make_request(db, session_value))

    assert user.username == "alice"


def test_get_current_user_rejects_expired_session_and_deletes_it(db):
    db.create_session(
        "alice",
        "expired-session",
        "hash",
        (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_request(db, "expired-session.secret"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Session expired"
    assert db.get_session("expired-session") is None


def test_get_current_user_rejects_bad_session_hash_and_deletes_it(db):
    session_value, _expires_at = create_session_for_user(db, "alice")
    session_id, _secret = session_value.split(".", 1)
    db.data["users"]["alice"]["sessions"][0]["hash"] = "invalid"
    db.save()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_request(db, session_value))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"
    assert db.get_session(session_id) is None


def test_get_current_user_rejects_invalid_expiry_format_and_deletes_session(db):
    db.create_session("alice", "broken-session", "hash", "not-a-date")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(make_request(db, "broken-session.secret"))

    assert exc_info.value.status_code == 401
    assert db.get_session("broken-session") is None
