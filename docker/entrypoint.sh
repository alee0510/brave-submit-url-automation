#!/bin/bash
set -e

# Launch Xvfb
if [ "${HEADLESS,,}" != "true" ]; then
    echo "[entrypoint] HEADLESS=false — starting Xvfb on :99"
    Xvfb :99 -screen 0 1920x1080x24 &
    sleep 1
else
    echo "[entrypoint] HEADLESS=true — skipping Xvfb, no virtual display needed"
fi

# Run the submitted python script
exec /app/.venv/bin/python submit.py "$@"