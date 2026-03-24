# PRD: Pocket Studio — "Podcast-in-a-Box" (Local & Private)

## 1. Product Summary

Pocket Studio is a compact, self-hosted voice studio that enables content creators (podcasters) to generate high-quality synthetic voice and perform zero-shot voice cloning entirely locally. It uses a pluggable TTS engine (initially Pocket TTS 100M, later XTTS-v2) to ensure processing occurs in real-time even without a dedicated GPU.

## 2. Goals

1. **Total Privacy** — Voice data and scripts never leave the local network.
2. **Low Friction** — A single interface where you paste text and get audio.
3. **Portability** — Docker Compose deployment to avoid dependency hell on Windows/Intel.
4. **Multilingual** — Support 17 languages via XTTS-v2, with explicit language selection in the UI.

## 3. User Persona

**Primary:** Podcaster with an Intel i7 machine, looking to streamline post-production or create narrated segments without re-recording every take.

## 4. Functional Requirements

- **(MVP) RF01: Zero-Shot Voice Cloning**
  The system allows uploading a reference audio file (`.wav`/`.mp3`) of 5–10 seconds. The system extracts a voice embedding (`.safetensors` file) for reuse.

- **RF02: Text-to-Speech Synthesis**
  - Users can input plain text or long scripts.
  - Option to select between predefined (built-in) voices or previously cloned voices.
  - Control over Speed and Temperature parameters.

- **RF03: Audio Management**
  - Integrated player to preview results in-browser.
  - Download button for the final file in high-quality 24 kHz WAV format.

## 5. Technical Architecture

### Technology Stack

| Layer | Technology |
|---|---|
| **Model Core** | Pluggable: XTTS-v2 (primary) · Pocket TTS · Dummy |
| **Backend** | FastAPI (Python 3.11+) |
| **Frontend** | React (TypeScript), served by Nginx |
| **Orchestration** | Docker + Docker Compose |
| **CPU Optimization** | torch (CPU mode), onnxruntime-openvino, AVX-512 on Intel 12th Gen |

### Container Structure

- **Container A (Backend):** Exposes REST endpoints (`/clone`, `/generate`, `/voices`).
- **Container B (Frontend):** Visual UI served by Nginx, consuming the API.
- **Volumes:** Shared `./voices` folder to persist cloned voices.

## 6. API Design

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/clone` | Upload reference audio → returns a `voice_id`. |
| `POST` | `/api/generate` | Receive `text` + `voice_id` + `language` → streaming WAV. |
| `GET` | `/api/voices` | List available voices (built-in + cloned). |
| `GET` | `/api/health` | Service health, engine name, and sample rate. |

### `/api/generate` Request Schema

```json
{
  "text": "string (required, 1–5000 chars)",
  "voice_id": "string (optional, for cloned/built-in voices)",
  "speaker_wav_path": "string (optional, absolute or relative path under VOICES_DIR)",
  "language": "string (optional, ISO code, e.g. 'es', 'en'; defaults to 'es')",
  "speed": "float (optional, 0.5–2.0, default 1.0)",
  "temperature": "float (optional, 0.0–1.5, default 0.7)"
}
```

> **Note:** `voice_id` and `speaker_wav_path` are mutually exclusive. If `voice_id` is provided the system resolves the reference audio from the stored voice directory; `speaker_wav_path` allows direct reference to an audio file.

## 7. Performance Requirements (Intel i7 12th Gen)

- **Latency (TTFB):** Audio generation must start in under 300 ms.
- **Real-Time Factor (RTF):** Must be below 0.5 (generate 1 minute of audio in under 30 seconds).
- **CPU Usage:** Must not exceed 4 CPU cores.
- **Startup:** Backend must start without errors and pass the healthcheck when `TTS_ENGINE=xtts_v2` is set.

## 8. Implemented Features (Phase 1–8)

### Backend

- ✅ REST API with FastAPI: `/api/clone`, `/api/generate`, `/api/voices`, `/api/health`.
- ✅ Audio normalization via ffmpeg (24 kHz mono WAV) on upload.
- ✅ Duration validation for reference audio (5–10 seconds configurable).
- ✅ `TTSEngine` abstraction layer supporting multiple backends.
- ✅ Three engine implementations:
  - `dummy` — silent placeholder WAV (fast for UI dev).
  - `pocket_tts` — Pocket TTS 100M, English-only.
  - `xtts_v2` — Coqui XTTS-v2, multilingual (17 languages), lazy-loaded.
- ✅ Language parameter on `/api/generate` with server-side validation against engine's supported languages.
- ✅ `speaker_wav_path` parameter on `/api/generate` (restricted to `VOICES_DIR` subtree).
- ✅ Speed and Temperature parameters forwarded to engine.
- ✅ Lazy model loading for XTTS (avoids blocking startup during first generation).
- ✅ `COQUI_TOS_AGREED` env var to accept CPML non-interactively.
- ✅ `transformers` pinned to `<5` to avoid import errors with Coqui TTS.
- ✅ CPU-only PyTorch via `--index-url https://download.pytorch.org/whl/cpu`.
- ✅ Build-time import check to fail fast on dependency incompatibilities.

### Frontend

- ✅ Voice cloning UI (file upload, name, duration validation feedback).
- ✅ TTS generation UI (text area, voice selector, language selector, speed + temperature sliders).
- ✅ Audio preview player and WAV download.
- ✅ API status indicator (online/offline) with polling.
- ✅ Language selector with all 17 XTTS languages (defaults to Spanish).

### Infrastructure

- ✅ Docker Compose orchestration.
- ✅ `python:3.11-slim` base images with `libsndfile1`, `ffmpeg`, `curl`.
- ✅ Healthchecks on both containers.
- ✅ `OMP_NUM_THREADS` and `MKL_NUM_THREADS` tuned for 4-core i7.
- ✅ `./voices`, `./models`, `./outputs` volumes.
- ✅ `.env`-based configuration (no hardcoded values).
- ✅ Apache 2.0 license file.
- ✅ `.gitignore` covering Python, Node, Docker, IDE, and OS artifacts.

## 9. Acceptance Criteria (Definition of Done)

For each release, the following must be true:

- ✅ Backend starts and passes healthcheck with `TTS_ENGINE=xtts_v2` and `INSTALL_TTS_DEPS=1`.
- ✅ `/api/generate` returns a valid WAV file (24 kHz, > 44 bytes) for a known `voice_id`.
- ✅ The generated voice mimics the timbre of the uploaded reference audio.
- ✅ Generation time does not exceed a 2:1 ratio (e.g., 10 seconds of audio in ≤ 20 seconds of CPU time).
- ✅ The container starts without detecting missing CUDA/GPU errors.
- ✅ All 4 pytest tests pass.
- ✅ Frontend builds without errors and all vitest tests pass.
- ✅ No error or warning in the browser console on load.

## 10. Future Roadmap

- **v1.1 — RSS Integration:** Upload generated audio directly to podcast platforms via RSS.
- **v1.2 — Two-Voice Dialogues:** Support automatic dialogue between two distinct cloned voices (interview simulation).
- **v1.3 — Automatic Audio Cleanup:** Apply a denoiser to reference audio before cloning to improve output quality.
- **v1.4 — Streaming TTS:** Implement chunked/streaming audio output to reduce perceived latency.
- **v1.5 — Batch Generation:** Allow scheduling or queueing long scripts split into sections.
