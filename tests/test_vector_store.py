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


def test_add_document_sanitizes_nullable_and_nested_metadata(vector_store):
    content = "Test content"
    doc_id = "doc1"
    metadata = {
        "filename": "test.txt",
        "tag": None,
        "folder_id": None,
        "extra": {"course": "Security"},
    }

    vector_store.embedding_model.encode.return_value = np.array([[0.1, 0.2]])

    vector_store.add_document(doc_id, content, metadata)

    vector_store.collection.add.assert_called_once_with(
        embeddings=[[0.1, 0.2]],
        documents=["Test content"],
        metadatas=[
            {
                "filename": "test.txt",
                "extra": '{"course": "Security"}',
                "doc_id": "doc1",
                "chunk_index": 0,
                "total_chunks": 1,
            }
        ],
        ids=["doc1_chunk_0"],
    )
    assert vector_store.documents[doc_id]["metadata"] == {
        "filename": "test.txt",
        "extra": '{"course": "Security"}',
    }

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


def test_build_where_filter_supports_multiple_files_and_tags(vector_store):
    where = vector_store._build_where_filter(
        owner_username="alice",
        selected_files=["week1.pdf", "week2.pdf"],
        selected_tags=["Security", "  Uncategorized  ", "Forensics"],
    )

    assert where == {
        "$and": [
            {"owner_username": "alice"},
            {"filename": {"$in": ["week1.pdf", "week2.pdf"]}},
            {"tag": {"$in": ["Security", "Forensics"]}},
        ]
    }

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


def test_get_relevant_context_combines_documents_and_sources(vector_store):
    vector_store.search = MagicMock(
        return_value=[
            {
                "document": "Chunk one",
                "metadata": {"doc_id": "doc1", "filename": "week1.pdf", "chunk_index": 0},
                "distance": 0.1,
            },
            {
                "document": "Chunk two",
                "metadata": {"doc_id": "doc2", "filename": "week2.pdf", "chunk_index": 1},
                "distance": 0.2,
            },
        ]
    )

    context, sources = vector_store.get_relevant_context("query", owner_username="alice", selected_files=["week1.pdf"])

    assert context == "Chunk one\n\nChunk two"
    assert sources == [
        {"doc_id": "doc1", "filename": "week1.pdf", "chunk_index": 0, "distance": 0.1},
        {"doc_id": "doc2", "filename": "week2.pdf", "chunk_index": 1, "distance": 0.2},
    ]


def test_get_document_metadata_returns_copy(vector_store):
    vector_store.documents = {
        "doc1": {"metadata": {"filename": "alpha.pdf", "owner_username": "alice", "tag": "Security"}}
    }

    metadata = vector_store.get_document_metadata("alice", "alpha.pdf")
    metadata["tag"] = "Changed"

    assert vector_store.documents["doc1"]["metadata"]["tag"] == "Security"


def test_get_full_document_content_prefers_processed_markdown(vector_store, tmp_path):
    processed_path = tmp_path / "alpha.md"
    processed_path.write_text("Full markdown", encoding="utf-8")
    vector_store.documents = {
        "doc1": {
            "metadata": {
                "filename": "alpha.pdf",
                "owner_username": "alice",
                "processed_path": str(processed_path),
                "tag": "Security",
            }
        }
    }

    payload = vector_store.get_full_document_content("alice", "alpha.pdf")

    assert payload == {
        "filename": "alpha.pdf",
        "tag": "Security",
        "content": "Full markdown",
        "source": "processed_markdown",
    }


def test_get_full_document_content_reconstructs_from_chunks(vector_store):
    vector_store.documents = {
        "doc1": {
            "metadata": {"filename": "alpha.pdf", "owner_username": "alice", "tag": "Security"},
            "chunks": 2,
        }
    }
    vector_store.collection.get.return_value = {
        "documents": ["Second", "First"],
        "metadatas": [{"chunk_index": 1}, {"chunk_index": 0}],
    }

    payload = vector_store.get_full_document_content("alice", "alpha.pdf")

    assert payload == {
        "filename": "alpha.pdf",
        "tag": "Security",
        "content": "First\n\nSecond",
        "source": "reconstructed_chunks",
    }


def test_update_document_tag_updates_memory_and_collection(vector_store):
    vector_store.documents = {
        "doc1": {
            "metadata": {"filename": "alpha.pdf", "owner_username": "alice", "tag": "OldTag"},
            "chunks": 2,
        }
    }

    result = vector_store.update_document_tag("alice", "alpha.pdf", "NewTag")

    assert result is True
    assert vector_store.documents["doc1"]["metadata"]["tag"] == "NewTag"
    vector_store.collection.update.assert_called_once_with(
        ids=["doc1_chunk_0", "doc1_chunk_1"],
        metadatas=[
            {"filename": "alpha.pdf", "owner_username": "alice", "tag": "NewTag", "doc_id": "doc1", "chunk_index": 0, "total_chunks": 2},
            {"filename": "alpha.pdf", "owner_username": "alice", "tag": "NewTag", "doc_id": "doc1", "chunk_index": 1, "total_chunks": 2},
        ],
    )
