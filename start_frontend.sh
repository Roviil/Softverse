#!/bin/bash
  
# Start Gunicorn processes
echo Starting Gunicorn.
cd "${0%/*}/frontend"
#exec gunicorn app:app --bind 0.0.0.0:8000 --workers 4 -k uvicorn.workers.UvicornWorker 
exec gunicorn app:app --bind unix:/tmp/frontend.sock --workers 4 -k uvicorn.workers.UvicornWorker 
