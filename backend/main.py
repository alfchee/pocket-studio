import io
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator

from tts_engine import TTSEngine, create_engine


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_path(name: str, default: str) -> Path:
    value = os.getenv(name)
    if value is None or value == "":
        value = default
    return Path(value)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str | None = None
    speaker_wav_path: str | None = None
    language: str | None = None
    speed: float | None = None
    temperature: float | None = None

    @model_validator(mode="after")
    def _validate_voice_source(self) -> "GenerateRequest":
        voice_id = (self.voice_id or "").strip()
        speaker_wav_path = (self.speaker_wav_path or "").strip()
        if voice_id == "" and speaker_wav_path == "":
            raise ValueError("Either voice_id or speaker_wav_path is required")
        self.voice_id = voice_id or None
        self.speaker_wav_path = speaker_wav_path or None
        self.language = (self.language or "").strip() or None
        return self


def _normalize_audio_to_wav_24k_mono(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-f",
        "wav",
        str(output_path),
    ]
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="ignore"))


def create_app() -> FastAPI:
    voices_dir = _env_path("VOICES_DIR", "./voices")
    engine_name = (os.getenv("TTS_ENGINE") or "dummy").strip().lower()
    max_audio_mb = _env_int("MAX_AUDIO_UPLOAD_SIZE_MB", 5)
    max_text_len = _env_int("MAX_TEXT_LENGTH", 5000)
    min_ref_s = _env_float("MIN_REF_SECONDS", 5.0)
    max_ref_s = _env_float("MAX_REF_SECONDS", 10.0)

    min_speed = _env_float("MIN_SPEED", 0.5)
    max_speed = _env_float("MAX_SPEED", 2.0)
    min_temp = _env_float("MIN_TEMPERATURE", 0.0)
    max_temp = _env_float("MAX_TEMPERATURE", 1.5)

    voices_dir.mkdir(parents=True, exist_ok=True)

    try:
        engine: TTSEngine = create_engine(engine_name)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize TTS engine '{engine_name}': {str(e)}")

    app = FastAPI(title="Pocket Studio API")

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "engine": getattr(engine, "name", engine_name),
            "sample_rate": getattr(engine, "sample_rate", None),
        }

    @app.get("/api/voices")
    def list_voices() -> list[dict]:
        results: list[dict] = []

        for v in getattr(engine, "builtin_voices", []):
            results.append({"voice_id": v, "name": v, "builtin": True})

        if not voices_dir.exists():
            return results
        for entry in sorted(voices_dir.iterdir()):
            if not entry.is_dir():
                continue
            meta_path = entry / "meta.json"
            name = entry.name
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    name = meta.get("name") or name
                except Exception:
                    name = name
            results.append({"voice_id": entry.name, "name": name, "builtin": False})
        return results

    @app.post("/api/clone")
    async def clone_voice(
        file: UploadFile = File(...),
        name: str | None = Form(default=None),
    ) -> JSONResponse:
        if file.filename is None or file.filename == "":
            raise HTTPException(status_code=400, detail="Missing filename")

        raw = await file.read()
        if len(raw) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(raw) > max_audio_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")

        voice_id = str(uuid.uuid4())
        voice_path = voices_dir / voice_id
        voice_path.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            in_path = tmp_dir / "input"
            in_path.write_bytes(raw)
            ref_path = voice_path / "reference.wav"
            try:
                _normalize_audio_to_wav_24k_mono(in_path, ref_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Audio decode failed: {str(e)}")

        try:
            import wave

            with wave.open(str(ref_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
            duration_s = (frames / rate) if rate else 0.0
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid WAV after normalization: {str(e)}")

        if duration_s < min_ref_s or duration_s > max_ref_s:
            raise HTTPException(
                status_code=400,
                detail=f"Reference audio must be between {min_ref_s:.1f}s and {max_ref_s:.1f}s (got {duration_s:.2f}s)",
            )

        embedding_path = voice_path / "voice.safetensors"
        try:
            engine.clone_to_safetensors(ref_path, embedding_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Voice embedding failed: {str(e)}")

        meta = {
            "voice_id": voice_id,
            "name": (name or "").strip() or voice_id,
            "source_filename": file.filename,
        }
        (voice_path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        return JSONResponse({"voice_id": voice_id, "name": meta["name"]})

    @app.post("/api/generate")
    def generate_audio(payload: GenerateRequest) -> StreamingResponse:
        text = payload.text.strip()
        if text == "":
            raise HTTPException(status_code=400, detail="Empty text")
        if len(text) > max_text_len:
            raise HTTPException(status_code=413, detail="Text too long")

        language = (payload.language or "es").strip()
        supported_languages = getattr(engine, "supported_languages", None)
        if supported_languages:
            if language not in supported_languages:
                raise HTTPException(status_code=400, detail="Unsupported language")

        def _resolve_speaker_wav_path(raw_path: str) -> Path:
            p = Path(raw_path)
            if not p.is_absolute():
                p = voices_dir / p
            try:
                resolved = p.resolve(strict=False)
            except Exception:
                resolved = p
            try:
                voices_root = voices_dir.resolve(strict=False)
                if voices_root not in resolved.parents and resolved != voices_root:
                    raise HTTPException(status_code=400, detail="speaker_wav_path must be under VOICES_DIR")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid speaker_wav_path")
            if not resolved.exists() or not resolved.is_file():
                raise HTTPException(status_code=404, detail="speaker_wav_path not found")
            return resolved

        voice_state = None
        if payload.speaker_wav_path is not None:
            speaker_path = _resolve_speaker_wav_path(payload.speaker_wav_path)
            try:
                voice_state = engine.load_voice_state(speaker_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid speaker_wav_path: {str(e)}")
        elif payload.voice_id is not None:
            voice_path = voices_dir / payload.voice_id
            if voice_path.exists() and voice_path.is_dir():
                safetensors_path = voice_path / "voice.safetensors"
                reference_path = voice_path / "reference.wav"
                if safetensors_path.exists():
                    voice_state = engine.load_voice_state(safetensors_path)
                elif reference_path.exists():
                    voice_state = engine.load_voice_state(reference_path)
            elif payload.voice_id in getattr(engine, "builtin_voices", []):
                voice_state = engine.load_voice_state(payload.voice_id)

        if voice_state is None:
            raise HTTPException(status_code=404, detail="Unknown voice")

        if isinstance(voice_state, dict):
            voice_state = {**voice_state, "language": language}

        speed = payload.speed
        if speed is not None:
            if speed < min_speed:
                speed = min_speed
            elif speed > max_speed:
                speed = max_speed

        temperature = payload.temperature
        if temperature is not None:
            if temperature < min_temp:
                temperature = min_temp
            elif temperature > max_temp:
                temperature = max_temp

        try:
            result = engine.generate_wav(voice_state, text, speed, temperature)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

        wav_bytes = result.wav_bytes
        headers = {"Content-Disposition": "attachment; filename=output.wav"}
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav", headers=headers)

    return app


app = create_app()
