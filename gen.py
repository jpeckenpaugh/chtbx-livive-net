#!/usr/bin/env python3
"""Zero-shot voice cloning with Chatterbox TTS.

Clones the voice from a short reference clip (--ref) and speaks --text in that
voice. Omit --ref to use Chatterbox's built-in voice (useful as a smoke test).
"""
import argparse
import logging
import pathlib
import shutil
import subprocess
import sys
import tempfile
import warnings

# Known-benign noise from third-party packages. Chatterbox instantiates
# diffusers' LoRACompatibleLinear and calls torch's deprecated sdp_kernel
# context manager, and perth still imports pkg_resources (hence setuptools<81).
# These are installed before the heavy imports so warnings raised at import
# time (e.g. perth -> pkg_resources) are caught too.
warnings.filterwarnings("ignore", message=r".*LoRACompatibleLinear.*")
warnings.filterwarnings("ignore", message=r".*sdp_kernel\(\).*deprecated.*")
warnings.filterwarnings("ignore", message=r".*pkg_resources is deprecated.*")

import torch
import soundfile as sf

from chatterbox.tts import ChatterboxTTS

# The `sdpa` notice is emitted via transformers' logger (not `warnings`), so
# filter it at the logging layer instead. Only this exact message is dropped.
# The notice is logged on a child logger (transformers.integrations.sdpa_attention)
# and reaches the "transformers" handler by propagation, so filter the handler
# too -- filters on the parent logger alone do not apply to child records.
class _DropSdpaNotice(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "does not support `output_attentions=True`" not in record.getMessage()


_hf_logger = logging.getLogger("transformers")
_hf_logger.addFilter(_DropSdpaNotice())
for _handler in _hf_logger.handlers:
    _handler.addFilter(_DropSdpaNotice())


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def normalize_ref(src: pathlib.Path) -> pathlib.Path:
    """Decode any audio container to 24 kHz mono WAV.

    Chatterbox loads the reference through librosa; libsndfile cannot read
    AAC/M4A, so it silently falls back to the deprecated audioread path (and
    that requires ffmpeg at runtime). Normalizing up front avoids that.
    """
    if src.suffix.lower() == ".wav":
        return src
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print(f"note: ffmpeg not found, passing {src} straight to librosa", file=sys.stderr)
        return src
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cb_ref_")) / "ref.wav"
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
         "-ac", "1", "-ar", "24000", str(tmp)],
        check=True,
    )
    print(f"normalized {src} -> {tmp}")
    return tmp


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

    ref = normalize_ref(pathlib.Path(args.ref)) if args.ref else None

    device = args.device or pick_device()
    if args.seed is not None:
        torch.manual_seed(args.seed)

    print(f"device={device} ref={ref or '<built-in voice>'}")
    model = ChatterboxTTS.from_pretrained(device=device)

    wav = model.generate(
        args.text,
        audio_prompt_path=str(ref) if ref else None,
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
