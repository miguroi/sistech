#!/usr/bin/env bash
set -e

# Use PORT environment variable or default to 8000
PORT=${PORT:-8000}

echo "🚀 Starting Career Platform API Server on port $PORT"
echo "🌐 Server will be available at http://0.0.0.0:$PORT"

# Start the FastAPI server
exec uvicorn api_server:app --host 0.0.0.0 --port $PORT
