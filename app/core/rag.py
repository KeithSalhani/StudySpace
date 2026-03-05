"""
RAG Chat module using Gemini-2.0 Flash
"""
from google import genai
import os
import logging
from typing import List, Dict, Any, Tuple
from app.db.vector_store import VectorStore

logger = logging.getLogger(__name__)

class RAGChat:
    def __init__(self, vector_store: VectorStore, api_key: str = None):
        """
        Initialize RAG chat with Gemini

        Args:
            vector_store: Vector store instance
            api_key: Google AI API key (can also be set via GEMINI_API_KEY env var)
        """
        self.vector_store = vector_store

        # Set up API key
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        # Initialize Google Gen AI client
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3.1-flash-lite-preview'

        logger.info("RAG Chat initialized with Gemini 3.1 Flash Lite Preview")

    def chat(self, message: str, selected_files: List[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a chat message with RAG

        Args:
            message: User message
            selected_files: Optional list of filenames to filter by

        Returns:
            Tuple of (response, sources)
        """
        try:
            # Get relevant context from vector store
            context, sources = self.vector_store.get_relevant_context(message, selected_files=selected_files)

            # Create prompt with context
            prompt = self._create_prompt(message, context)

            # Generate response with Gemini
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )

            if not response.text:
                raise ValueError("Empty response from Gemini")

            return response.text, sources

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            raise

    def _create_prompt(self, message: str, context: str) -> str:
        """
        Create a prompt for Gemini with context

        Args:
            message: User message
            context: Relevant context from documents

        Returns:
            Formatted prompt
        """
        if context.strip():
            prompt = f"""You are a helpful AI assistant for students studying various academic modules.
You have access to the following relevant information from the student's documents:

{context}

Based on the above context, please answer the following question:

{message}

If the context doesn't contain relevant information to answer the question, please say so and provide a general response based on your knowledge.

Please provide a clear, concise, and helpful response."""
        else:
            prompt = f"""You are a helpful AI assistant for students. The user asked: {message}

Since no relevant context was found in the uploaded documents, please provide a general response based on your knowledge."""

        return prompt
