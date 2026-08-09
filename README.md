# Celloscope Speech & Document Extraction

An AI service with two jobs:

- **Transcribe audio** in Bengali and English (`POST /api/v1/transcribe`)
- **Pull structured data out of photographed lab reports** in English (`POST /api/v1/documents/extract`)

Both endpoints can run against a **mock** provider (no network, no model, no API key — the default) or a **real** provider (Whisper/Gemini for speech, Gemini for extraction), switched purely by config. See [DECISIONS.md](DECISIONS.md) for why those specific providers were picked and what got rejected along the way.

## Running it

### With Docker (recommended — this is what gets graded)

```bash
docker compose up
```

No `.env` file needed. This boots the API on mock adapters only — zero credentials, zero model downloads. Once it's up:

```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -F "file=@testdata/harvard.wav" \
  -F "language=en"

curl -X POST http://localhost:8000/api/v1/documents/extract \
  -F "file=@testdata/image.png"

curl http://localhost:8000/health
```

`/health` also tells you which providers are currently active, so you can confirm at a glance whether you're hitting mocks or real adapters.

To switch on a real provider, copy `.env.example` to `.env` and fill in what you need:

```bash
cp .env.example .env
# then edit .env: set TRANSCRIPTION_PROVIDER and/or EXTRACTION_PROVIDER
```

| Setting | Options | Needs |
|---|---|---|
| `TRANSCRIPTION_PROVIDER` | `mock` \| `whisper` \| `gemini` | `whisper`: nothing, downloads model weights on first use. `gemini`: `GEMINI_API_KEY`. |
| `EXTRACTION_PROVIDER` | `mock` \| `gemini` | `gemini`: `GEMINI_API_KEY`. |

Self-hosted Whisper is CPU-only by default inside the Docker image (`WHISPER_DEVICE=auto`, no GPU passthrough configured in `docker-compose.yml`) — see the GPU note in [DECISIONS.md](DECISIONS.md) if you want to try it with CUDA locally instead.

### Without Docker (local dev)

Requires Python 3.11+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.api.main:app --reload
```

Run the tests:

```bash
pytest
```

Tests always run against the mock adapters regardless of what's in your local `.env` (see `tests/conftest.py`) — they won't accidentally call a real model or burn API quota.

## Architecture, and why

Three layers, dependencies pointing one way only:

```
app/api/        HTTP routing, request/response models, validation
app/services/   orchestration and business logic
app/adapters/   provider and model integration (mock + real)
```

- `api/` is the only place allowed to know FastAPI exists — `UploadFile`, `HTTPException`, etc. never leak past it.
- `services/` is plain Python. It takes bytes in, returns plain dataclasses out. It has no idea whether the audio came over HTTP, and no idea whether the provider underneath it is a mock or a paid API.
- `adapters/` is the only place allowed to import a provider SDK (`faster_whisper`, `google.genai`, `mutagen`). Every adapter — mock or real — implements the same `Protocol` (`app/adapters/base.py`), so `services/` never has to special-case which one it's holding.

Which adapter actually runs is picked in `app/adapters/factory.py`, driven entirely by the typed `Settings` object in `app/config.py` (itself just env vars). Swapping mock for real is a config change, never a code change. There's a test (`tests/test_layer_separation.py`) that mechanically checks these import rules instead of just trusting everyone to remember them.

**Why this shape:** the point of the exercise, as I read it, is proving the boundaries hold up — not how much gets built. Keeping `services/` ignorant of both HTTP and SDKs is what makes it possible to unit-test the tricky logic (silence detection, non-lab-report handling, value normalisation) with plain stub objects instead of spinning up FastAPI or mocking a network call every time.

## Normalised value format

Lab values arrive as messy, inconsistent text. Here's what gets normalised and what doesn't (full rationale in `app/services/normalisation.py`):

- **Numeric value** → parsed to a real `float` only when it's unambiguously one point value:
  - `"12.5"` → `12.5`
  - `"12,500"` → `12500.0` (thousands separator stripped)
  - `"1.2 x 10^3"` → `1200.0` (scientific/multiplier notation expanded)
  - `"<0.5"`, `">100"`, `"0.8 - 1.2"` → **left exactly as the string it came in as.** A `<` or a range can't be collapsed into one float without quietly deciding what it means — that's a guess, not a normalisation, so it's not made. Every result still gets *a* value (per the brief's requirement), it just won't always be numeric.
- **Unit** → lowercased, whitespace-trimmed, then passed through a small alias table so equivalent spellings collapse together (`"gm/dl"`, `"Gm/dL"`, `"g/dl"` → all `"g/dl"`). Units not in the table are kept as-is rather than rejected — normalisation only ever applies to variants it can confidently map, not everything it doesn't recognize.
- **Date** → matched against a fixed list of common lab-report formats and returned as ISO `YYYY-MM-DD` on a confident hit. Ambiguous or unrecognised dates are returned unchanged.
- **`raw_line`** → never touched. It's always the exact text the provider returned for that row, regardless of what normalisation did or didn't manage to do with it.

## Test data

Everything lives under `testdata/`.

| File | What it is | Why |
|---|---|---|
| `harvard.wav` | Classic public-domain "Harvard sentences" English recording | Clean, well-known baseline — a sanity check that the happy path works before throwing anything harder at it |
| `wavs/ban_*.wav` (12 clips) | Bengali speech clips, filename pattern matches OpenSLR's Bengali TTS corpus (SLR37) speaker/utterance IDs | Bengali coverage, since the service has to handle both languages |
| `image.png` | A real "Popular Diagnostic Centre" lipid profile report, flat and well-lit | Clean baseline for the extraction endpoint |
| `image copy.png` | A real "Suma Diagnostic" hematology report, photographed on paper with natural glare and a slight skew | The brief specifically calls out angled, poorly-lit photos as the real-world case to handle — this is an actual example of one, not a synthetic approximation |
| `image copy 2.png` | A photo of a gloved hand holding a blood collection tube — not a lab report at all | Exercises the "handle documents that are not lab reports without producing garbage" requirement |
| `sterling-accuris-pathology-sample-report-unlocked.pdf` | A clean sample CBC report template | Reference source only — not fed to the endpoint directly (the API only accepts jpg/jpeg/png/webp, not PDF) |
| `fixtures/*.json` | Hand-written canned responses | What the mock adapters replay — not real provider output, just realistic-looking fixtures for the no-cost default path |

**Known gaps in the test data (disclosed, not fixed yet):**
- No written reference transcripts yet for `harvard.wav` or the Bengali clips, so transcription accuracy hasn't actually been measured against ground truth — it's on the list, just not done.
- No dedicated silence/ambient-noise-only clip exists yet to manually exercise the no-speech path end-to-end (the *logic* for it is unit-tested directly in `tests/test_transcription_service.py`, just not demonstrated with a real audio file).
- Twelve Bengali clips is probably more than this exercise needs — a handful, hand-picked for difficulty (accented, noisy, short), would tell you more than twelve similar ones.
- `image.png`, `image copy.png`, `image copy 2.png` are named by an OS copy-paste, not by content — functional, but not self-documenting from the filename alone (see the table above for what each one actually is).

## Known limitations

- **Gemini free-tier quota has been flaky during development** — at one point returning a `RESOURCE_EXHAUSTED` error with a quota limit of literally zero, which points at a key/project/region issue more than normal rate-limiting. Doesn't affect the graded default path (mocks only), but worth knowing before trying the real adapter. Details in [DECISIONS.md](DECISIONS.md).
- **Self-hosted Whisper doesn't currently run on GPU on newer NVIDIA hardware** (RTX 5080 / Blackwell) due to a CTranslate2 compatibility gap. It works correctly on CPU, just slower. Gemini is the default real transcription adapter instead — full story in [DECISIONS.md](DECISIONS.md).
- **Mock adapters always return the same fixture**, regardless of what's uploaded — they don't vary their response to simulate silence or a non-lab-report image. Those behaviors are guaranteed by the service layer instead (and tested there directly against stub providers), not by the mocks. See [DECISIONS.md](DECISIONS.md) for the reasoning.
- **Detected language for the Gemini transcription adapter falls back to the requested language** (or `"unknown"` for `auto`) rather than a real detected code, since Gemini's text response doesn't expose one the way Whisper's does.
- **Gemini's extraction OCR/parsing hasn't been benchmarked for accuracy** against the harder test images (`image copy.png`) yet — it runs, but how well it does on glare/skew specifically hasn't been formally checked.
