#!/bin/bash
# Simple run script for the RAG Chat application

echo "🎓 Student Study Hub RAG Chat"
echo "=============================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if API key is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY environment variable not set."
    echo "   Get your API key from: https://makersuite.google.com/app/apikey"
    echo "   Then run: export GEMINI_API_KEY='your_api_key'"
    exit 1
fi

echo "🚀 Starting web application..."
echo "   Open http://localhost:8000 in your browser"
echo ""

# Start the application
python main.py
