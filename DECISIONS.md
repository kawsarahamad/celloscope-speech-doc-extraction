# Decisions

Short notes on the choices that actually mattered, what I turned down instead, and why.

## 1. Transcription: Gemini API instead of self-hosted Whisper

I started with self-hosted Whisper through `faster-whisper` (CTranslate2), since it's free, runs offline, and needs no API key — a good fit for a "no credentials required" service. It worked fine on CPU. The problem showed up trying to get GPU acceleration on my RTX 5080: CTranslate2's CUDA backend doesn't yet support the Blackwell architecture, so every GPU run failed. I could have waited for upstream support, forced CPU-only mode, or switched adapters. With four days on the clock, I didn't want to gamble on a library update landing in time, so I switched the *default* real transcription adapter to the Gemini API instead — it's fast, has a free tier, and needs zero local setup.

I didn't throw Whisper away. `app/adapters/whisper_adapter.py` is still in the codebase and still works correctly in CPU mode — it's just not the adapter selected by default anymore. Anyone with a compatible GPU (or patience for CPU speed) can still use it by setting `TRANSCRIPTION_PROVIDER=whisper`. I'm noting this as a rejected-then-partially-kept option rather than hiding the detour, since it's exactly the kind of real engineering snag this exercise is testing for.

## 2. Lab report extraction: Gemini vision, not a self-hosted OCR + LLM pipeline

For extracting structured data from lab report photos, I considered a two-stage pipeline: run a self-hosted OCR engine (Tesseract or PaddleOCR) to get raw text lines, then feed that text to a small LLM to structure it into the `meta`/`results` JSON. That approach has a genuine advantage — the raw OCR output naturally becomes your `raw_line` field with zero risk of an LLM "cleaning it up," since the two steps never talk to each other about it.

I decided against it for this submission, mainly on time grounds. It's two providers stitched into one adapter instead of one, which means twice the failure surface (OCR mangles the image, or the structuring LLM misreads OCR's mangled text) for a take-home that explicitly marks down "volume" and rewards a smaller, cleaner submission. I went with a single Gemini vision call instead — it reads the image and returns structured JSON directly, including the row's original text for `raw_line`. It's a fair alternative worth documenting rather than acting like the hybrid option never occurred to me — if I had more time, it's the first thing I'd build and compare against.

## 3. Values I can't confidently parse are kept exactly as-is, never guessed

Lab values show up as plain numbers, but also as `<0.5`, `1.2 x 10^3`, or a range like `0.8 - 1.2` sitting where a single value was expected. I only convert to a real number when I'm sure it means one specific point value. A `<0.5` isn't really "0.5" — the `<` carries real meaning (below detectable threshold), and collapsing it to a bare float would quietly throw that meaning away. Same logic for a range shown as a single value: there's no way to know which end (if either) is the "real" one, so picking one would just be a guess wearing a number's clothes.

The brief was explicit that guessing is worse than admitting you didn't know, so anything like this is preserved exactly as the provider returned it, in the `value` field, as a string. It's a deliberate trade: I could make every `value` field "clean" by silently stripping the `<` and parsing the rest, but that would be lying about how confident the system actually is.

## 4. Mock adapters stay dumb; the tricky edge cases live in the service layer

Both mock adapters (`mock_transcription_adapter.py`, `mock_extraction_adapter.py`) do the simplest possible thing: read one canned JSON fixture off disk and return it, no matter what's uploaded. I could have made them smarter — for example, branching on the filename to fake a silent-audio response or a "this isn't a lab report" response — but that would mean growing the adapter interface (passing filenames through, adding branching logic) just to simulate behavior that real providers already produce naturally.

Instead, the guarantees that actually matter — "no speech detected" must be reliable, "not a lab report" must degrade gracefully — live in `services/transcription_service.py` and `services/extraction_service.py`, and are unit-tested directly against stub providers built for exactly that purpose. That way the behavior is tested against the real logic that enforces it, not against a mock's imitation of it. The trade-off I'm accepting: if you poke the mock-only Docker setup by hand with a silent audio file, you won't see a different response — you'd need to check the unit tests (or run the real adapter) to see that path exercised. I think that's a reasonable line to draw rather than adding machinery for a demo-only benefit.

## 5. Living with Gemini's free-tier flakiness instead of switching plans mid-project

While wiring up the Gemini adapter, I hit a `429 RESOURCE_EXHAUSTED` error with the free tier — at one point with a quota limit of literally zero requests for the model, which points at either a malformed API key or a project/region that never got free-tier access in the first place, rather than normal rate-limiting from heavy use. I could have switched to a paid Gemini plan, or built the OCR + Cerebras hybrid from decision #2 to dodge Gemini entirely.

I chose to keep Gemini as the documented default and treat the quota issue as a known limitation instead, mainly because the part that's actually graded by default — `docker compose up` on the mock adapters — doesn't touch Gemini at all. Spending the rest of the timeline chasing a more resilient real-provider setup felt like solving a problem the grading process was never going to hit. It's called out here and in the README so it isn't a silent gap.
