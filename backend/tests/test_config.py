"""Tests for configuration module."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

for key in ['PORT', 'VOICES_DIR', 'OUTPUTS_DIR', 'MODELS_DIR', 'STATIC_DIR', 'HF_HOME', 'TTS_CACHE_DIR', 'TRANSFORMERS_CACHE']:
    if key in os.environ:
        del os.environ[key]

from backend.config.settings import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test default settings values."""
        settings = Settings()
        assert isinstance(settings.voices_dir, Path)
        assert isinstance(settings.outputs_dir, Path)
        assert isinstance(settings.static_dir, Path)
        assert settings.tts_engine == "dummy"
        assert settings.max_audio_upload_size_mb == 5
        assert settings.max_text_length == 5000
        assert settings.min_ref_seconds == 5.0
        assert settings.max_ref_seconds == 10.0
        assert settings.min_speed == 0.5
        assert settings.max_speed == 2.0
        assert settings.min_temperature == 0.0
        assert settings.max_temperature == 1.5
        assert settings.stream_segment_max_chars == 250
        assert settings.stream_keepalive_seconds == 10.0
        assert settings.stream_keepalive_silence_seconds == 0.15
        assert settings.port == 8000

    def test_custom_values(self):
        """Test custom settings values via environment."""
        settings = Settings(
            voices_dir="/custom/voices",
            outputs_dir="/custom/outputs",
            static_dir="/custom/static",
            tts_engine="xtts_v2",
            max_audio_upload_size_mb=10,
            max_text_length=10000,
            port=9000,
        )
        assert settings.voices_dir == Path("/custom/voices")
        assert settings.outputs_dir == Path("/custom/outputs")
        assert settings.static_dir == Path("/custom/static")
        assert settings.tts_engine == "xtts_v2"
        assert settings.max_audio_upload_size_mb == 10
        assert settings.max_text_length == 10000
        assert settings.port == 9000

    def test_path_resolution_from_string(self):
        """Test that string paths are resolved to Path objects."""
        settings = Settings(voices_dir="/test/voices")
        assert isinstance(settings.voices_dir, Path)
        assert settings.voices_dir == Path("/test/voices")

    def test_ensure_directories_creates_when_missing(self, tmp_path):
        """Test ensure_directories creates directories when missing."""
        voices = tmp_path / "voices"
        outputs = tmp_path / "outputs"
        settings = Settings(voices_dir=voices, outputs_dir=outputs)
        settings.ensure_directories()
        assert voices.exists()
        assert outputs.exists()

    def test_ensure_directories_skips_existing(self, tmp_path):
        """Test ensure_directories doesn't fail when directories exist."""
        voices = tmp_path / "voices"
        voices.mkdir()
        outputs = tmp_path / "outputs"
        outputs.mkdir()
        settings = Settings(voices_dir=voices, outputs_dir=outputs)
        settings.ensure_directories()
        assert voices.exists()
        assert outputs.exists()

    def test_to_dict(self):
        """Test to_dict method returns correct dictionary."""
        settings = Settings(
            voices_dir=Path("/test/voices"),
            outputs_dir=Path("/test/outputs"),
            static_dir=Path("/test/static"),
            tts_engine="test_engine",
            max_audio_upload_size_mb=5,
            max_text_length=5000,
        )
        d = settings.to_dict()
        assert d["voices_dir"] == "/test/voices"
        assert d["outputs_dir"] == "/test/outputs"
        assert d["static_dir"] == "/test/static"
        assert d["tts_engine"] == "test_engine"
        assert d["max_audio_upload_size_mb"] == 5
        assert d["max_text_length"] == 5000

    def test_get_settings_returns_settings_instance(self):
        """Test get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)


class TestSettingsValidators:
    """Tests for Settings validators."""

    def test_path_validator_preserves_path_objects(self):
        """Test that Path objects are preserved by validator."""
        path = Path("/test/path")
        settings = Settings(voices_dir=path)
        assert settings.voices_dir == path

    def test_path_validator_converts_strings(self):
        """Test that string paths are converted to Path objects."""
        settings = Settings(voices_dir="/test/path")
        assert isinstance(settings.voices_dir, Path)
        assert settings.voices_dir == Path("/test/path")
