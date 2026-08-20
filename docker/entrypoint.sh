#!/bin/bash
set -e

# Launch Xvfb
Xvfb :99 -screen 0 1920x1080x24 &

# Wait for Xvfb to be ready
sleep 1

# Run the submitted python script
exec /app/.venv/bin/python submit.py "$@"