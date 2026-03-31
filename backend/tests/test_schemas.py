"""Tests for schemas module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent))

from backend.schemas.requests import GenerateRequest
from backend.schemas.responses import CloneResponse, ErrorResponse, HealthInfo, VoiceInfo


class TestGenerateRequest:
    """Tests for GenerateRequest schema."""

    def test_valid_request_with_voice_id(self):
        """Test valid request with voice_id."""
        req = GenerateRequest(
            text="Hello world",
            voice_id="test-voice",
        )
        assert req.text == "Hello world"
        assert req.voice_id == "test-voice"
        assert req.speaker_wav_path is None
        assert req.language is None
        assert req.speed is None
        assert req.temperature is None

    def test_valid_request_with_speaker_wav_path(self):
        """Test valid request with speaker_wav_path."""
        req = GenerateRequest(
            text="Hello world",
            speaker_wav_path="/path/to/speaker.wav",
        )
        assert req.text == "Hello world"
        assert req.voice_id is None
        assert req.speaker_wav_path == "/path/to/speaker.wav"

    def test_valid_request_with_all_fields(self):
        """Test valid request with all fields."""
        req = GenerateRequest(
            text="Hello world",
            voice_id="test-voice",
            language="en",
            speed=1.5,
            temperature=0.8,
        )
        assert req.text == "Hello world"
        assert req.voice_id == "test-voice"
        assert req.language == "en"
        assert req.speed == 1.5
        assert req.temperature == 0.8

    def test_invalid_request_empty_text(self):
        """Test that empty text raises error."""
        with pytest.raises(ValueError):
            GenerateRequest(text="", voice_id="test-voice")

    def test_invalid_request_no_voice_source(self):
        """Test that request without voice_id or speaker_wav_path raises error."""
        with pytest.raises(ValueError, match="Either voice_id or speaker_wav_path is required"):
            GenerateRequest(text="Hello world")

    def test_whitespace_only_voice_id_normalized(self):
        """Test that whitespace-only voice_id is stripped."""
        req = GenerateRequest(text="Hello world", voice_id="test ")
        assert req.voice_id == "test"

    def test_whitespace_only_speaker_wav_path_normalized(self):
        """Test that whitespace-only speaker_wav_path is stripped."""
        req = GenerateRequest(text="Hello world", speaker_wav_path="test.wav ")
        assert req.speaker_wav_path == "test.wav"

    def test_language_whitespace_trimmed(self):
        """Test that language whitespace is trimmed."""
        req = GenerateRequest(text="Hello world", voice_id="test", language="  en  ")
        assert req.language == "en"

    def test_speed_out_of_range_low(self):
        """Test that speed below 0.1 raises error."""
        with pytest.raises(ValueError):
            GenerateRequest(text="Hello world", voice_id="test", speed=0.05)

    def test_speed_out_of_range_high(self):
        """Test that speed above 10.0 raises error."""
        with pytest.raises(ValueError):
            GenerateRequest(text="Hello world", voice_id="test", speed=15.0)

    def test_temperature_out_of_range_low(self):
        """Test that temperature below 0.0 raises error."""
        with pytest.raises(ValueError):
            GenerateRequest(text="Hello world", voice_id="test", temperature=-0.1)

    def test_temperature_out_of_range_high(self):
        """Test that temperature above 2.0 raises error."""
        with pytest.raises(ValueError):
            GenerateRequest(text="Hello world", voice_id="test", temperature=3.0)


class TestHealthInfo:
    """Tests for HealthInfo schema."""

    def test_valid_health_info(self):
        """Test valid HealthInfo creation."""
        info = HealthInfo(status="ok", engine="xtts_v2", sample_rate=24000)
        assert info.status == "ok"
        assert info.engine == "xtts_v2"
        assert info.sample_rate == 24000

    def test_health_info_without_sample_rate(self):
        """Test HealthInfo without sample_rate."""
        info = HealthInfo(status="ok", engine="dummy")
        assert info.status == "ok"
        assert info.engine == "dummy"
        assert info.sample_rate is None


class TestVoiceInfo:
    """Tests for VoiceInfo schema."""

    def test_valid_voice_info(self):
        """Test valid VoiceInfo creation."""
        info = VoiceInfo(voice_id="test-id", name="Test Voice", builtin=False)
        assert info.voice_id == "test-id"
        assert info.name == "Test Voice"
        assert info.builtin is False

    def test_voice_info_default_builtin(self):
        """Test VoiceInfo builtin defaults to False."""
        info = VoiceInfo(voice_id="test-id", name="Test Voice")
        assert info.builtin is False


class TestCloneResponse:
    """Tests for CloneResponse schema."""

    def test_valid_clone_response(self):
        """Test valid CloneResponse creation."""
        response = CloneResponse(voice_id="new-voice-id", name="My Voice")
        assert response.voice_id == "new-voice-id"
        assert response.name == "My Voice"


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_valid_error_response(self):
        """Test valid ErrorResponse creation."""
        response = ErrorResponse(detail="Something went wrong")
        assert response.detail == "Something went wrong"
