import io
import json
import os
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_path(name: str, default: str) -> Path:
    value = os.getenv(name)
    if value is None or value == "":
        value = default
    return Path(value)


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str = Field(min_length=1)
    speed: float | None = None
    temperature: float | None = None


def _write_test_wav(duration_s: float = 1.0, sample_rate: int = 24000) -> bytes:
    frames = int(duration_s * sample_rate)
    pcm = bytearray()
    for _ in range(frames):
        pcm.extend((0).to_bytes(2, byteorder="little", signed=True))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm))
    return buf.getvalue()


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
    voices_dir = _env_path("VOICES_DIR", "/app/voices")
    max_audio_mb = _env_int("MAX_AUDIO_UPLOAD_SIZE_MB", 5)
    max_text_len = _env_int("MAX_TEXT_LENGTH", 5000)

    voices_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Pocket Studio API")

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/voices")
    def list_voices() -> list[dict]:
        results: list[dict] = []
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
            results.append({"voice_id": entry.name, "name": name})
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

        embedding_path = voice_path / "voice.safetensors"
        embedding_path.write_bytes(b"PLACEHOLDER")

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

        voice_path = voices_dir / payload.voice_id
        if not voice_path.exists() or not voice_path.is_dir():
            raise HTTPException(status_code=404, detail="Unknown voice_id")

        wav_bytes = _write_test_wav(duration_s=1.0, sample_rate=24000)
        headers = {"Content-Disposition": "attachment; filename=output.wav"}
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav", headers=headers)

    return app


app = create_app()

