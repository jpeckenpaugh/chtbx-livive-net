#!/usr/bin/env python3
"""Render phrases.txt in the cloned voice and encode web-optimized audio.

The model is loaded once and reused for every phrase. Each clip is normalized to
a common *speech level* (active RMS) so the set sounds consistent, then encoded
to the target format.

Examples:
    .venv/bin/python render_phrases.py --ref refs/jarad.m4a --out-dir ../livive-net/audio
    .venv/bin/python render_phrases.py --ref refs/jarad.m4a --format mp3 --bitrate 64k
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

import numpy as np

from gen import normalize_ref, pick_device  # also installs the warning filters
import torch
import soundfile as sf
from chatterbox.tts import ChatterboxTTS

# Why not loudnorm/EBU R128? These are very short clips with high crest factor
# (peaks ~18-24 dB above speech level). EBU R128 targets a hot integrated
# loudness, but loudnorm caps gain at the true-peak ceiling, so it cannot reach
# the target and every clip lands wherever its own crest factor puts it
# (measured -26..-20 LUFS when targeting -16). Peak-normalizing collapses the
# set to one peak instead. Normalizing *speech level* (active RMS) equalizes
# perceived loudness directly and, at the target below, needs no limiting.
SR = 24000  # Chatterbox's native sample rate
SPEECH_LEVEL_DBFS = -25.0  # target active-RMS of speech
LIMIT_DBFS = -1.0  # safety ceiling; not reached at the default target

# Encoder settings per container. Opus/M4A are offered for size/Apple, but MP3
# is the default: it is universally decodable and GitHub Pages serves it with
# the correct `audio/mpeg` MIME type (unknown extensions fall back to
# application/octet-stream, which can break <audio> playback).
FORMATS = {
    "mp3": lambda br: ["-c:a", "libmp3lame", "-b:a", br],
    "m4a": lambda br: ["-c:a", "aac", "-b:a", br],
    "opus": lambda br: ["-c:a", "libopus", "-b:a", br],
    "wav": lambda br: ["-c:a", "pcm_s16le"],
}


def slugify(text: str) -> str:
    text = text.lower().replace("'", "").replace("\u2019", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def read_phrases(path: pathlib.Path) -> list[str]:
    lines = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def speech_level_dbfs(a, sr: int) -> float:
    """Mean level of speech frames, ignoring silence.

    Trims to whole 20 ms frames, keeps frames above -40 dBFS, and returns the
    mean frame RMS in dBFS. A better perceptual proxy than overall RMS, which is
    dragged down by pauses.
    """
    n = max(1, int(0.02 * sr))
    frames = a[: len(a) // n * n].reshape(-1, n)
    frame_rms = np.sqrt((frames**2).mean(axis=1))
    active = frame_rms[frame_rms > 0.01]  # -40 dBFS
    if not len(active):
        return -99.0
    return float(20 * np.log10(active.mean()))


def encode(wav_path: pathlib.Path, out_path: pathlib.Path, fmt: str, bitrate: str,
           target_level: float | None) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found on PATH")
    filters = []
    if target_level:
        a, sr = sf.read(wav_path, dtype="float64")
        if a.ndim > 1:
            a = a.mean(axis=1)
        gain = target_level - speech_level_dbfs(a, sr)
        limit = 10 ** (LIMIT_DBFS / 20)
        # volume applies the gain; alimiter is insurance for clips whose crest
        # factor would otherwise push the peak past the ceiling.
        filters = ["-af", f"volume={gain:.2f}dB,"
                          f"alimiter=limit={limit:.4f}:level=disabled"]
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), *filters,
         "-ac", "1", "-ar", str(SR), *FORMATS[fmt](bitrate), str(out_path)],
        check=True,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ref", required=True, help="reference clip of the target voice")
    p.add_argument("--phrases", default="phrases.txt", help="phrase manifest")
    p.add_argument("--out-dir", default="audio", help="where encoded clips are written")
    p.add_argument("--format", default="mp3", choices=sorted(FORMATS))
    p.add_argument("--bitrate", default="64k")
    p.add_argument("--level", type=float, default=SPEECH_LEVEL_DBFS,
                   help="target speech level in dBFS (active RMS); 0 disables")
    p.add_argument("--wav-dir", default="out/wav", help="keep intermediate WAVs here")
    p.add_argument("--force", action="store_true", help="re-render existing clips")
    p.add_argument("--device", default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--exaggeration", type=float, default=0.5)
    p.add_argument("--cfg-weight", type=float, default=0.5)
    p.add_argument("--temperature", type=float, default=0.8)
    args = p.parse_args()

    phrases = read_phrases(pathlib.Path(args.phrases))
    if not phrases:
        sys.exit(f"no phrases found in {args.phrases}")

    ref = normalize_ref(pathlib.Path(args.ref))
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = pathlib.Path(args.wav_dir)
    wav_dir.mkdir(parents=True, exist_ok=True)

    device = args.device or pick_device()
    print(f"device={device} ref={ref}")
    print(f"rendering {len(phrases)} phrase(s) -> {out_dir} ({args.format}, {args.bitrate})\n")
    model = ChatterboxTTS.from_pretrained(device=device)

    written, skipped = [], []
    for i, text in enumerate(phrases, 1):
        slug = slugify(text)
        out_path = out_dir / f"{slug}.{args.format}"
        if out_path.exists() and not args.force:
            skipped.append(out_path)
            print(f"[{i}/{len(phrases)}] skip   {out_path.name} (exists; --force to redo)")
            continue

        torch.manual_seed(args.seed)  # per-phrase deterministic
        wav = model.generate(
            text,
            audio_prompt_path=str(ref),
            exaggeration=args.exaggeration,
            cfg_weight=args.cfg_weight,
            temperature=args.temperature,
        )
        wav_path = wav_dir / f"{slug}.wav"
        sf.write(str(wav_path), wav.squeeze(0).numpy(), model.sr)

        encode(wav_path, out_path, args.format, args.bitrate,
               args.level if args.level else None)

        dur = wav.shape[-1] / model.sr
        size = out_path.stat().st_size
        flag = "  <-- suspiciously short, check for early EOS" if dur < 0.8 else ""
        print(f"[{i}/{len(phrases)}] {out_path.name}  {dur:.2f}s  {size/1024:.1f} KB{flag}")
        written.append(out_path)

    print(f"\n{len(written)} written, {len(skipped)} skipped -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
