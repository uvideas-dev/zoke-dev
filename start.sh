#!/bin/bash
# Production start script for Render

# Run migrations if necessary (optional, depending on your setup)
# python -m app.db.init_db 

# Start FastAPI using uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
