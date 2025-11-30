"""
RAG Chat Application for Student Study Hub
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import tempfile

from config import GEMINI_API_KEY, UPLOAD_DIR, STATIC_DIR, TEMPLATES_DIR
from document_processor import DocumentProcessor
from vector_store import VectorStore
from rag_chat import RAGChat
from db import JSONDatabase

# Check for API key
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable must be set. Please check config.py")

app = FastAPI(title="Student Study Hub RAG Chat")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize components
doc_processor = DocumentProcessor()
vector_store = VectorStore()
rag_chat = RAGChat(vector_store, GEMINI_API_KEY)
db = JSONDatabase()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]

class TagRequest(BaseModel):
    tag: str

class NoteRequest(BaseModel):
    content: str

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": {}})

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process document
        content = doc_processor.process_document(str(file_path))
        
        # Classify document
        # Get current tags as candidates
        current_tags = db.get_tags()
        if not current_tags:
            # Fallback defaults if no tags exist
            current_tags = ['Forensics', 'Machine Learning', 'Security', 'Study Material']
            
        predicted_tag = doc_processor.classify_content(content, current_tags)
        
        if predicted_tag:
            # Add the predicted tag to the database if it doesn't exist (it should, since we used existing tags)
            # But if we used default fallback tags, we might want to save them.
            # For now, let's just ensure it's saved if we classified it.
            if predicted_tag not in db.get_tags():
                db.add_tag(predicted_tag)

        # Add to vector store
        doc_id = f"{file.filename}_{len(vector_store.documents)}"
        metadata = {
            "filename": file.filename, 
            "path": str(file_path),
            "tag": predicted_tag
        }
        vector_store.add_document(doc_id, content, metadata)

        return {
            "message": f"Document '{file.filename}' processed successfully", 
            "doc_id": doc_id,
            "predicted_tag": predicted_tag
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG"""
    try:
        response, sources = rag_chat.chat(request.message)
        return ChatResponse(response=response, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    # We want to list unique filenames, not just doc_ids
    # The vector store keys are doc_ids, but we stored filename in metadata
    # However, for simplicity in the current implementation, the doc_id keys in self.documents
    # were constructed as f"{filename}_{index}".
    # Let's just return the unique filenames extracted from the metadata of stored documents.
    
    # We use a dictionary keyed by filename to store unique documents, so we can update metadata if needed (like different chunks having same metadata)
    unique_docs = {}
    for doc_data in vector_store.documents.values():
        metadata = doc_data.get("metadata", {})
        if "filename" in metadata:
            filename = metadata["filename"]
            if filename not in unique_docs:
                unique_docs[filename] = {
                    "filename": filename,
                    "tag": metadata.get("tag") or "Uncategorized"
                }
            
    return {"documents": list(unique_docs.values())}

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document"""
    try:
        # 1. Remove from vector store
        if vector_store.delete_document(filename):
            # 2. Remove file from filesystem
            file_path = UPLOAD_DIR / filename
            if file_path.exists():
                os.remove(file_path)
            
            return {"message": f"Document '{filename}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found in vector store")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

# Tag Endpoints
@app.get("/tags")
async def get_tags():
    """Get all tags"""
    return {"tags": db.get_tags()}

@app.post("/tags")
async def add_tag(request: TagRequest):
    """Add a new tag"""
    if db.add_tag(request.tag):
        return {"message": "Tag added successfully", "tag": request.tag}
    raise HTTPException(status_code=400, detail="Tag already exists")

@app.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str):
    """Delete a tag"""
    if db.delete_tag(tag_name):
        return {"message": "Tag deleted successfully"}
    raise HTTPException(status_code=404, detail="Tag not found")

# Note Endpoints
@app.get("/notes")
async def get_notes():
    """Get all notes"""
    return {"notes": db.get_notes()}

@app.post("/notes")
async def add_note(request: NoteRequest):
    """Add a new note"""
    note = db.add_note(request.content)
    return {"message": "Note added successfully", "note": note}

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a note"""
    if db.delete_note(note_id):
        return {"message": "Note deleted successfully"}
    raise HTTPException(status_code=404, detail="Note not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
