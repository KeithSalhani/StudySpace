# Student Study Hub RAG Chat

A simple RAG (Retrieval-Augmented Generation) chat application for students to upload documents and chat with AI about their academic content.

## Features

- 📄 Document upload (PDF, DOCX, TXT, MD)
- 🤖 AI chat powered by Google Gemini-2.5 Flash
- 🔍 Vector search using ChromaDB and sentence transformers
- 📚 Source citation in responses
- 🎨 Modern web interface

## Quick Start

1. **Set up environment:**
   ```bash
   # Create virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Get Google Gemini API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Set the environment variable:
   ```bash
   export GEMINI_API_KEY="your_actual_api_key_here"
   ```

3. **Run the demo (optional):**
   ```bash
   python test_demo.py
   ```

4. **Start the web application:**
   ```bash
   python main.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:8000`

## Alternative: Run Script

We've included a convenient run script:

```bash
# Make sure you have GEMINI_API_KEY set
export GEMINI_API_KEY="your_api_key"

# Run the application
./run.sh  # or python main.py
```

## How to Use

1. **Upload Documents:**
   - Click the upload area or drag & drop files
   - Supported formats: PDF, DOCX, TXT, MD
   - Documents are automatically processed and indexed

2. **Chat with AI:**
   - Ask questions about your uploaded documents
   - The AI will provide answers based on your documents
   - Sources are cited for each response

## Architecture

- **Document Processing:** Uses Microsoft Markitdown to convert documents to markdown
- **Embeddings:** Sentence transformers (all-MiniLM-L6-v2) for text embeddings
- **Vector Store:** ChromaDB for storing and searching document embeddings
- **AI Model:** Google Gemini-1.5-flash for generating responses
- **Web Framework:** FastAPI with Jinja2 templates

## Project Structure

```
├── main.py                 # FastAPI application
├── config.py               # Configuration settings
├── document_processor.py   # Document processing with Markitdown
├── vector_store.py         # ChromaDB vector store management
├── rag_chat.py            # Gemini integration for RAG
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Web interface
├── static/                # Static files (CSS/JS)
├── uploads/               # Uploaded documents
└── chroma_db/             # Vector database
```

## Future Enhancements

This is the foundation for a comprehensive Student Study Hub that will include:

- Module auto-classification
- Administrative data extraction (deadlines, contacts)
- Quiz generation
- Flashcard creation
- Calendar integration
- Progress tracking
- Past paper analysis

## Requirements

- Python 3.8+
- Google Gemini API key
- Internet connection for API calls
