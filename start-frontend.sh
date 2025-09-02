#!/bin/bash

# Healthcare Care Gap Automation - Frontend Startup Script
echo "🌐 Starting Healthcare Care Gap Automation Frontend..."

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

echo "🚀 Starting Angular development server on http://localhost:4200"
echo "🔄 Hot reload enabled for development"
echo "🌐 Accessible from any browser at http://localhost:4200"
echo ""

# Start Angular development server
ng serve --host 0.0.0.0 --port 4200 --open