import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_db, get_services
from app.api.schemas import DeleteAccountRequest
from app.auth import AuthenticatedUser, create_password_record, get_current_user, validate_password, validate_username, verify_password
from app.services.account_data import build_account_export, delete_account_data
from app.services.storage import clear_session_cookie

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/export")
async def export_account_data(current_user: AuthenticatedUser = Depends(get_current_user)):
    services = get_services()
    export_bytes = await asyncio.to_thread(
        build_account_export,
        get_db(),
        services.vector_store,
        current_user.username,
    )
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"studyspace-export-{current_user.username}-{date_stamp}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(content=export_bytes, media_type="application/zip", headers=headers)


@router.delete("")
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    username = validate_username(payload.username)
    password = validate_password(payload.password)

    if current_user.username != username:
        raise HTTPException(status_code=403, detail="You can only delete your own account")

    user_record = get_db().get_user_credentials(username)
    if not user_record or not verify_password(
        password,
        user_record["password_hash"],
        user_record["password_salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    services = get_services()
    await asyncio.to_thread(
        delete_account_data,
        get_db(),
        services.vector_store,
        username,
    )
    clear_session_cookie(response)
    return {"message": "Account deleted successfully"}


create_password_record = create_password_record
