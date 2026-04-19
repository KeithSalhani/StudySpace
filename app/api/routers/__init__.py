from app.api.routers.account import router as account_router
from app.api.routers.auth import router as auth_router
from app.api.routers.chat import router as chat_router
from app.api.routers.documents import router as documents_router
from app.api.routers.exams import router as exams_router
from app.api.routers.study import router as study_router
from app.api.routers.ui import router as ui_router
from app.api.routers.uploads import router as uploads_router
from app.api.routers.workspace import router as workspace_router

__all__ = [
    "account_router",
    "auth_router",
    "chat_router",
    "documents_router",
    "exams_router",
    "study_router",
    "ui_router",
    "uploads_router",
    "workspace_router",
]
