from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_db, get_services
from app.api.schemas import DocumentFolderRequest, DocumentTagRequest, FolderRequest
from app.auth import AuthenticatedUser, get_current_user
from app.services.ownership import get_owned_document_metadata, get_owned_folder

router = APIRouter(tags=["documents"])
METADATA_LIST_FIELDS = {"assessments", "deadlines", "contacts"}


@router.get("/documents")
async def list_documents(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"documents": get_services().vector_store.list_documents(current_user.username)}


@router.get("/documents/{filename}/file")
async def get_document_file(filename: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    metadata = get_owned_document_metadata(get_db(), get_services().vector_store, current_user.username, filename)
    file_path = Path(metadata["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")

    media_type = "application/pdf" if filename.lower().endswith(".pdf") else None
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
    )


@router.delete("/documents/{filename}")
async def delete_document(filename: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    services = get_services()
    try:
        metadata = get_owned_document_metadata(get_db(), services.vector_store, current_user.username, filename)
        paths_to_delete = services.vector_store.get_document_paths(current_user.username, filename)

        if services.vector_store.delete_document(current_user.username, filename):
            for path in paths_to_delete:
                file_path = Path(path)
                if file_path.exists():
                    file_path.unlink(missing_ok=True)

            processed_path = Path(metadata["processed_path"])
            if processed_path.exists():
                processed_path.unlink(missing_ok=True)

            get_db().delete_document_metadata(current_user.username, filename)
            return {"message": f"Document '{filename}' deleted successfully"}

        raise HTTPException(status_code=404, detail="Document not found in vector store")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(exc)}")


@router.delete("/documents/{filename}/metadata/{section}/{index}")
async def delete_metadata_entry(
    filename: str,
    section: str,
    index: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    database = get_db()
    services = get_services()
    get_owned_document_metadata(database, services.vector_store, current_user.username, filename)

    normalized_section = section.strip().lower()
    if normalized_section not in METADATA_LIST_FIELDS:
        raise HTTPException(status_code=400, detail="Unsupported metadata section")

    current_metadata = dict(database.get_document_metadata(current_user.username, filename) or {})
    entries = current_metadata.get(normalized_section)
    if not isinstance(entries, list):
        raise HTTPException(status_code=404, detail="Metadata section not found")
    if index < 0 or index >= len(entries):
        raise HTTPException(status_code=404, detail="Metadata entry not found")

    next_entries = [item for item_index, item in enumerate(entries) if item_index != index]
    database.set_document_metadata(
        current_user.username,
        filename,
        {normalized_section: next_entries},
    )
    updated_metadata = dict(database.get_document_metadata(current_user.username, filename) or {})
    return {
        "message": "Metadata entry deleted successfully",
        "metadata": updated_metadata,
    }


@router.put("/documents/{filename}/tag")
async def update_document_tag(
    filename: str,
    request: DocumentTagRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    database = get_db()
    services = get_services()
    try:
        get_owned_document_metadata(database, services.vector_store, current_user.username, filename)

        raw_tag = request.tag if request.tag is not None else ""
        normalized_tag = raw_tag.strip()
        if normalized_tag.lower() == "uncategorized":
            normalized_tag = ""

        if normalized_tag:
            database.add_tag(current_user.username, normalized_tag)

        current_metadata = dict(database.get_document_metadata(current_user.username, filename) or {})
        previous_tag = current_metadata.get("tag")
        database.set_document_metadata(current_user.username, filename, {"tag": normalized_tag})

        success = services.vector_store.update_document_tag(current_user.username, filename, normalized_tag)
        if success:
            return {"message": "Document tag updated successfully", "tag": normalized_tag}
        rollback_tag = previous_tag if previous_tag is not None else ""
        database.set_document_metadata(current_user.username, filename, {"tag": rollback_tag})
        raise HTTPException(status_code=500, detail="Failed to update document tag")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error updating document tag: {str(exc)}")


@router.put("/documents/{filename}/folder")
async def update_document_folder(
    filename: str,
    request: DocumentFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    database = get_db()
    services = get_services()
    try:
        get_owned_document_metadata(database, services.vector_store, current_user.username, filename)
        folder = None
        normalized_folder_id = request.folder_id.strip() if isinstance(request.folder_id, str) else None
        if normalized_folder_id:
            folder = get_owned_folder(database, current_user.username, normalized_folder_id)

        previous_metadata = dict(database.get_document_metadata(current_user.username, filename) or {})
        database.set_document_folder(current_user.username, filename, folder["id"] if folder else None)
        success = services.vector_store.update_document_folder(
            current_user.username,
            filename,
            folder["id"] if folder else None,
            folder["name"] if folder else None,
        )
        if not success:
            database.set_document_metadata(
                current_user.username,
                filename,
                {
                    "folder_id": previous_metadata.get("folder_id"),
                    "folder_name": previous_metadata.get("folder_name"),
                },
            )
            raise HTTPException(status_code=500, detail="Failed to update document folder")

        return {
            "message": "Document folder updated successfully",
            "folder_id": folder["id"] if folder else None,
            "folder_name": folder["name"] if folder else None,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error updating document folder: {str(exc)}")


@router.get("/folders")
async def list_folders(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"folders": get_db().list_folders(current_user.username)}


@router.post("/folders", status_code=201)
async def create_folder(request: FolderRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        folder = get_db().create_folder(current_user.username, request.name)
        return {"message": "Folder created successfully", "folder": folder}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
