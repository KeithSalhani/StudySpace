import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_services
from app.api.schemas import ChatRequest, ChatResponse
from app.auth import AuthenticatedUser, get_current_user
from app.services.ownership import ensure_selected_files_owned

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    services = get_services()
    try:
        selected_files = ensure_selected_files_owned(
            services.vector_store,
            current_user.username,
            request.selected_files,
        )
        payload = await asyncio.to_thread(
            services.rag_chat.chat,
            request.message,
            current_user.username,
            selected_files,
        )
        return ChatResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(exc)}")
