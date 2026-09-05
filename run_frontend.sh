#!/bin/bash
# Start the Streamlit frontend
cd "$(dirname "$0")/frontend"
streamlit run app.py --server.port 8501
