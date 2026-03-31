# API Reference

Complete reference documentation for the Pocket Studio REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication is required for local deployment.

## Endpoints

---

### Health Check

Check if the service is running and get engine information.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "ok",
  "engine": "dummy",
  "sample_rate": 24000
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Health status, always "ok" when healthy |
| `engine` | string | Name of the active TTS engine |
| `sample_rate` | integer | Output audio sample rate in Hz |

---

### List Voices

Get all available voices (both cloned and built-in).

**Endpoint:** `GET /api/voices`

**Response:**
```json
[
  {
    "voice_id": "my-cloned-voice",
    "name": "My Voice",
    "builtin": false
  },
  {
    "voice_id": "default",
    "name": "default",
    "builtin": true
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `voice_id` | string | Unique identifier for the voice |
| `name` | string | Human-readable name |
| `builtin` | boolean | Whether this is a built-in voice |

---

### Clone Voice

Upload reference audio to create a new voice clone.

**Endpoint:** `POST /api/clone`

**Content-Type:** `multipart/form-data`

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Reference audio file (WAV, MP3) |
| `name` | string | No | Custom name for the voice |

**Request Example:**
```bash
curl -X POST http://localhost:8000/api/clone \
  -F "file=@reference.wav" \
  -F "name=My Voice"
```

**Response:**
```json
{
  "voice_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Voice"
}
```

**Error Responses:**

| Status | Detail |
|--------|--------|
| 400 | Empty file |
| 400 | File too large |
| 400 | Audio decode failed |
| 400 | Reference audio must be between 5.0s and 10.0s |

---

### Generate Audio

Synthesize speech from text (non-streaming).

**Endpoint:** `POST /api/generate`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "text": "Hello, world!",
  "voice_id": "my-voice",
  "language": "en",
  "speed": 1.0,
  "temperature": 0.8
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | Text to synthesize |
| `voice_id` | string | Yes* | - | ID of cloned voice |
| `speaker_wav_path` | string | Yes* | - | Path to reference audio |
| `language` | string | No | "es" | Target language code |
| `speed` | number | No | 1.0 | Speech speed (0.5-2.0) |
| `temperature` | number | No | 0.8 | Generation temperature (0.0-1.5) |

> \* Either `voice_id` or `speaker_wav_path` is required.

**Response:** `audio/wav` (24kHz mono WAV)

**Error Responses:**

| Status | Detail |
|--------|--------|
| 400 | Empty text |
| 400 | Either voice_id or speaker_wav_path is required |
| 400 | Unsupported language |
| 404 | Unknown voice |
| 413 | Text too long |
| 500 | TTS generation failed |

---

### Generate Audio Stream

Synthesize speech from text with streaming response.

**Endpoint:** `POST /api/generate_stream`

**Content-Type:** `application/json`

**Request Body:** Same as `/api/generate`

**Response:** `audio/mpeg` (streaming MP3)

This endpoint provides lower latency by streaming audio chunks as they are generated. Useful for longer texts.

---

## Language Codes

Supported language codes:

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `it` | Italian |
| `pt` | Portuguese |
| `pl` | Polish |
| `tr` | Turkish |
| `ru` | Russian |
| `nl` | Dutch |
| `cs` | Czech |
| `ar` | Arabic |
| `zh` | Chinese |
| `ja` | Japanese |
| `hu` | Hungarian |
| `ko` | Korean |
| `hi` | Hindi |

---

## TTS Engines

### Dummy Engine

The `dummy` engine is a placeholder that returns generated WAV headers without actual speech synthesis. Use for testing the API or UI without downloading large models.

### XTTS-v2 Engine

The `xtts_v2` engine uses Coqui's XTTS-v2 for high-quality multilingual voice synthesis.

**Configuration:**
```bash
TTS_ENGINE=xtts_v2
COQUI_TOS_AGREED=1   # Required for XTTS-v2
```

### Qwen3-TTS Engine

The `qwen3_tts` engine uses Qwen's TTS model.

**Configuration:**
```bash
TTS_ENGINE=qwen3_tts
QWEN3_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-Base
```

---

## Rate Limits

No rate limits are enforced for local deployments.

---

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```