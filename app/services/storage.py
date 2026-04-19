from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import Response

from app.auth import SESSION_COOKIE_NAME
from app.config import SESSION_COOKIE_SECURE, USERS_DIR


def user_root(username: str) -> Path:
    path = USERS_DIR / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_upload_dir(username: str) -> Path:
    path = user_root(username) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_processed_dir(username: str) -> Path:
    path = user_root(username) / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_exam_papers_dir(username: str) -> Path:
    path = user_root(username) / "exam_papers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload_file(source_file, destination: Path) -> None:
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(source_file, buffer)


def set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
        expires=int(expires_at.timestamp()),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
