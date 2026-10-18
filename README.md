# Chatterbox voice-clone experiment

Zero-shot voice cloning with [Chatterbox](https://github.com/resemble-ai/chatterbox):
clone a voice from a short reference clip and synthesize arbitrary text.

Target phrase for this experiment: **"Artificial Intelligence & Machine Learning"**.
Rendered for the portfolio at <https://www.livive.net/>.

## Repeatable workflow

```sh
# 1. One-time setup: create .venv (Python 3.14) and install chatterbox-tts
./install.sh

# 2. Record ~10s of your voice -> ref.wav
./record_ref.sh ref.wav

#    Or convert an existing recording (QuickTime, Voice Memos, iPhone):
./prep_ref.sh ~/Desktop/my-voice.m4a ref.wav

# 3. Synthesize the phrase in your cloned voice
.venv/bin/python gen.py \
  --ref ref.wav \
  --text "Artificial Intelligence & Machine Learning" \
  --out out/voice.wav

# 4. Listen
afplay out/voice.wav
```

Or via `make`: `make setup && make record && make say && make preview`.

## Web audio for the portfolio (livive.net)

Render a whole set of phrases (category titles, taglines) as web-optimized audio
and drop them into the portfolio repo:

```sh
make web                     # renders phrases.txt -> ../livive-net/audio
# or explicitly:
.venv/bin/python render_phrases.py --ref refs/jarad.m4a --out-dir ../livive-net/audio
```

The model loads once for the whole batch. Existing clips are skipped unless you
pass `--force`. Edited `phrases.txt`? Just re-run.

### Format recommendation: MP3, mono, 24 kHz, 64 kbps

| Option | Verdict |
| :--- | :--- |
| **MP3 (chosen)** | Universally decodable; GitHub Pages serves `.mp3` as `audio/mpeg`. |
| AAC / `.m4a` | Good for Apple, but Firefox-on-Linux may lack an AAC decoder, and Pages may not map the MIME type. |
| Opus in `.webm`/`.opus` | Best quality-per-byte (~half the size), but Safari/Opus container support is uneven and Pages likely serves `.opus` as `application/octet-stream`, which can break `<audio>`. |

These are 1–3 second clips, so size is a non-issue (~116 KB for all 8). Prefer
the format with zero playback risk. Keep MP3 mono at the source's 24 kHz — no
resampling, no stereo, and CBR is fine at these sizes.

`<audio>` MIME types matter: Pages serves known extensions (`video/webm`,
`image/webp`) with correct `Content-Type`, but unknown ones fall back to
`application/octet-stream`, which some browsers refuse to play.

### Levels

Clips are normalized to a common **speech level** (active RMS, default
`-25 dBFS`) with a `-1 dBFS` safety limiter. This is deliberately *not* EBU R128
`loudnorm`: these short clips have 18–24 dB crest factors, so `loudnorm` caps its
gain at the true-peak ceiling and each clip lands wherever its own dynamics put
it (measured −26…−20 LUFS when targeting −16 — a 6 dB spread). Speech-level
normalization brought the set to a **0.99 dB spread** with a max peak of −1.8 dBFS
and no limiting engaged.

### Naming and layout

Files are named by slugified phrase, e.g. `It's a live vive` →
`its-a-live-vive.mp3`, in `livive-net/audio/` (a root-level media folder,
matching the existing `previews/` and `thumbnails/`).

To use a clip:

```html
<audio src="/audio/artificial-intelligence-and-machine-learning.mp3" preload="none"></audio>
```

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
- `gen.py` normalizes non-WAV references to 24 kHz mono WAV via ffmpeg, so
  `.m4a`/`.mp3` behave identically to `.wav` and skip librosa's deprecated
  `audioread` fallback.

## Reading the debug output

`gen.py` silences the known-benign chatter from third-party libraries, so a
clean run only shows real information:

| Suppressed message | Why it appears | Handled by |
| :--- | :--- | :--- |
| `pkg_resources is deprecated` | `perth` imports `pkg_resources`; that is why `setuptools<81` is pinned | `warnings` filter |
| ``LoRACompatibleLinear` is deprecated` | `diffusers==0.29.0` constructs the class | `warnings` filter |
| ``torch.backends.cuda.sdp_kernel()` is deprecated` | Chatterbox internals; a no-op on MPS | `warnings` filter |
| ``sdpa` attention does not support `output_attentions=True`` | `transformers` `logger.warning_once` | logging filter |

Note: **installing `peft` does not silence** the `LoRACompatibleLinear` warning.
That warning is emitted inside `LoRACompatibleLinear.__init__` on every
construction — not an "is peft installed?" check — so only a diffusers upgrade
would remove it. `peft` is therefore not a dependency here.

Remaining output worth acting on:

| Message | Meaning / fix |
| :--- | :--- |
| `You are sending unauthenticated requests to the HF Hub` | Set `HF_TOKEN` (e.g. `export HF_TOKEN=hf_...`) for faster, rate-limit-free model downloads. Only matters on first run; the weights are cached afterwards |
| `loaded PerthNet (Implicit) at step 250,000` | Info — watermarker ready |
| `Sampling: N%` | Progress bar (generation stops early at end-of-utterance) |
| `PySoundFile failed. Trying audioread instead` | Should no longer occur: `gen.py` converts non-WAV references to 24 kHz mono WAV first. If you see it, `ffmpeg` was not on `PATH`, or you called `prepare_conditionals` directly |
| `wrote ... (0.5s @ 24000 Hz)` for a long sentence | Early EOS / truncation. Retry with a different `--seed`, raise `--cfg-weight`, or record a cleaner reference |

## Layout

```
install.sh        # create .venv + install deps
record_ref.sh     # record a reference clip
prep_ref.sh       # convert an existing recording to ref.wav
check_level.py    # (used by the two above) duration/level verdict
gen.py            # clone + synthesize one phrase
render_phrases.py # batch render phrases.txt -> web audio
phrases.txt       # phrase manifest (category titles, taglines)
Makefile          # setup / record / prep / say / web / preview / clean
requirements.txt  # pinned chatterbox-tts
out/              # generated audio + intermediate WAVs (gitignored)
```
