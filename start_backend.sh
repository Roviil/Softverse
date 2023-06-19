#!/bin/bash

# Start Gunicorn processes
echo Starting Backend Process.
cd "${0%/*}/backend"
python server_subscribe.py
