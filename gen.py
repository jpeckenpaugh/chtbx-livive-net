#!/usr/bin/env python3
"""Zero-shot voice cloning with Chatterbox TTS.

Clones the voice from a short reference clip (--ref) and speaks --text in that
voice. Omit --ref to use Chatterbox's built-in voice (useful as a smoke test).
"""
import argparse
import pathlib
import sys

import torch
import soundfile as sf

from chatterbox.tts import ChatterboxTTS


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text", required=True, help="text to synthesize")
    p.add_argument("--out", required=True, help="output .wav path")
    p.add_argument("--ref", help="reference .wav of the target voice (~10s)")
    p.add_argument("--device", default=None, help="cuda | mps | cpu (default: auto)")
    p.add_argument("--exaggeration", type=float, default=0.5)
    p.add_argument("--cfg-weight", type=float, default=0.5)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    if args.ref and not pathlib.Path(args.ref).is_file():
        p.error(f"reference clip not found: {args.ref}")

    device = args.device or pick_device()
    if args.seed is not None:
        torch.manual_seed(args.seed)

    print(f"device={device} ref={args.ref or '<built-in voice>'}")
    model = ChatterboxTTS.from_pretrained(device=device)

    wav = model.generate(
        args.text,
        audio_prompt_path=args.ref,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        temperature=args.temperature,
    )

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), wav.squeeze(0).numpy(), model.sr)
    duration = wav.shape[-1] / model.sr
    print(f"wrote {out} ({duration:.2f}s @ {model.sr} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
