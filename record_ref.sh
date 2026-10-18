#!/usr/bin/env bash
# Record a ~10s reference clip of your voice into ref.wav (mono, 24 kHz).
#
# Uses the first available tool of: ffmpeg, sox, macOS `say` (demo only).
# On macOS, QuickTime/Voice Memos is often easiest -- record 10s, then run:
#   afconvert -f WAVE -d LEI16@24000 input.m4a ref.wav
set -euo pipefail

OUT="${1:-ref.wav}"
SECONDS_TO_RECORD="${SECONDS_TO_RECORD:-10}"

echo "Recording ${SECONDS_TO_RECORD}s into ${OUT} -- speak naturally, no background noise."

if command -v ffmpeg >/dev/null 2>&1; then
  # ":0" = first audio input device. Run `ffmpeg -f avfoundation -list_devices true -i ""` to list.
  ffmpeg -y -f avfoundation -i ":0" -t "$SECONDS_TO_RECORD" -ac 1 -ar 24000 "$OUT"
elif command -v sox >/dev/null 2>&1; then
  sox -d -c 1 -r 24000 "$OUT" trim 0 "$SECONDS_TO_RECORD"
else
  cat >&2 <<'EOF'
No ffmpeg or sox found. Record with any app, then convert to a 24 kHz mono WAV:

  # QuickTime Player: File > New Audio Recording, save, then:
  afconvert -f WAVE -d LEI16@24000 /path/to/recording.m4a ref.wav

Or generate a throwaway clip to smoke-test the pipeline (not your voice):
  say -o ref.wav --data-format=LEI16@24000 "This is a test reference clip."
EOF
  exit 1
fi

echo "Wrote ${OUT}."

# Quick level check so you know the clip is usable.
PY="$(dirname "$0")/.venv/bin/python"
if [ -x "$PY" ]; then
  "$PY" - "$OUT" <<'PYEOF'
import sys
import numpy as np
import soundfile as sf

a, sr = sf.read(sys.argv[1], dtype="float64")
peak = float(np.abs(a).max())
rms = float((a**2).mean() ** 0.5)
print(f"  {len(a)/sr:.2f}s | peak {peak:.3f} | rms {rms:.4f}")
if rms < 0.01:
    print("  WARNING: very quiet -- is the mic muted? speak closer and re-record.")
elif peak > 0.99:
    print("  WARNING: clipping -- lower input gain and re-record.")
else:
    print("  Level looks good.")
PYEOF
fi

echo "Preview with: afplay ${OUT}"
