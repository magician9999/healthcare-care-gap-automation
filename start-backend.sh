#!/bin/bash

# Healthcare Care Gap Automation - Backend Startup Script
echo "🏥 Starting Healthcare Care Gap Automation Backend..."

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env || touch .env
    echo "📝 Please configure your .env file with database settings"
fi

# Set environment variables for development
export DEBUG=true
export DATABASE_ECHO=false
export LOG_LEVEL=INFO

echo "🚀 Starting FastAPI server on http://localhost:8000"
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔄 Auto-reload enabled for development"
echo ""

# Start the server with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info