#!/bin/bash
cd $(dirname $0)
# Assuming venv is at /opt/raspi-ai/venv
VENV_PATH="/opt/raspi-ai/venv"

if [ -f "$VENV_PATH/bin/activate" ]; then
    source $VENV_PATH/bin/activate
else
    echo "Error: venv not found at $VENV_PATH"
    exit 1
fi

exec python main.py
