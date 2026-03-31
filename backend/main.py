"""Main FastAPI application for Pocket Studio.

This module provides the main application factory and entry point.
It wires together all components following clean architecture principles.
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.routes import create_tts_routes
from backend.config.settings import Settings, get_settings
from backend.services.audio import AudioService
from backend.services.voice import VoiceService
from backend.tts_engine import TTSEngine, create_engine
from backend.utils.logging import setup_logging

if __name__ == "__main__" and "." not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logger = logging.getLogger("pocket_studio")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings instance. If not provided, loads from environment.

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    setup_logging(level=logging.INFO)
    logger.info(f"Starting Pocket Studio with engine: {settings.tts_engine}")

    settings.ensure_directories()

    try:
        engine: TTSEngine = create_engine(settings.tts_engine)
    except Exception as e:
        logger.error(f"Failed to initialize TTS engine '{settings.tts_engine}': {str(e)}")
        raise RuntimeError(f"Failed to initialize TTS engine '{settings.tts_engine}': {str(e)}")

    audio_service = AudioService(
        stream_segment_max_chars=settings.stream_segment_max_chars,
        stream_keepalive_seconds=settings.stream_keepalive_seconds,
        stream_keepalive_silence_seconds=settings.stream_keepalive_silence_seconds,
    )

    voice_service = VoiceService(
        voices_dir=settings.voices_dir,
        min_ref_seconds=settings.min_ref_seconds,
        max_ref_seconds=settings.max_ref_seconds,
        max_audio_mb=settings.max_audio_upload_size_mb,
    )

    app = FastAPI(
        title="Pocket Studio API",
        description="Text-to-Speech API with voice cloning support",
        version="1.0.0",
    )

    tts_router = create_tts_routes(
        engine=engine,
        voice_service=voice_service,
        audio_service=audio_service,
        max_text_length=settings.max_text_length,
        min_speed=settings.min_speed,
        max_speed=settings.max_speed,
        min_temperature=settings.min_temperature,
        max_temperature=settings.max_temperature,
        voices_dir=settings.voices_dir,
    )
    app.include_router(tts_router)

    _setup_static_files(app, settings.static_dir)

    return app


def _setup_static_files(app: FastAPI, static_dir: Path) -> None:
    """Configure static file serving for SPA.

    Args:
        app: FastAPI application
        static_dir: Path to static files directory
    """
    if static_dir.exists() and static_dir.is_dir():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(str(static_dir / "index.html"))

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            candidate = static_dir / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(static_dir / "index.html"))


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
