#!/usr/bin/env python3
"""Print duration/level stats for an audio file with a usability verdict."""
import sys

import numpy as np
import soundfile as sf

if len(sys.argv) < 2:
    sys.exit("usage: check_level.py AUDIO_FILE")

a, sr = sf.read(sys.argv[1], dtype="float64")
if a.ndim > 1:
    a = a.mean(axis=1)
dur = len(a) / sr
peak = float(np.abs(a).max())
rms = float((a**2).mean() ** 0.5)

print(f"  {sys.argv[1]}: {dur:.2f}s @ {sr} Hz | peak {peak:.3f} | rms {rms:.4f}")

warnings = []
if rms < 0.01:
    warnings.append("very quiet - is the mic muted? speak closer and re-record")
if peak > 0.99:
    warnings.append("clipping - lower input gain and re-record")
if dur > 12:
    warnings.append("longer than ~10s - Chatterbox truncates the conditioning audio")
if dur < 3:
    warnings.append("shorter than ~3s - may not capture enough of your voice")

if warnings:
    for w in warnings:
        print(f"  WARNING: {w}")
else:
    print("  Level looks good.")
