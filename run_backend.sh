#!/bin/bash
# Start the backend API server
cd "$(dirname "$0")/backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
