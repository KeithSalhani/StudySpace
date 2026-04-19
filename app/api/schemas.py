from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    selected_files: Optional[List[str]] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    trace: Optional[Dict[str, Any]] = None


class AuthRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    user: Dict[str, Any]


class TagRequest(BaseModel):
    tag: str


class NoteRequest(BaseModel):
    content: str


class FolderRequest(BaseModel):
    name: str


class DocumentFolderRequest(BaseModel):
    folder_id: Optional[str] = None


class ExamFolderRequest(BaseModel):
    name: str


class ExamDocumentFolderRequest(BaseModel):
    folder_id: str


class QuizRequest(BaseModel):
    filename: str
    num_questions: int = 5
    difficulty: str = "Medium"


class FlashcardRequest(BaseModel):
    filename: str
    num_cards: int = 10


class StudySetGenerateRequest(BaseModel):
    filename: str
    type: str
    num_items: int = 10
    difficulty: str = "Medium"


class DeleteAccountRequest(BaseModel):
    username: str
    password: str


class DocumentTagRequest(BaseModel):
    tag: Optional[str] = None
