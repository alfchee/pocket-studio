"""Tests for services module."""

import io
import os
import sys
import tempfile
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent))

for key in ['PORT', 'VOICES_DIR', 'OUTPUTS_DIR', 'MODELS_DIR', 'STATIC_DIR', 'HF_HOME']:
    if key in os.environ:
        del os.environ[key]

from backend.services.audio import AudioService, AudioProcessingError
from backend.services.voice import VoiceService, VoiceManagementError


class TestAudioService:
    """Tests for AudioService class."""

    @pytest.fixture
    def audio_service(self):
        """Create an AudioService instance."""
        return AudioService(
            stream_segment_max_chars=250,
            stream_keepalive_seconds=10.0,
            stream_keepalive_silence_seconds=0.15,
        )

    @pytest.fixture
    def valid_wav_bytes(self):
        """Create valid WAV bytes (6 seconds at 24kHz mono)."""
        frames = int(24000 * 6)
        pcm = b"\x00\x00" * frames
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm)
        return buf.getvalue()

    def test_init_default_values(self):
        """Test AudioService initializes with correct defaults."""
        service = AudioService()
        assert service.stream_segment_max_chars == 250
        assert service.stream_keepalive_seconds == 10.0
        assert service.stream_keepalive_silence_seconds == 0.15

    def test_init_custom_values(self):
        """Test AudioService initializes with custom values."""
        service = AudioService(
            stream_segment_max_chars=500,
            stream_keepalive_seconds=5.0,
            stream_keepalive_silence_seconds=0.5,
        )
        assert service.stream_segment_max_chars == 500
        assert service.stream_keepalive_seconds == 5.0
        assert service.stream_keepalive_silence_seconds == 0.5

    def test_normalize_audio_to_wav_24k_mono(self, audio_service, tmp_path):
        """Test audio normalization to 24kHz mono WAV."""
        input_path = tmp_path / "input.wav"
        output_path = tmp_path / "output.wav"

        frames = int(44100 * 3)
        pcm = b"\x00\x00" * frames
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(pcm)
        input_path.write_bytes(buf.getvalue())

        audio_service.normalize_audio_to_wav_24k_mono(input_path, output_path)

        assert output_path.exists()
        with wave.open(str(output_path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 24000

    def test_wav_bytes_to_pcm_s16le(self, audio_service, valid_wav_bytes):
        """Test WAV bytes to PCM S16LE conversion."""
        sample_rate, pcm = audio_service.wav_bytes_to_pcm_s16le(valid_wav_bytes)

        assert sample_rate == 24000
        assert isinstance(pcm, bytes)
        assert len(pcm) > 0

    def test_wav_bytes_to_pcm_s16le_invalid_format(self, audio_service, tmp_path):
        """Test that non-mono or non-16-bit WAV raises error."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * 100)

        with pytest.raises(AudioProcessingError, match="Only mono 16-bit WAV"):
            audio_service.wav_bytes_to_pcm_s16le(buf.getvalue())

    def test_encode_mp3_from_pcm_s16le(self, audio_service):
        """Test MP3 encoding from PCM S16LE."""
        frames = int(24000 * 1)
        pcm = b"\x00\x00" * frames

        mp3 = audio_service.encode_mp3_from_pcm_s16le(pcm, 24000)

        assert isinstance(mp3, bytes)
        assert len(mp3) > 0
        assert mp3[:1] == b"\xff" or mp3[:3] == b"ID3"

    def test_get_silence_mp3(self, audio_service):
        """Test silence MP3 generation and caching."""
        silence1 = audio_service.get_silence_mp3(24000, 0.15)
        silence2 = audio_service.get_silence_mp3(24000, 0.15)

        assert isinstance(silence1, bytes)
        assert len(silence1) > 0
        assert silence1 == silence2

    def test_get_silence_mp3_different_durations(self, audio_service):
        """Test silence MP3 with different durations."""
        silence1 = audio_service.get_silence_mp3(24000, 0.1)
        silence2 = audio_service.get_silence_mp3(24000, 0.5)

        assert isinstance(silence1, bytes)
        assert isinstance(silence2, bytes)
        assert len(silence1) != len(silence2)

    def test_split_text_for_streaming_empty(self, audio_service):
        """Test splitting empty text."""
        chunks = audio_service.split_text_for_streaming("")
        assert chunks == []

    def test_split_text_for_streaming_short_text(self, audio_service):
        """Test splitting text shorter than max chars."""
        text = "Hello world"
        chunks = audio_service.split_text_for_streaming(text)
        assert chunks == ["Hello world"]

    def test_split_text_for_streaming_long_text(self, audio_service):
        """Test splitting text longer than max chars."""
        text = "Hello. World! How are you today? I am fine."
        chunks = audio_service.split_text_for_streaming(text)
        assert len(chunks) > 0
        assert all(len(c) <= audio_service.stream_segment_max_chars for c in chunks)

    def test_split_text_for_streaming_multiple_sentences(self, audio_service):
        """Test splitting text with multiple sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three. " * 10
        chunks = audio_service.split_text_for_streaming(text)
        assert len(chunks) > 1

    def test_split_text_for_streaming_whitespace_normalization(self, audio_service):
        """Test that whitespace is normalized in splitting."""
        text = "Hello    world   how   are   you?"
        chunks = audio_service.split_text_for_streaming(text)
        assert "Hello    world   how   are   you?" not in chunks
        assert all("  " not in c for c in chunks)


class TestVoiceService:
    """Tests for VoiceService class."""

    @pytest.fixture
    def temp_voices_dir(self, tmp_path):
        """Create a temporary voices directory."""
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        return voices_dir

    @pytest.fixture
    def voice_service(self, temp_voices_dir):
        """Create a VoiceService instance."""
        return VoiceService(
            voices_dir=temp_voices_dir,
            min_ref_seconds=5.0,
            max_ref_seconds=10.0,
            max_audio_mb=5,
        )

    @pytest.fixture
    def valid_ref_audio(self):
        """Create valid reference audio bytes (6 seconds at 24kHz mono)."""
        frames = int(24000 * 6)
        pcm = b"\x00\x00" * frames
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm)
        return buf.getvalue()

    def test_init_default_values(self):
        """Test VoiceService initializes with correct defaults."""
        service = VoiceService(
            voices_dir=Path("/test/voices"),
            min_ref_seconds=5.0,
            max_ref_seconds=10.0,
            max_audio_mb=5,
        )
        assert service.voices_dir == Path("/test/voices")
        assert service.min_ref_seconds == 5.0
        assert service.max_ref_seconds == 10.0
        assert service.max_audio_mb == 5

    def test_clone_voice_empty_file(self, voice_service):
        """Test that cloning with empty file raises error."""
        with pytest.raises(VoiceManagementError, match="Empty file"):
            voice_service.clone_voice(
                audio_bytes=b"",
                filename="test.wav",
                name=None,
                engine=MagicMock(),
            )

    def test_clone_voice_missing_filename(self, voice_service, valid_ref_audio):
        """Test that cloning without filename raises error."""
        with pytest.raises(VoiceManagementError, match="Missing filename"):
            voice_service.clone_voice(
                audio_bytes=valid_ref_audio,
                filename="",
                name=None,
                engine=MagicMock(),
            )

    def test_list_voices_empty(self, voice_service):
        """Test listing voices when directory is empty."""
        voices = voice_service.list_voices([])
        assert voices == []

    def test_list_voices_with_builtin(self, voice_service):
        """Test listing voices with builtin voices."""
        voices = voice_service.list_voices(["voice1", "voice2"])
        assert len(voices) == 2
        assert all(v.builtin for v in voices)

    def test_resolve_speaker_wav_path_invalid(self, voice_service):
        """Test that resolving invalid path raises error."""
        with pytest.raises(VoiceManagementError, match="Invalid speaker_wav_path"):
            voice_service.resolve_speaker_wav_path("/etc/passwd", voice_service.voices_dir)

    def test_resolve_speaker_wav_path_not_found(self, voice_service):
        """Test that resolving non-existent path raises error."""
        with pytest.raises(VoiceManagementError, match="speaker_wav_path not found"):
            voice_service.resolve_speaker_wav_path("nonexistent.wav", voice_service.voices_dir)


class MockTTSEngine:
    """Mock TTS engine for testing."""

    name = "dummy"
    sample_rate = 24000
    supported_languages = ["en", "es", "fr"]
    builtin_voices = []

    def clone_to_safetensors(self, ref_path, output_path):
        """Mock clone method."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mock safetensors data")

    def load_voice_state(self, path):
        """Mock load voice state method."""
        if isinstance(path, str) and path in self.builtin_voices:
            return {"type": "builtin", "id": path}
        return {"type": "custom", "path": str(path)}

    def generate_wav(self, voice_state, text, speed, temperature):
        """Mock generate method."""
        class MockResult:
            wav_bytes = b"RIFF" + b"\x00" * 44 + b"\x00" * 1000
        return MockResult()


from unittest.mock import MagicMock
