#!/bin/bash

# Healthcare Care Gap Automation - Complete Application Startup Script
echo "🏥 Starting Healthcare Care Gap Automation System..."
echo "=============================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ All prerequisites are available"
echo ""

# Function to start backend
start_backend() {
    echo "🏥 Starting Backend Service..."
    cd "$(dirname "$0")/backend"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Set development environment
    export DEBUG=true
    export LOG_LEVEL=INFO
    
    # Start server
    echo "🚀 Backend starting on http://localhost:8000"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    cd ..
}

# Function to start frontend
start_frontend() {
    echo "🌐 Starting Frontend Service..."
    cd "$(dirname "$0")/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing Node.js dependencies..."
        npm install
    fi
    
    # Start Angular server
    echo "🚀 Frontend starting on http://localhost:4200"
    ng serve --host 0.0.0.0 --port 4200 &
    FRONTEND_PID=$!
    
    cd ..
}

# Start services
start_backend
sleep 3  # Give backend time to start
start_frontend

echo ""
echo "🎉 Healthcare Care Gap Automation System Started!"
echo "=============================================="
echo "🏥 Backend API: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🌐 Frontend: http://localhost:4200"
echo "🔧 System Status: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup INT TERM EXIT

# Wait for services (keep script running)
wait