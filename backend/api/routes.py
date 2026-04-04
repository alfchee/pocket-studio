"""API routes for Pocket Studio."""

import io
import logging
import threading
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.schemas.requests import GenerateRequest
from backend.schemas.responses import CloneResponse, HealthInfo, VoiceInfo
from backend.services.audio import AudioService
from backend.services.voice import VoiceService

if TYPE_CHECKING:
    from backend.tts_engine import TTSEngine

logger = logging.getLogger("pocket_studio")

router = APIRouter()


def create_tts_routes(
    engine: "TTSEngine",
    voice_service: VoiceService,
    audio_service: AudioService,
    max_text_length: int,
    min_speed: float,
    max_speed: float,
    min_temperature: float,
    max_temperature: float,
    voices_dir: Path,
) -> APIRouter:
    """Create TTS API routes with injected dependencies.

    Args:
        engine: TTS engine instance
        voice_service: Voice service instance
        audio_service: Audio service instance
        max_text_length: Maximum text length
        min_speed: Minimum speed value
        max_speed: Maximum speed value
        min_temperature: Minimum temperature value
        max_temperature: Maximum temperature value
        voices_dir: Voices directory path

    Returns:
        Configured API router
    """
    router_instance = APIRouter()

    @router_instance.get("/api/health")
    def health() -> HealthInfo:
        """Health check endpoint."""
        return HealthInfo(
            status="ok",
            engine=getattr(engine, "name", "unknown"),
            sample_rate=getattr(engine, "sample_rate", None),
        )

    @router_instance.get("/api/voices")
    def list_voices() -> list[VoiceInfo]:
        """List all available voices."""
        builtin_voices = getattr(engine, "builtin_voices", [])
        return voice_service.list_voices(builtin_voices)

    @router_instance.post("/api/clone")
    async def clone_voice(
        file: Annotated[UploadFile, File(description="Reference audio file")],
        name: Annotated[str | None, Form()] = None,
        ref_text: Annotated[str | None, Form(description="Transcription of the reference audio (enables higher-quality ICL mode)")] = None,
    ) -> CloneResponse:
        """Clone a voice from reference audio."""
        if file.filename is None or file.filename == "":
            raise HTTPException(status_code=400, detail="Missing filename")

        raw = await file.read()
        if len(raw) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        try:
            voice_id, voice_name = voice_service.clone_voice(
                audio_bytes=raw,
                filename=file.filename,
                name=name,
                ref_text=ref_text,
                engine=engine,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        return CloneResponse(voice_id=voice_id, name=voice_name)

    @router_instance.post("/api/generate")
    def generate_audio(payload: GenerateRequest) -> StreamingResponse:
        """Generate audio from text."""
        text = payload.text.strip()
        if text == "":
            raise HTTPException(status_code=400, detail="Empty text")
        if len(text) > max_text_length:
            raise HTTPException(status_code=413, detail="Text too long")

        language = (payload.language or "es").strip()
        supported_languages = getattr(engine, "supported_languages", None)
        if supported_languages and language not in supported_languages:
            raise HTTPException(status_code=400, detail="Unsupported language")

        try:
            voice_state = voice_service.get_voice_state(
                voice_id=payload.voice_id,
                speaker_wav_path=payload.speaker_wav_path,
                voices_dir=voices_dir,
                builtin_voices=getattr(engine, "builtin_voices", []),
                engine=engine,
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

        if isinstance(voice_state, dict):
            voice_state = {**voice_state, "language": language}

        speed = _clamp_speed(payload.speed, min_speed, max_speed)
        temperature = _clamp_temperature(payload.temperature, min_temperature, max_temperature)

        try:
            result = engine.generate_wav(voice_state, text, speed, temperature)
        except Exception as e:
            logger.exception("TTS generation failed")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

        headers = {"Content-Disposition": "attachment; filename=output.wav"}
        return StreamingResponse(
            io.BytesIO(result.wav_bytes),
            media_type="audio/wav",
            headers=headers,
        )

    @router_instance.post("/api/generate_stream")
    def generate_audio_stream(payload: GenerateRequest) -> StreamingResponse:
        """Generate streaming audio from text."""
        text = payload.text.strip()
        if text == "":
            raise HTTPException(status_code=400, detail="Empty text")
        if len(text) > max_text_length:
            raise HTTPException(status_code=413, detail="Text too long")

        language = (payload.language or "es").strip()
        supported_languages = getattr(engine, "supported_languages", None)
        if supported_languages and language not in supported_languages:
            raise HTTPException(status_code=400, detail="Unsupported language")

        try:
            voice_state = voice_service.get_voice_state(
                voice_id=payload.voice_id,
                speaker_wav_path=payload.speaker_wav_path,
                voices_dir=voices_dir,
                builtin_voices=getattr(engine, "builtin_voices", []),
                engine=engine,
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

        if isinstance(voice_state, dict):
            voice_state = {**voice_state, "language": language}

        speed = _clamp_speed(payload.speed, min_speed, max_speed)
        temperature = _clamp_temperature(payload.temperature, min_temperature, max_temperature)

        chunks = audio_service.split_text_for_streaming(text)
        if not chunks:
            raise HTTPException(status_code=400, detail="Empty text")

        try:
            first_result = engine.generate_wav(voice_state, chunks[0], speed, temperature)
            sr, pcm = audio_service.wav_bytes_to_pcm_s16le(first_result.wav_bytes)
            first_mp3 = audio_service.encode_mp3_from_pcm_s16le(pcm, sr)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("TTS generation failed (stream, first chunk)")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

        generator, q, stop_event = audio_service.create_streaming_generator(
            voice_state=voice_state,
            chunks=chunks,
            speed=speed,
            temperature=temperature,
            engine=engine,
            first_mp3=first_mp3,
        )

        if len(chunks) > 1:
            import threading
            t = threading.Thread(
                target=_stream_worker,
                args=(
                    chunks[1:],
                    sr,
                    voice_state,
                    speed,
                    temperature,
                    engine,
                    audio_service,
                    q,
                    stop_event,
                ),
                daemon=True,
            )
            t.start()
        else:
            q.put(None)

        headers = {
            "Content-Disposition": "inline; filename=output.mp3",
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(
            generator(),
            media_type="audio/mpeg",
            headers=headers,
        )

    return router_instance


def _stream_worker(
    rest: list[str],
    sample_rate: int,
    voice_state: dict,
    speed: float | None,
    temperature: float | None,
    engine: "TTSEngine",
    audio_service: AudioService,
    q: Queue[bytes | None],
    stop_event: threading.Event,
) -> None:
    """Worker thread for streaming audio generation."""
    try:
        for part in rest:
            if stop_event.is_set():
                return
            result = engine.generate_wav(voice_state, part, speed, temperature)
            sr2, pcm2 = audio_service.wav_bytes_to_pcm_s16le(result.wav_bytes)
            if sr2 != sample_rate:
                sample_rate = sr2
            mp3 = audio_service.encode_mp3_from_pcm_s16le(pcm2, sample_rate)
            q.put(mp3)
    except Exception:
        logger.exception("TTS generation failed (stream worker)")
    finally:
        q.put(None)


def _clamp_speed(speed: float | None, min_speed: float, max_speed: float) -> float | None:
    """Clamp speed value to valid range."""
    if speed is None:
        return None
    if speed < min_speed:
        return min_speed
    if speed > max_speed:
        return max_speed
    return speed


def _clamp_temperature(
    temperature: float | None, min_temp: float, max_temp: float
) -> float | None:
    """Clamp temperature value to valid range."""
    if temperature is None:
        return None
    if temperature < min_temp:
        return min_temp
    if temperature > max_temp:
        return max_temp
    return temperature
