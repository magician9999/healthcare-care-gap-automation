#!/bin/bash

# EHR MCP Server Startup Script

set -e

echo "Healthcare EHR MCP Server Startup"
echo "================================="

# Check if virtual environment exists
if [ ! -d "../../.venv" ]; then
    echo "Error: Virtual environment not found at ../../.venv"
    echo "Please run this script from the healthcare-care-gap-automation directory"
    exit 1
fi

# Activate virtual environment
source ../../.venv/bin/activate

# Check if required packages are installed
echo "Checking dependencies..."
python -c "import mcp, sqlalchemy, pydantic" 2>/dev/null || {
    echo "Installing missing dependencies..."
    pip install -r requirements.txt
}

# Check database connection
echo "Testing database connection..."
python generate_sample_data.py --test-connection || {
    echo "Error: Database connection failed"
    echo "Please ensure PostgreSQL is running and DATABASE_URL is correct"
    exit 1
}

# Check if sample data exists
echo "Checking for sample data..."
PATIENT_COUNT=$(python -c "
import sys
sys.path.append('../../backend')
from database import get_db_session, Patient
try:
    with get_db_session() as session:
        count = session.query(Patient).count()
        print(count)
except Exception as e:
    print(0)
")

if [ "$PATIENT_COUNT" -eq 0 ]; then
    echo "No sample data found. Generating sample data..."
    python generate_sample_data.py --patients 30
fi

echo "Starting EHR MCP Server..."
echo "Server will listen on stdio for MCP protocol messages"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python server.py