#!/bin/bash
# Run InstaBill using the local virtual environment
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/.venv/bin/python3.12" "$DIR/main.py"
