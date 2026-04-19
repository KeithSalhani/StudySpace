import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import get_db, get_services
from app.auth import AuthenticatedUser, get_current_user
from app.services.ownership import get_owned_folder
from app.services.storage import save_upload_file, user_upload_dir

router = APIRouter(tags=["uploads"])


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    file_path: Optional[Path] = None
    services = get_services()
    try:
        filename = os.path.basename(file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        try:
            services.doc_processor.ensure_supported_file(filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        storage_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = user_upload_dir(current_user.username) / storage_name
        folder = None
        normalized_folder_id = folder_id.strip() if isinstance(folder_id, str) else None
        if normalized_folder_id:
            folder = get_owned_folder(get_db(), current_user.username, normalized_folder_id)

        await asyncio.to_thread(save_upload_file, file.file, file_path)
        job = services.upload_jobs.enqueue(
            owner_username=current_user.username,
            filename=filename,
            file_path=file_path,
            folder_id=folder["id"] if folder else None,
            folder_name=folder["name"] if folder else None,
        )
        return {
            "message": f"Document '{filename}' upload accepted",
            "job": job,
        }
    except Exception as exc:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(exc)}")
    finally:
        await file.close()


@router.get("/upload-config")
async def get_upload_config(current_user: AuthenticatedUser = Depends(get_current_user)):
    del current_user
    services = get_services()
    supported_suffixes = services.doc_processor.get_supported_suffixes()
    return {
        "accept": ",".join(supported_suffixes),
        "supported_extensions": list(supported_suffixes),
        "supported_types_label": services.doc_processor.get_supported_types_label(),
    }


@router.get("/upload-jobs")
async def list_upload_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return {"jobs": get_services().upload_jobs.list_jobs(current_user.username, limit=limit)}


@router.get("/upload-jobs/{job_id}")
async def get_upload_job(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    job = get_services().upload_jobs.get_job(current_user.username, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job
