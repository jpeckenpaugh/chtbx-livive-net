#!/usr/bin/env bash
# Convert an existing recording (m4a, mp3, aiff, ...) into a 24 kHz mono WAV
# reference clip. Use this for files from QuickTime, Voice Memos, iPhone, etc.
#
#   ./prep_ref.sh ~/Desktop/my-voice.m4a ref.wav
set -euo pipefail

IN="${1:?usage: prep_ref.sh INPUT [OUT]}"
OUT="${2:-ref.wav}"

[ -f "$IN" ] || { echo "no such file: $IN" >&2; exit 1; }

ffmpeg -y -loglevel error -i "$IN" -ac 1 -ar 24000 "$OUT"

PY="$(dirname "$0")/.venv/bin/python"
if [ -x "$PY" ]; then
  "$PY" "$(dirname "$0")/check_level.py" "$OUT"
fi

echo "Preview with: afplay ${OUT}"
