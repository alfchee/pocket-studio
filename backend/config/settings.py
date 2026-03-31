"""Settings and configuration management for Pocket Studio."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        voices_dir: Directory for storing voice embeddings
        outputs_dir: Directory for generated audio outputs
        static_dir: Directory for static frontend files
        tts_engine: Name of the TTS engine to use
        max_audio_upload_size_mb: Maximum upload size in megabytes
        max_text_length: Maximum text length for synthesis
        min_ref_seconds: Minimum reference audio duration
        max_ref_seconds: Maximum reference audio duration
        min_speed: Minimum speech speed
        max_speed: Maximum speech speed
        min_temperature: Minimum temperature for generation
        max_temperature: Maximum temperature for generation
        stream_segment_max_chars: Maximum characters per streaming segment
        stream_keepalive_seconds: Timeout for stream keepalive
        stream_keepalive_silence_seconds: Silence duration for stream keepalive
        port: Server port
    """

    voices_dir: Path = Path("./voices")
    outputs_dir: Path = Path("./outputs")
    static_dir: Path = Path("./static")
    tts_engine: str = "dummy"

    max_audio_upload_size_mb: int = 5
    max_text_length: int = 5000

    min_ref_seconds: float = 5.0
    max_ref_seconds: float = 10.0

    min_speed: float = 0.5
    max_speed: float = 2.0
    min_temperature: float = 0.0
    max_temperature: float = 1.5

    stream_segment_max_chars: int = 250
    stream_keepalive_seconds: float = 10.0
    stream_keepalive_silence_seconds: float = 0.15

    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("voices_dir", "outputs_dir", "static_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        if isinstance(v, Path):
            return v
        return Path(v)

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.voices_dir, self.outputs_dir]:
            if dir_path.exists():
                continue
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError):
                pass

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "voices_dir": str(self.voices_dir),
            "outputs_dir": str(self.outputs_dir),
            "static_dir": str(self.static_dir),
            "tts_engine": self.tts_engine,
            "max_audio_upload_size_mb": self.max_audio_upload_size_mb,
            "max_text_length": self.max_text_length,
            "min_ref_seconds": self.min_ref_seconds,
            "max_ref_seconds": self.max_ref_seconds,
            "min_speed": self.min_speed,
            "max_speed": self.max_speed,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "stream_segment_max_chars": self.stream_segment_max_chars,
            "stream_keepalive_seconds": self.stream_keepalive_seconds,
            "stream_keepalive_silence_seconds": self.stream_keepalive_silence_seconds,
            "port": self.port,
        }


def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings: Application settings instance
    """
    return Settings()