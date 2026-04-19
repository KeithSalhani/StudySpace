from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_db
from app.api.schemas import AuthRequest, SessionResponse
from app.auth import (
    AuthenticatedUser,
    SESSION_COOKIE_NAME,
    create_password_record,
    create_session_for_user,
    get_current_user,
    validate_password,
    validate_username,
    verify_password,
)
from app.services.storage import clear_session_cookie, set_session_cookie, user_processed_dir, user_upload_dir

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=SessionResponse)
async def auth_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    user = get_db().get_user(current_user.username)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return SessionResponse(user=user)


@router.post("/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def auth_signup(request: Request, response: Response, payload: AuthRequest):
    del request
    try:
        username = validate_username(payload.username)
        password = validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    password_hash, password_salt = create_password_record(password)
    try:
        user = get_db().create_user(username, password_hash, password_salt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_upload_dir(username)
    user_processed_dir(username)

    session_value, expires_at = create_session_for_user(get_db(), username)
    set_session_cookie(response, session_value, expires_at)
    return SessionResponse(user=user)


@router.post("/signin", response_model=SessionResponse)
async def auth_signin(request: Request, response: Response, payload: AuthRequest):
    del request
    try:
        username = validate_username(payload.username)
        password = validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_record = get_db().get_user_credentials(username)
    if not user_record or not verify_password(
        password,
        user_record["password_hash"],
        user_record["password_salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = get_db().get_user(username)
    session_value, expires_at = create_session_for_user(get_db(), username)
    set_session_cookie(response, session_value, expires_at)
    return SessionResponse(user=user)


@router.post("/logout")
async def auth_logout(
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    del current_user
    session_value = request.cookies.get(SESSION_COOKIE_NAME)
    if session_value and "." in session_value:
        session_id = session_value.split(".", 1)[0]
        get_db(request).delete_session(session_id)
    clear_session_cookie(response)
    return {"message": "Logged out"}
