# Student Study Hub RAG Chat

A comprehensive RAG (Retrieval-Augmented Generation) chat application designed for students. Upload your academic documents (PDF, DOCX, etc.), let the system automatically classify them, and chat with an AI that understands your specific study materials.

## Features

- **📄 Multi-Format Document Support**: Upload PDF, DOCX, TXT, and MD files.
- **🧠 Smart Auto-Classification**: Automatically categorizes documents into subjects (e.g., "Machine Learning", "Security") using zero-shot classification (`facebook/bart-large-mnli`).
- **🤖 Advanced RAG Chat**: Powered by **Google Gemini-2.5 Flash** for fast, context-aware responses based on your documents.
- **🔍 Semantic Search**: Uses **ChromaDB** and **Sentence Transformers** (`all-MiniLM-L6-v2`) to find the most relevant content for your questions.
- **🏷️ Tag Management**: Organize content with custom tags.
- **📝 Integrated Notes**: Quick note-taking feature to jot down thoughts while studying.
- **📚 Source Citations**: Chat responses cite the specific documents and chunks used.
- **💾 Persistent Storage**: All data (vectors, tags, notes) is saved locally.

## Architecture

- **Frontend/Backend**: FastAPI with Jinja2 templates for a lightweight, responsive web interface.
- **Document Processing**: `MarkItDown` for converting various formats to text.
- **NLP & Classification**: `transformers` pipeline for zero-shot classification.
- **Vector Store**: `ChromaDB` for storing and querying document embeddings.
- **LLM Integration**: `google-generativeai` SDK connecting to Gemini 2.5 Flash.
- **Database**: Simple JSON-based storage for tags and notes (`db.json`).

## Project Structure

```
├── main.py                 # FastAPI application entry point & API routes
├── config.py               # Configuration settings (paths, model names, keys)
├── document_processor.py   # Handles file reading and MarkItDown conversion
├── classification.py       # Zero-shot document classification logic
├── vector_store.py         # ChromaDB wrapper for adding/searching documents
├── rag_chat.py            # RAG implementation using Gemini API
├── db.py                   # JSON database manager for tags and notes
├── db.json                 # Local storage for tags and notes (auto-created)
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates for the web UI
├── static/                 # Static assets (CSS, JS)
├── uploads/                # Directory for uploaded source files
└── chroma_db/             # Directory for Vector database persistence
```

## Installation & Setup

### 1. Prerequisites
- Python 3.8+
- A Google Gemini API Key (Get one from [Google AI Studio](https://aistudio.google.com/app/apikey))

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd StudySpace_Interim

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Set your Gemini API key. You can do this via an environment variable:

```bash
export GEMINI_API_KEY="your_actual_api_key_here"
```

Or create a `.env` file in the project root (if you have `python-dotenv` set up to read it, though the current code relies on `os.getenv` which works with system env vars or `.env` if loaded):
```
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Start the Application

```bash
python main.py
```
The server will start at `http://0.0.0.0:8000`.

### Using the Interface

1.  **Open Browser**: Navigate to `http://localhost:8000`.
2.  **Upload Documents**:
    *   Drag and drop files or click to upload.
    *   The system will process the text and automatically assign a tag (e.g., "Forensics").
3.  **Manage Tags**:
    *   View the auto-assigned tags.
    *   Add new custom tags or delete existing ones via the UI or API.
4.  **Chat with AI**:
    *   Type your question in the chat box.
    *   The AI will search your uploaded documents and provide an answer with citations.
5.  **Take Notes**:
    *   Use the Notes section to save important information alongside your chat.

### API Endpoints

*   `POST /upload`: Upload and process a file.
*   `POST /chat`: Send a message to the RAG chat.
*   `GET /documents`: List all indexed documents.
*   `DELETE /documents/{filename}`: Remove a document.
*   `GET/POST/DELETE /tags`: Manage document categories.
*   `GET/POST/DELETE /notes`: Manage study notes.

## Troubleshooting

*   **Missing API Key**: Ensure `GEMINI_API_KEY` is set in your environment.
*   **Processing Errors**: If a specific PDF fails, check if it's a scanned image (OCR might be needed, which `MarkItDown` supports depending on setup, but standard text extraction is default).
*   **Model Errors**: If `gemini-2.5-flash` is not available for your key/region, update the model name in `rag_chat.py`.

## Future Enhancements

*   Module auto-classification improvements.
*   Administrative data extraction (deadlines, contacts).
*   Quiz generation from study materials.
*   Flashcard creation.
*   Calendar integration.
