import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from app.db.vector_store import VectorStore

@pytest.fixture
def mock_chroma():
    with patch('app.db.vector_store.chromadb.PersistentClient') as MockClient:
        yield MockClient

@pytest.fixture
def mock_sentence_transformer():
    with patch('app.db.vector_store.SentenceTransformer') as MockST:
        yield MockST

@pytest.fixture
def vector_store(mock_chroma, mock_sentence_transformer, tmp_path):
    with patch('app.db.vector_store.COLLECTION_NAME', 'test_collection'), \
         patch('app.db.vector_store.CHROMA_DB_DIR', tmp_path):
        store = VectorStore()
        # Reset mocks for cleaner testing
        store.collection = MagicMock()
        store.embedding_model = MagicMock()
        return store

def test_chunk_text(vector_store):
    text = "Sentence one. " * 50  # Create a long text
    chunks = vector_store._chunk_text(text, chunk_size=100, overlap=20)
    
    assert len(chunks) > 1
    # Check first chunk size
    assert len(chunks[0]) <= 100

def test_add_document(vector_store):
    # Setup
    content = "Test content"
    doc_id = "doc1"
    metadata = {"filename": "test.txt"}
    
    # Mock embedding generation
    vector_store.embedding_model.encode.return_value = np.array([[0.1, 0.2]])
    
    # Execute
    vector_store.add_document(doc_id, content, metadata)
    
    # Verify
    vector_store.collection.add.assert_called_once()
    assert doc_id in vector_store.documents
    assert vector_store.documents[doc_id]["content"] == content

def test_search(vector_store):
    # Setup
    vector_store.embedding_model.encode.return_value = np.array([[0.1, 0.2]])
    vector_store.collection.query.return_value = {
        'documents': [['res1']], 
        'metadatas': [[{'meta': 'data', 'doc_id': 'd1', 'chunk_index': 0}]],
        'distances': [[0.5]],
        'ids': [['id1']]
    }
    
    # Execute
    results = vector_store.search("query", owner_username="alice")
    
    # Verify
    assert len(results) == 1
    assert results[0]['document'] == 'res1'
    vector_store.collection.query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2]],
        n_results=5,
        where={"owner_username": "alice"}
    )


def test_search_with_tag_filter(vector_store):
    vector_store.embedding_model.encode.return_value = np.array([[0.1, 0.2]])
    vector_store.collection.query.return_value = {
        'documents': [[]],
        'metadatas': [[]],
        'distances': [[]],
        'ids': [[]]
    }

    vector_store.search("query", owner_username="alice", selected_tags=["Security"])

    vector_store.collection.query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2]],
        n_results=5,
        where={"$and": [{"owner_username": "alice"}, {"tag": "Security"}]}
    )

def test_delete_document(vector_store):
    # Setup
    # Populate internal state manually as it matches filename
    vector_store.documents = {
        "doc1": {"metadata": {"filename": "target.txt", "owner_username": "alice"}},
        "doc2": {"metadata": {"filename": "target.txt", "owner_username": "bob"}},
        "doc3": {"metadata": {"filename": "other.txt", "owner_username": "alice"}}
    }
    
    # Execute
    result = vector_store.delete_document("alice", "target.txt")
    
    # Verify
    assert result is True
    assert "doc1" not in vector_store.documents
    assert "doc2" in vector_store.documents
    assert "doc3" in vector_store.documents
    vector_store.collection.delete.assert_called_once_with(where={"doc_id": "doc1"})

def test_delete_document_not_found(vector_store):
    vector_store.documents = {}
    assert vector_store.delete_document("alice", "missing.txt") is False

def test_list_documents_returns_unique_filenames_with_tag_fallback(vector_store):
    vector_store.documents = {
        "doc1": {"metadata": {"filename": "alpha.pdf", "tag": "Security", "owner_username": "alice"}},
        "doc2": {"metadata": {"filename": "alpha.pdf", "tag": "ShouldBeIgnored", "owner_username": "alice"}},
        "doc3": {"metadata": {"filename": "beta.pdf", "owner_username": "alice"}},
        "doc4": {"metadata": {"filename": "gamma.pdf", "owner_username": "bob"}},
        "doc5": {"metadata": {"path": "/tmp/no-filename.pdf", "owner_username": "alice"}},
    }
    docs = vector_store.list_documents("alice")
    docs_by_name = {item["filename"]: item for item in docs}

    assert len(docs) == 2
    assert docs_by_name["alpha.pdf"]["tag"] == "Security"
    assert docs_by_name["beta.pdf"]["tag"] == "Uncategorized"

def test_get_document_paths_filters_by_filename_and_deduplicates(vector_store):
    vector_store.documents = {
        "doc1": {"metadata": {"filename": "alpha.pdf", "path": "/tmp/a1.pdf", "owner_username": "alice"}},
        "doc2": {"metadata": {"filename": "alpha.pdf", "path": "/tmp/a1.pdf", "owner_username": "alice"}},
        "doc3": {"metadata": {"filename": "alpha.pdf", "path": "/tmp/a2.pdf", "owner_username": "alice"}},
        "doc4": {"metadata": {"filename": "beta.pdf", "path": "/tmp/b1.pdf", "owner_username": "alice"}},
        "doc5": {"metadata": {"filename": "alpha.pdf", "owner_username": "bob"}},
    }

    paths = vector_store.get_document_paths("alice", "alpha.pdf")

    assert paths == ["/tmp/a1.pdf", "/tmp/a2.pdf"]
