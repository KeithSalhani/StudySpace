import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_db, get_services
from app.api.schemas import ExamDocumentFolderRequest, ExamFolderRequest
from app.auth import AuthenticatedUser, get_current_user
from app.services.ownership import (
    get_owned_exam_document,
    get_owned_exam_folder,
    list_exam_folder_documents,
)
from app.services.storage import save_upload_file, user_exam_papers_dir

router = APIRouter(tags=["exams"])


@router.get("/exam-folders")
async def list_exam_folders(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"folders": get_db().list_exam_folders(current_user.username)}


@router.post("/exam-folders", status_code=status.HTTP_201_CREATED)
async def create_exam_folder(
    request: ExamFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        folder = get_db().create_exam_folder(current_user.username, request.name)
        return {"message": "Exam folder created successfully", "folder": folder}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/exam-folders/{folder_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_exam_folder(
    folder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    database = get_db()
    folder = get_owned_exam_folder(database, current_user.username, folder_id)
    documents = list_exam_folder_documents(database, current_user.username, folder_id)
    if not documents:
        raise HTTPException(status_code=400, detail="No exam papers found in this folder")

    try:
        job = get_services().topic_mining_jobs.enqueue(
            owner_username=current_user.username,
            folder_id=folder["id"],
            folder_name=folder["name"],
            total_documents=len(documents),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    analysis = database.get_exam_folder_analysis(current_user.username, folder_id)
    return {
        "message": "Topic mining started",
        "job": job,
        "analysis": analysis,
    }


@router.get("/exam-folders/{folder_id}/analysis")
async def get_exam_folder_analysis(
    folder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    database = get_db()
    get_owned_exam_folder(database, current_user.username, folder_id)
    analysis = database.get_exam_folder_analysis(current_user.username, folder_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No topic analysis found for this folder")
    return analysis


@router.get("/exam-papers")
async def list_exam_papers(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"documents": get_db().list_exam_documents(current_user.username)}


@router.post("/exam-papers/upload", status_code=status.HTTP_201_CREATED)
async def upload_exam_paper(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    filename = os.path.basename(file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    database = get_db()
    folder = get_owned_exam_folder(database, current_user.username, folder_id)
    storage_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = user_exam_papers_dir(current_user.username) / storage_name

    try:
        await asyncio.to_thread(save_upload_file, file.file, file_path)
        document = database.add_exam_document(
            current_user.username,
            {
                "id": uuid.uuid4().hex,
                "filename": filename,
                "folder_id": folder["id"],
                "folder_name": folder["name"],
                "path": str(file_path),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream",
            },
        )
        return {"message": "Exam paper uploaded successfully", "document": document}
    except HTTPException:
        raise
    except Exception as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error uploading exam paper: {str(exc)}")
    finally:
        await file.close()


@router.put("/exam-papers/{document_id}/folder")
async def move_exam_paper(
    document_id: str,
    request: ExamDocumentFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        get_owned_exam_document(get_db(), current_user.username, document_id)
        updated = get_db().update_exam_document_folder(current_user.username, document_id, request.folder_id)
        return {
            "message": "Exam paper moved successfully",
            "document": updated,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/exam-papers/{document_id}/file")
async def get_exam_paper_file(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    document = get_owned_exam_document(get_db(), current_user.username, document_id)
    file_path = Path(document["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Exam paper file not found")

    media_type = document.get("content_type") or (
        "application/pdf" if str(document.get("filename", "")).lower().endswith(".pdf") else None
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=document.get("filename"),
        content_disposition_type="inline",
    )
