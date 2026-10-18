#!/usr/bin/env bash
set -euo pipefail

# Create a Python 3.14 virtual environment and install dependencies.
PYTHON="${PYTHON:-python3.14}"
VENV_DIR="${VENV_DIR:-.venv}"

cd "$(dirname "$0")"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt

echo "Done. Activate with: source $VENV_DIR/bin/activate"
