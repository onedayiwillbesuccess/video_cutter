#!/bin/bash
# Start the backend API server (niced so it never starves other VMs on the host)
cd "$(dirname "$0")/backend"
export PYTHONPATH="$(pwd)"
nice -n 19 python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload