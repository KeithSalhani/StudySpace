#!/usr/bin/env python3
"""
Demo script for the RAG Chat application
"""
import os
import tempfile
from pathlib import Path

# Set a dummy API key for demo
os.environ['GEMINI_API_KEY'] = 'demo_key_for_testing'

from document_processor import DocumentProcessor
from vector_store import VectorStore
from rag_chat import RAGChat

def demo():
    print("🎓 Student Study Hub RAG Chat Demo")
    print("=" * 50)

    # Initialize components
    print("📚 Initializing components...")
    doc_processor = DocumentProcessor()
    vector_store = VectorStore()
    rag_chat = RAGChat(vector_store, "demo_key")

    # Create a sample document
    sample_content = """
    # Introduction to Machine Learning

    Machine Learning (ML) is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.

    ## Key Concepts

    ### Supervised Learning
    In supervised learning, the algorithm learns from labeled training data. The goal is to learn a mapping from inputs to outputs.

    ### Unsupervised Learning
    Unsupervised learning finds hidden patterns in data without labeled examples. Common techniques include clustering and dimensionality reduction.

    ### Deep Learning
    Deep learning uses neural networks with multiple layers to model complex patterns in data.

    ## Applications

    - Image recognition
    - Natural language processing
    - Recommendation systems
    - Predictive analytics

    ## Assessment Information

    - Midterm Exam: 30% of final grade
    - Final Project: 40% of final grade
    - Weekly Assignments: 30% of final grade

    Lecturer: Dr. Sarah Johnson
    Contact: sarah.johnson@university.edu
    Office Hours: Tuesdays 2-4 PM
    """

    # Save sample document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(sample_content)
        temp_file = f.name

    try:
        print("📄 Processing sample document...")
        # Process document
        processed_content = doc_processor.process_text_file(temp_file)
        print(f"✅ Document processed: {len(processed_content)} characters")

        # Add to vector store
        vector_store.add_document("ml_intro", processed_content, {"filename": "ml_intro.md", "subject": "Machine Learning"})
        print("✅ Document added to vector store")

        # Test search
        print("\n🔍 Testing search functionality...")
        results = vector_store.search("supervised learning", n_results=2)
        print(f"✅ Found {len(results)} relevant chunks")

        # Test RAG chat
        print("\n🤖 Testing RAG chat...")
        questions = [
            "What is supervised learning?",
            "What are the assessment weights for this course?",
            "Who is the lecturer and how can I contact them?"
        ]

        for question in questions:
            print(f"\n❓ Question: {question}")
            try:
                response, sources = rag_chat.chat(question)
                print(f"🤖 Answer: {response[:200]}..." if len(response) > 200 else f"🤖 Answer: {response}")
                print(f"📚 Sources: {len(sources)} chunks found")
            except Exception as e:
                print(f"❌ Error: {e}")

        print("\n🎉 Demo completed successfully!")
        print("\nTo run the full web application:")
        print("1. Get a real Gemini API key from https://makersuite.google.com/app/apikey")
        print("2. Set GEMINI_API_KEY environment variable")
        print("3. Run: python main.py")
        print("4. Open http://localhost:8000 in your browser")

    finally:
        # Clean up
        Path(temp_file).unlink()

if __name__ == "__main__":
    demo()
