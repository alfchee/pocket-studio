# Pocket Studio (Local TTS Voice Studio)

Dockerized, self-hosted voice studio for local voice cloning + text-to-speech.

## Quick Start (Dummy engine)

This mode runs fully offline and is fast to build. It produces valid WAV output but does not synthesize real speech.

1. Copy env file:
   - `cp .env.example .env`
2. Start the stack:
   - `docker compose up --build`
3. Open the UI:
   - `http://localhost:3000`

## Real TTS (Pocket TTS engine)

Pocket TTS requires heavier dependencies (PyTorch). The Docker build can optionally install them.

1. Copy env file:
   - `cp .env.example .env`
2. Edit `.env`:
   - `TTS_ENGINE=pocket_tts`
   - `INSTALL_TTS_DEPS=1`
3. Build and run:
   - `docker compose up --build`

Artifacts and caches:
- Cloned voices persist in `./voices`
- Model/cache persists in `./models` (HuggingFace cache at `./models/hf`)
- Generated outputs can be persisted in `./outputs` (optional for future use)

## UI Flow

1. **Clone voice**: upload a clean 5–10s reference audio (`.wav` or `.mp3`).
2. **Generate**: paste text, select voice, tweak speed/temperature, generate WAV.
3. **Preview/Download**: play audio in the browser or download `.wav`.

## API

Backend base URL: `http://localhost:8000`

- `GET /api/health`
- `GET /api/voices`
- `POST /api/clone` (multipart: `file`, optional `name`)
- `POST /api/generate` (json: `text`, `voice_id`, optional `speed`, `temperature`)

## Configuration

All configuration is via environment variables (see `.env.example`):
- `MAX_AUDIO_UPLOAD_SIZE_MB`
- `MAX_TEXT_LENGTH`
- `MIN_REF_SECONDS`, `MAX_REF_SECONDS`
- `MIN_SPEED`, `MAX_SPEED`
- `MIN_TEMPERATURE`, `MAX_TEMPERATURE`

## Tests

Backend tests (inside Docker):
- `docker compose run --rm backend pytest -q`

## Notes

- Voice cloning should only be used with explicit consent and lawful permission.
- Reference audio quality matters: background noise and compression artifacts will carry into outputs.

