"""
Vector store module using ChromaDB and sentence transformers
"""
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import COLLECTION_NAME, CHROMA_DB_DIR, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, DEFAULT_SEARCH_RESULTS

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, collection_name: str = COLLECTION_NAME, persist_directory: str = str(CHROMA_DB_DIR)):
        """
        Initialize vector store with ChromaDB and sentence transformer

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
        """
        self._lock = threading.RLock()
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

        # Initialize sentence transformer
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, device='cpu')

        # Keep track of documents for metadata
        self.documents = {}
        
        # Hydrate self.documents from existing collection
        self._load_documents_from_collection()

        logger.info("Vector store initialized")

    def _load_documents_from_collection(self):
        """Load existing documents metadata from ChromaDB collection"""
        try:
            with self._lock:
                # Get all data
                result = self.collection.get()
                if not result['ids']:
                    return

                # Reconstruct self.documents structure
                # We only have chunks in DB, so we need to aggregate them back to document level metadata
                # This is an approximation because we don't store the full original content in one piece
                # But for metadata purposes (filename, tag), it's enough.
                seen_doc_ids = set()

                for i, metadata in enumerate(result['metadatas']):
                    if not metadata:
                        continue

                    doc_id = metadata.get('doc_id')
                    if doc_id and doc_id not in seen_doc_ids:
                        # Create a dummy entry for self.documents to track existence
                        self.documents[doc_id] = {
                            "content": "(Content loaded from DB)", # We don't load full content to memory on init
                            "metadata": metadata,
                            "chunks": metadata.get('total_chunks', 1)
                        }
                        seen_doc_ids.add(doc_id)
                    
        except Exception as e:
            logger.error(f"Error loading documents from collection: {str(e)}")

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """
        Add a document to the vector store

        Args:
            doc_id: Unique identifier for the document
            content: Text content of the document
            metadata: Additional metadata for the document
        """
        try:
            with self._lock:
                # Split content into chunks (simple approach - split by paragraphs)
                chunks = self._chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)

                # Generate embeddings for each chunk
                embeddings = self.embedding_model.encode(chunks)

                # Prepare data for ChromaDB
                ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
                documents = chunks
                metadatas = []

                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata.update({
                        "doc_id": doc_id,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    })
                    metadatas.append(chunk_metadata)

                # Add to collection
                self.collection.add(
                    embeddings=embeddings.tolist(),
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

                # Store document info
                self.documents[doc_id] = {
                    "content": content,
                    "metadata": metadata or {},
                    "chunks": len(chunks)
                }

                logger.info(f"Added document {doc_id} with {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Error adding document {doc_id}: {str(e)}")
            raise

    def _build_where_filter(
        self,
        owner_username: str,
        selected_files: Optional[List[str]] = None,
        selected_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        filters: List[Dict[str, Any]] = [{"owner_username": owner_username}]

        if selected_files:
            if len(selected_files) == 1:
                filters.append({"filename": selected_files[0]})
            else:
                filters.append({"filename": {"$in": selected_files}})

        cleaned_tags = [
            tag.strip()
            for tag in (selected_tags or [])
            if isinstance(tag, str) and tag.strip() and tag.strip().lower() != "uncategorized"
        ]
        if cleaned_tags:
            if len(cleaned_tags) == 1:
                filters.append({"tag": cleaned_tags[0]})
            else:
                filters.append({"tag": {"$in": cleaned_tags}})

        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def search(
        self,
        query: str,
        owner_username: str,
        n_results: int = 5,
        selected_files: Optional[List[str]] = None,
        selected_tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents

        Args:
            query: Search query
            n_results: Number of results to return
            selected_files: Optional list of filenames to filter by

        Returns:
            List of search results with documents, metadata, and distances
        """
        try:
            # Generate embedding for query outside the store lock so read queries
            # do not block writes while CPU-bound embedding work runs.
            query_embedding = self.embedding_model.encode([query])[0]

            kwargs = {
                "query_embeddings": [query_embedding.tolist()],
                "n_results": n_results,
                "where": self._build_where_filter(
                    owner_username=owner_username,
                    selected_files=selected_files,
                    selected_tags=selected_tags,
                ),
            }

            with self._lock:
                # Search in collection
                results = self.collection.query(**kwargs)

            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                    "id": results['ids'][0][i]
                }
                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            raise

    def delete_document(self, owner_username: str, filename: str):
        """
        Delete a document from the vector store by filename

        Args:
            filename: Name of the file to delete
        """
        try:
            with self._lock:
                # Find doc_id(s) associated with the filename AND owner
                doc_ids_to_remove = []
                for doc_id, doc_data in self.documents.items():
                    metadata = doc_data.get("metadata", {})
                    if metadata.get("owner_username") == owner_username and metadata.get("filename") == filename:
                        doc_ids_to_remove.append(doc_id)

                if not doc_ids_to_remove:
                    logger.warning(f"No document found for user {owner_username} with filename {filename}")
                    return False

                # Delete from ChromaDB
                # We need to delete all chunks. The IDs are constructed as f"{doc_id}_chunk_{i}"
                for doc_id in doc_ids_to_remove:
                    self.collection.delete(where={"doc_id": doc_id})
                    del self.documents[doc_id]
                    logger.info(f"Deleted document {doc_id} (filename: {filename})")

                return True

        except Exception as e:
            logger.error(f"Error deleting document {filename}: {str(e)}")
            raise

    def get_relevant_context(
        self,
        query: str,
        owner_username: str,
        n_results: int = DEFAULT_SEARCH_RESULTS,
        selected_files: Optional[List[str]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Get relevant context for RAG

        Args:
            query: Search query
            n_results: Number of results to retrieve
            selected_files: Optional list of filenames to filter by

        Returns:
            Tuple of (context_string, sources_list)
        """
        results = self.search(
            query,
            owner_username=owner_username,
            n_results=n_results,
            selected_files=selected_files,
        )

        # Combine documents into context
        context_parts = []
        sources = []

        for result in results:
            context_parts.append(result["document"])
            sources.append({
                "doc_id": result["metadata"]["doc_id"],
                "filename": result["metadata"].get("filename", "Unknown"),
                "chunk_index": result["metadata"]["chunk_index"],
                "distance": result["distance"]
            })

        context = "\n\n".join(context_parts)
        return context, sources

    def list_documents(self, owner_username: str) -> List[Dict[str, str]]:
        """List unique documents and their tags."""
        with self._lock:
            unique_docs = {}
            for doc_data in self.documents.values():
                metadata = doc_data.get("metadata", {})
                filename = metadata.get("filename")
                if metadata.get("owner_username") != owner_username or not filename:
                    continue
                    
                if filename not in unique_docs:
                    unique_docs[filename] = {
                        "filename": filename,
                        "tag": metadata.get("tag") or "Uncategorized"
                    }
            return list(unique_docs.values())

    def get_document_paths(self, owner_username: str, filename: str) -> List[str]:
        """Return all stored file paths linked to a logical filename."""
        with self._lock:
            seen_paths = set()
            paths: List[str] = []
            for doc_data in self.documents.values():
                metadata = doc_data.get("metadata", {})
                if metadata.get("owner_username") != owner_username or metadata.get("filename") != filename:
                    continue
                path = metadata.get("path")
                if path and path not in seen_paths:
                    seen_paths.add(path)
                    paths.append(path)
            return paths

    def get_document_metadata(self, owner_username: str, filename: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for doc_data in self.documents.values():
                metadata = doc_data.get("metadata", {})
                if metadata.get("owner_username") == owner_username and metadata.get("filename") == filename:
                    return dict(metadata)
        return None

    def get_full_document_content(self, owner_username: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Return the full processed content for a document when available.

        Falls back to reconstructing the document from stored chunks if the
        processed markdown file is unavailable.
        """
        with self._lock:
            matches: List[Tuple[str, Dict[str, Any]]] = []
            for doc_id, doc_data in self.documents.items():
                metadata = doc_data.get("metadata", {})
                if metadata.get("owner_username") == owner_username and metadata.get("filename") == filename:
                    matches.append((doc_id, dict(metadata)))

        if not matches:
            return None

        for _doc_id, metadata in matches:
            processed_path = metadata.get("processed_path")
            if processed_path and os.path.exists(processed_path):
                with open(processed_path, "r", encoding="utf-8") as handle:
                    return {
                        "filename": filename,
                        "tag": metadata.get("tag"),
                        "content": handle.read(),
                        "source": "processed_markdown",
                    }

        for doc_id, metadata in matches:
            with self._lock:
                result = self.collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])

            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            if not documents:
                continue

            ordered_chunks = sorted(
                zip(metadatas, documents),
                key=lambda item: (item[0] or {}).get("chunk_index", 0),
            )
            content = "\n\n".join(chunk for _meta, chunk in ordered_chunks if chunk)
            if content.strip():
                return {
                    "filename": filename,
                    "tag": metadata.get("tag"),
                    "content": content,
                    "source": "reconstructed_chunks",
                }

        return None

    def update_document_tag(self, owner_username: str, filename: str, new_tag: str) -> bool:
        """Update the tag for all chunks of a specific document."""
        try:
            with self._lock:
                doc_ids_to_update = []
                for doc_id, doc_data in self.documents.items():
                    metadata = doc_data.get("metadata", {})
                    if metadata.get("owner_username") == owner_username and metadata.get("filename") == filename:
                        doc_ids_to_update.append((doc_id, metadata, doc_data["chunks"]))

                if not doc_ids_to_update:
                    return False

                for doc_id, metadata, num_chunks in doc_ids_to_update:
                    # Update metadata in memory
                    metadata["tag"] = new_tag
                    
                    # Prepare data to update in ChromaDB
                    ids = [f"{doc_id}_chunk_{i}" for i in range(num_chunks)]
                    metadatas = []
                    for i in range(num_chunks):
                        chunk_meta = metadata.copy()
                        chunk_meta.update({
                            "doc_id": doc_id,
                            "chunk_index": i,
                            "total_chunks": num_chunks
                        })
                        metadatas.append(chunk_meta)

                    # Update in ChromaDB collection
                    self.collection.update(ids=ids, metadatas=metadatas)

                logger.info(f"Updated tag to '{new_tag}' for document {filename}")
                return True

        except Exception as e:
            logger.error(f"Error updating tag for document {filename}: {str(e)}")
            return False

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # If we're not at the end, try to find a good breaking point
            if end < len(text):
                # Look for paragraph break
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break != -1 and paragraph_break > start + chunk_size // 2:
                    end = paragraph_break + 2
                else:
                    # Look for sentence break
                    sentence_break = text.rfind('. ', start, end)
                    if sentence_break != -1 and sentence_break > start + chunk_size // 2:
                        end = sentence_break + 2
                    else:
                        # Look for space
                        space_break = text.rfind(' ', start, end)
                        if space_break != -1:
                            end = space_break

            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + 1, end - overlap)

        return chunks
