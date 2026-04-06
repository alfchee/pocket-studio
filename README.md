# 🎙️ Pocket Studio — Local TTS Voice Studio

**Private · Self-Hosted · Multilingual Voice Cloning & Text-to-Speech**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## ✨ What is Pocket Studio?

Pocket Studio is a **compact, self-contained voice studio** that runs entirely on your own hardware. It gives podcasters, content creators, and developers the ability to:

- **Clone any voice** from a short 5–10 second audio clip — zero training required.
- **Generate natural speech** in 17 languages from plain text, with fine-grained control over speed and style.
- **Stay 100% private** — all processing happens locally; no data ever leaves your network.

No cloud accounts. No API keys. No subscriptions.

---

## 🤖 TTS Engines

Pocket Studio supports three TTS engines selectable via Docker Compose profiles. You can also **download** the images with the models already included from Docker Hub.

| Engine | Profile | Docker Hub Image | Description |
|---|---|---|---|
| **XTTS-v2** | `xtts-v2` | [alfchee/pocket-studio-xtts-v2](https://hub.docker.com/r/alfchee/pocket-studio-xtts-v2) | Coqui XTTS-v2 — 17 languages, high-quality voice cloning |
| **Pocket TTS** | `pocket-tts` | [alfchee/pocket-studio-pocket-tts](https://hub.docker.com/r/alfchee/pocket-studio-qwen3-tts) | Lightweight English-only TTS |
| **Qwen3-TTS** | `qwen3-tts` | [alfchee/pocket-studio-qwen3-tts](https://hub.docker.com/r/alfchee/pocket-studio-pocket-tts) | Qwen3-TTS — multilingual, CPU-friendly, voice cloning with ICL mode |

---

## 🌍 Multilingual Support

### XTTS-v2
Powered by [Coqui's XTTS-v2](https://huggingface.co/coqui/XTTS-v2), supporting 17 languages:

`English` `Spanish` `French` `German` `Italian` `Portuguese` `Polish` `Turkish` `Russian`
`Dutch` `Czech` `Arabic` `Chinese` `Japanese` `Hungarian` `Korean` `Hindi`

### Qwen3-TTS
Powered by [Qwen/Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base), a compact multilingual model that runs on CPU. Supports two synthesis modes:

- **ICL mode** (higher fidelity): provide `ref_text` — the exact transcription of your reference audio clip.
- **X-vector mode** (fallback): no transcription needed; uses speaker embeddings directly.

---

## 🚀 Quick Start — Pre-built Docker Hub Images

The fastest way to get running — no build step required:

```bash
git clone https://github.com/alfchee/pocket-studio.git
cd pocket-studio

# XTTS-v2 (multilingual, high quality)
docker compose --profile xtts-v2 pull
docker compose --profile xtts-v2 up

# Pocket TTS (lightweight, English-only)
docker compose --profile pocket-tts pull
docker compose --profile pocket-tts up

# Qwen3-TTS (multilingual, CPU-friendly)
docker compose --profile qwen3-tts pull
docker compose --profile qwen3-tts up
```

Open **[http://localhost:8000](http://localhost:8000)** (or the port set by `PORT`) and you're ready.

---

## 🔨 Build Your Own Images

If you prefer to build locally (e.g., to include a custom HuggingFace model or modify the backend):

```bash
# Build XTTS-v2 image
docker compose --profile xtts-v2 build

# Build Pocket TTS image
docker compose --profile pocket-tts build

# Build Qwen3-TTS image (model is baked into the image at build time — allow ~5–10 min)
docker compose --profile qwen3-tts build

# Optional: pass a HuggingFace token if you need gated model access
HF_TOKEN=your_token docker compose --profile qwen3-tts build
```

After building, start with:
```bash
docker compose --profile <profile> up
```

Verify the Qwen3-TTS model was baked into the image:
```bash
docker exec pocket-studio find /app/models -name "*.safetensors" | head -5
```

---

## 💡 How It Works

### 1 · Clone a Voice
Upload a clean 5–10 second `.wav` or `.mp3` of the voice you want to clone. The system extracts a voice embedding and stores it locally.

For **Qwen3-TTS ICL mode** (higher fidelity), also provide the exact transcription of your reference audio:

```bash
curl -X POST http://localhost:8000/api/clone \
  -F "file=@reference.wav" \
  -F "name=my-voice" \
  -F "ref_text=The exact words spoken in the reference audio."
```

### 2 · Write Your Script
Paste any text — from a single sentence to a full podcast segment. Choose your cloned voice and target language.

### 3 · Generate & Download
Tweak **Speed** and **Temperature** (style/consistency trade-off), hit **Generate**, and download a high-quality 24 kHz WAV.

---

## 🧩 Architecture

| Layer | Technology |
|---|---|
| **UI** | React + TypeScript, served as static files |
| **API** | FastAPI (Python 3.11+) |
| **TTS Engine** | Pluggable: `xtts_v2` · `pocket_tts` · `qwen3_tts` · `dummy` |
| **Runtime** | Docker + Docker Compose |

### Backend Package Structure

```
backend/
├── config/           # Settings management (Pydantic)
├── schemas/         # Request/response validation
├── services/        # Business logic (audio, voice)
├── api/            # FastAPI routes
└── utils/          # Utilities (logging)
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health & engine info |
| `GET` | `/api/voices` | List available (cloned + built-in) voices |
| `POST` | `/api/clone` | Upload reference audio → get a `voice_id` |
| `POST` | `/api/generate` | Synthesize text → WAV audio |
| `POST` | `/api/generate_stream` | Synthesize text → streaming MP3 |

**`/api/clone` optional field for Qwen3-TTS:**

| Field | Type | Description |
|---|---|---|
| `ref_text` | `string` (optional) | Transcription of the reference audio — enables higher-quality ICL mode |

---

## 🛠️ Configuration

All settings are environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `TTS_ENGINE` | `dummy` | TTS engine: `xtts_v2`, `pocket_tts`, `qwen3_tts`, `dummy` |
| `VOICES_DIR` | `./voices` | Directory for voice embeddings |
| `OUTPUTS_DIR` | `./outputs` | Directory for generated audio |
| `MAX_AUDIO_UPLOAD_SIZE_MB` | `5` | Max upload size for reference audio |
| `MAX_TEXT_LENGTH` | `5000` | Max characters per generation request |
| `MIN_REF_SECONDS` / `MAX_REF_SECONDS` | `5.0` / `10.0` | Valid range for reference audio duration |
| `MIN_SPEED` / `MAX_SPEED` | `0.5` / `2.0` | Speed multiplier range |
| `MIN_TEMPERATURE` / `MAX_TEMPERATURE` | `0.0` / `1.5` | Temperature/style range |
| `COQUI_TOS_AGREED` | `0` | Required for XTTS-v2 (`1` = accepted CPML terms) |
| `HF_TOKEN` | _(empty)_ | HuggingFace token (only needed for gated models) |
| `QWEN3_TTS_MODEL` | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | Qwen3-TTS model ID |
| `HF_HOME` | `/app/models` | HuggingFace cache root inside container |
| `PORT` | `8000` | Host port to expose the service on |

---

## 🖥️ Local Development (Qwen3-TTS)

For local development without Docker:

```bash
# Create venv and install dependencies (Python 3.11 recommended)
chmod +x setup-dev.sh && ./setup-dev.sh

# Activate venv
source .venv/bin/activate

# Download the model locally (~1–2 GB)
HF_HOME=./models python docker/download_model.py

# Run the backend
TTS_ENGINE=qwen3_tts HF_HOME=./models uvicorn backend.main:app --reload
```

> **Note:** `sox` is required by `librosa` and must be installed at the OS level:
> ```bash
> sudo apt-get install sox libsox-fmt-all   # Debian/Ubuntu
> brew install sox                           # macOS
> ```

---

## 🧪 Tests

```bash
# Backend (58 tests, 71% coverage)
cd backend
python -m pytest tests/ -v --cov=backend

# Frontend
cd frontend && npm test
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [docs/API.md](docs/API.md) | Complete API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development guide |
| [docs/README.md](docs/README.md) | Documentation index |

---

## ⚠️ Ethics & Responsible Use

- **Only clone voices you have explicit consent to use.**
- Cloned voices must be used lawfully and ethically at all times.
- Reference audio quality directly affects output quality — use clean, uncompressed audio where possible.
- XTTS-v2 / Coqui TTS are licensed under CPML; ensure your use case complies with the license terms.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request. For major changes, please discuss them first.

---

## 📄 License

**Apache License 2.0** — see [LICENSE](LICENSE) for details.

This license allows broad use including commercial applications, requires attribution, and provides explicit patent grants — making it ideal for a project that integrates both open-source and CC-licensed ML models.
