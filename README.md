# Chatterbox voice-clone experiment

Zero-shot voice cloning with [Chatterbox](https://github.com/resemble-ai/chatterbox):
clone a voice from a short reference clip and synthesize arbitrary text.

Target phrase for this experiment: **"Artificial Intelligence & Machine Learning"**.

## Repeatable workflow

```sh
# 1. One-time setup: create .venv (Python 3.14) and install chatterbox-tts
./install.sh

# 2. Record ~10s of your voice -> ref.wav
./record_ref.sh ref.wav
#    (or record in QuickTime, then: afconvert -f WAVE -d LEI16@24000 in.m4a ref.wav)

# 3. Synthesize the phrase in your cloned voice
.venv/bin/python gen.py \
  --ref ref.wav \
  --text "Artificial Intelligence & Machine Learning" \
  --out out/voice.wav

# 4. Listen
afplay out/voice.wav
```

Or via `make`: `make setup && make record && make say && make preview`.

## Reference clip guidelines

- **~10 seconds** of clean, single-speaker speech. Longer is not better; Chatterbox
  truncates the conditioning audio (`ENC_COND_LEN` / `DEC_COND_LEN`).
- Mono, 24 kHz WAV is ideal. Any sample rate works (it is resampled internally).
- No music, background noise, or other speakers.
- Match the language of the reference to the text to avoid accent transfer.

## Tuning knobs

Passed through `gen.py`:

| Flag                 | Default | Effect                                                    |
| :------------------- | :------ | :-------------------------------------------------------- |
| `--exaggeration`     | `0.5`   | Expressiveness. Higher = more dramatic, slightly faster.  |
| `--cfg-weight`       | `0.5`   | Pacing/guidance. Lower (`~0.3`) for slower, deliberate speech. Use `0` to drop the reference accent. |
| `--temperature`      | `0.8`   | Sampling randomness. Lower = more stable.                 |
| `--seed`             | none    | Fix for reproducible output.                              |
| `--device`           | auto    | `cuda` → `mps` → `cpu`. This Mac uses `mps`.              |

## Reproducibility

- Pin the package version in `requirements.txt` (`chatterbox-tts==0.1.7`).
- Fix `--seed` so a given (reference, text, knob) tuple yields the same audio.
- Every output carries Resemble's PerTh watermark — expected, not a bug.

## Layout

```
install.sh        # create .venv + install deps
record_ref.sh     # record a reference clip
gen.py            # clone + synthesize
Makefile          # setup / record / say / preview / clean
requirements.txt  # pinned chatterbox-tts
out/              # generated audio (gitignored)
```
