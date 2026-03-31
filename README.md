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

## 🌍 Multilingual Power — Powered by XTTS-v2

Pocket Studio ships with [Coqui's XTTS-v2](https://huggingface.co/coqui/XTTS-v2), a state-of-the-art multilingual TTS model supporting:

`English` `Spanish` `French` `German` `Italian` `Portuguese` `Polish` `Turkish` `Russian`
`Dutch` `Czech` `Arabic` `Chinese` `Japanese` `Hungarian` `Korean` `Hindi`

Select the target language in the UI before generating — XTTS uses it to guide pronunciation, prosody, and text processing, producing noticeably better results than leaving it unspecified.

---

## 🚀 Get Started (Zero-Config)

```bash
git clone https://github.com/YOUR_HANDLE/pocket-studio.git
cd pocket-studio

# Start immediately (dummy engine — fast build, no heavy deps)
docker compose up --build
```

Open **[http://localhost:3000](http://localhost:3000)** and you're ready.

---

## 🎯 One-Click Real TTS (XTTS-v2)

Want real voice synthesis instead of the dummy engine? Set two environment variables:

```bash
# .env
TTS_ENGINE=xtts_v2
INSTALL_TTS_DEPS=1
COQUI_TOS_AGREED=1   # Required: you agree to CPML terms for XTTS-v2
```

```bash
docker compose up --build
```

> ⚠️ **XTTS-v2 licensing**: XTTS-v2 is distributed under Coqui's [CPML](https://coqui.ai/cpml) (non-commercial license). Set `COQUI_TOS_AGREED=1` only if you have a commercial license or agree to CPML terms. See [Coqui's licensing page](https://coqui.ai/cpml) for details.

---

## 💡 How It Works

### 1 · Clone a Voice
Upload a clean 5–10 second `.wav` or `.mp3` of the voice you want to clone. The system extracts a voice embedding and stores it locally.

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
| **TTS Engine** | Pluggable: `xtts_v2` · `pocket_tts` · `dummy` |
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

### Switching Engines

Pocket Studio's engine layer is pluggable via the `TTS_ENGINE` environment variable:

| Value | Description |
|---|---|
| `xtts_v2` | Coqui XTTS-v2 — multilingual, voice cloning (default with deps installed) |
| `pocket_tts` | Pocket TTS — English-only, lightweight |
| `dummy` | Silent placeholder WAV — fast for UI development |

---

## 🛠️ Configuration

All settings are environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `TTS_ENGINE` | `dummy` | TTS engine to use (`xtts_v2`, `pocket_tts`, `dummy`) |
| `VOICES_DIR` | `./voices` | Directory for voice embeddings |
| `OUTPUTS_DIR` | `./outputs` | Directory for generated audio |
| `MAX_AUDIO_UPLOAD_SIZE_MB` | `5` | Max upload size for reference audio |
| `MAX_TEXT_LENGTH` | `5000` | Max characters per generation request |
| `MIN_REF_SECONDS` / `MAX_REF_SECONDS` | `5.0` / `10.0` | Valid range for reference audio duration |
| `MIN_SPEED` / `MAX_SPEED` | `0.5` / `2.0` | Speed multiplier range |
| `MIN_TEMPERATURE` / `MAX_TEMPERATURE` | `0.0` / `1.5` | Temperature/style range |
| `COQUI_TOS_AGREED` | `0` | Required for XTTS-v2 (`1` = accepted CPML terms) |

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
