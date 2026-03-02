#!/bin/bash
set -e

echo "🚀 Starting ZoKe Backend..."
ls -R app | head -n 20 # Debug: Show directory structure

# Start FastAPI using uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
