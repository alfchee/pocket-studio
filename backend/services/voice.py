"""Voice management service for Pocket Studio."""

import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

import wave

from backend.schemas.responses import VoiceInfo
from backend.services.audio import AudioService

logger = logging.getLogger("pocket_studio")


class VoiceManagementError(Exception):
    """Custom exception for voice management errors."""
    pass


class VoiceService:
    """Service for voice cloning and management.

    This class handles voice cloning, embedding generation,
    and voice listing operations.
    """

    def __init__(
        self,
        voices_dir: Path,
        min_ref_seconds: float = 5.0,
        max_ref_seconds: float = 10.0,
        max_audio_mb: int = 5,
    ) -> None:
        """Initialize the voice service.

        Args:
            voices_dir: Directory for storing voice embeddings
            min_ref_seconds: Minimum reference audio duration
            max_ref_seconds: Maximum reference audio duration
            max_audio_mb: Maximum upload size in megabytes
        """
        self.voices_dir = voices_dir
        self.min_ref_seconds = min_ref_seconds
        self.max_ref_seconds = max_ref_seconds
        self.max_audio_mb = max_audio_mb
        self._audio_service = AudioService()

    def clone_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        name: str | None,
        engine: "TTSEngine",
    ) -> tuple[str, str]:
        """Clone a voice from audio data.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename
            name: Optional custom name for the voice
            engine: TTS engine for embedding generation

        Returns:
            Tuple of (voice_id, voice_name)

        Raises:
            VoiceManagementError: If cloning fails
        """
        if len(audio_bytes) == 0:
            raise VoiceManagementError("Empty file")

        if len(audio_bytes) > self.max_audio_mb * 1024 * 1024:
            raise VoiceManagementError("File too large")

        if filename is None or filename == "":
            raise VoiceManagementError("Missing filename")

        voice_id = str(uuid.uuid4())
        voice_path = self.voices_dir / voice_id
        voice_path.mkdir(parents=True, exist_ok=True)

        ref_path = voice_path / "reference.wav"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            in_path = tmp_dir / "input"
            in_path.write_bytes(audio_bytes)

            try:
                self._audio_service.normalize_audio_to_wav_24k_mono(in_path, ref_path)
            except Exception as e:
                raise VoiceManagementError(f"Audio decode failed: {str(e)}")

        try:
            with wave.open(str(ref_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
            duration_s = (frames / rate) if rate else 0.0
        except Exception as e:
            raise VoiceManagementError(f"Invalid WAV after normalization: {str(e)}")

        if duration_s < self.min_ref_seconds or duration_s > self.max_ref_seconds:
            raise VoiceManagementError(
                f"Reference audio must be between {self.min_ref_seconds:.1f}s "
                f"and {self.max_ref_seconds:.1f}s (got {duration_s:.2f}s)"
            )

        embedding_path = voice_path / "voice.safetensors"
        try:
            engine.clone_to_safetensors(ref_path, embedding_path)
        except Exception as e:
            logger.exception("Voice embedding failed")
            raise VoiceManagementError(f"Voice embedding failed: {str(e)}")

        meta = {
            "voice_id": voice_id,
            "name": (name or "").strip() or voice_id,
            "source_filename": filename,
        }
        (voice_path / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

        return voice_id, meta["name"]

    def list_voices(self, builtin_voices: list[str]) -> list[VoiceInfo]:
        """List all available voices.

        Args:
            builtin_voices: List of built-in voice IDs

        Returns:
            List of VoiceInfo objects
        """
        results: list[VoiceInfo] = []

        for v in builtin_voices:
            results.append(VoiceInfo(voice_id=v, name=v, builtin=True))

        if not self.voices_dir.exists():
            return results

        for entry in sorted(self.voices_dir.iterdir()):
            if not entry.is_dir():
                continue

            meta_path = entry / "meta.json"
            name = entry.name

            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    name = meta.get("name") or name
                except Exception:
                    pass

            results.append(VoiceInfo(voice_id=entry.name, name=name, builtin=False))

        return results

    def resolve_speaker_wav_path(
        self, raw_path: str, voices_dir: Path
    ) -> Path:
        """Resolve and validate a speaker WAV path.

        Args:
            raw_path: Raw path string from request
            voices_dir: Base voices directory

        Returns:
            Resolved absolute Path

        Raises:
            VoiceManagementError: If path is invalid
        """
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
                raise VoiceManagementError("speaker_wav_path must be under VOICES_DIR")
        except Exception:
            raise VoiceManagementError("Invalid speaker_wav_path")

        if not resolved.exists() or not resolved.is_file():
            raise VoiceManagementError("speaker_wav_path not found")

        return resolved

    def get_voice_state(
        self,
        voice_id: str | None,
        speaker_wav_path: str | None,
        voices_dir: Path,
        builtin_voices: list[str],
        engine: "TTSEngine",
    ) -> Any:
        """Get voice state for synthesis.

        Args:
            voice_id: Voice ID to look up
            speaker_wav_path: Path to speaker WAV file
            voices_dir: Base voices directory
            builtin_voices: List of built-in voice IDs
            engine: TTS engine

        Returns:
            Voice state for synthesis

        Raises:
            VoiceManagementError: If voice not found
        """
        voice_state = None

        if speaker_wav_path is not None:
            speaker_path = self.resolve_speaker_wav_path(speaker_wav_path, voices_dir)
            try:
                voice_state = engine.load_voice_state(speaker_path)
            except Exception as e:
                raise VoiceManagementError(f"Invalid speaker_wav_path: {str(e)}")

        elif voice_id is not None:
            voice_path = voices_dir / voice_id
            if voice_path.exists() and voice_path.is_dir():
                safetensors_path = voice_path / "voice.safetensors"
                reference_path = voice_path / "reference.wav"

                if safetensors_path.exists():
                    voice_state = engine.load_voice_state(safetensors_path)
                elif reference_path.exists():
                    voice_state = engine.load_voice_state(reference_path)

            elif voice_id in builtin_voices:
                voice_state = engine.load_voice_state(voice_id)

        if voice_state is None:
            raise VoiceManagementError("Unknown voice")

        return voice_state