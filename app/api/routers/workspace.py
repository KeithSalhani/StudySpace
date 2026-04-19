from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db
from app.api.schemas import NoteRequest, TagRequest
from app.auth import AuthenticatedUser, get_current_user

router = APIRouter(tags=["workspace"])


@router.get("/tags")
async def get_tags(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"tags": get_db().get_tags(current_user.username)}


@router.post("/tags")
async def add_tag(request: TagRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    if get_db().add_tag(current_user.username, request.tag):
        return {"message": "Tag added successfully", "tag": request.tag}
    raise HTTPException(status_code=400, detail="Tag already exists")


@router.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    if get_db().delete_tag(current_user.username, tag_name):
        return {"message": "Tag deleted successfully"}
    raise HTTPException(status_code=404, detail="Tag not found")


@router.get("/notes")
async def get_notes(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"notes": get_db().get_notes(current_user.username)}


@router.post("/notes")
async def add_note(request: NoteRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    note = get_db().add_note(current_user.username, request.content)
    return {"message": "Note added successfully", "note": note}


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    if get_db().delete_note(current_user.username, note_id):
        return {"message": "Note deleted successfully"}
    raise HTTPException(status_code=404, detail="Note not found")


@router.get("/metadata")
async def get_metadata(current_user: AuthenticatedUser = Depends(get_current_user)):
    return get_db().get_all_metadata(current_user.username)
