"""Audio processing service for Pocket Studio."""

import io
import logging
import queue
import re
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

import wave

if TYPE_CHECKING:
    from backend.tts_engine import TTSEngine

logger = logging.getLogger("pocket_studio")


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors."""
    pass


class AudioService:
    """Service for audio processing operations.

    This class handles audio normalization, format conversion,
    MP3 encoding, and streaming operations.
    """

    def __init__(
        self,
        stream_segment_max_chars: int = 250,
        stream_keepalive_seconds: float = 10.0,
        stream_keepalive_silence_seconds: float = 0.15,
    ) -> None:
        """Initialize the audio service.

        Args:
            stream_segment_max_chars: Maximum characters per streaming segment
            stream_keepalive_seconds: Timeout for stream keepalive
            stream_keepalive_silence_seconds: Silence duration for stream keepalive
        """
        self.stream_segment_max_chars = stream_segment_max_chars
        self.stream_keepalive_seconds = stream_keepalive_seconds
        self.stream_keepalive_silence_seconds = stream_keepalive_silence_seconds
        self._silence_mp3_cache: dict[tuple[int, float], bytes] = {}

    @staticmethod
    def normalize_audio_to_wav_24k_mono(input_path: Path, output_path: Path) -> None:
        """Normalize audio file to WAV format at 24kHz mono.

        Args:
            input_path: Path to input audio file
            output_path: Path to output WAV file

        Raises:
            AudioProcessingError: If ffmpeg processing fails
        """
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
        completed = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if completed.returncode != 0:
            raise AudioProcessingError(
                completed.stderr.decode("utf-8", errors="ignore")
            )

    @staticmethod
    def wav_bytes_to_pcm_s16le(wav_bytes: bytes) -> tuple[int, bytes]:
        """Convert WAV bytes to PCM S16LE format.

        Args:
            wav_bytes: WAV file bytes

        Returns:
            Tuple of (sample_rate, PCM bytes)

        Raises:
            AudioProcessingError: If WAV is not mono 16-bit
        """
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if channels != 1 or sampwidth != 2:
            raise AudioProcessingError(
                "Only mono 16-bit WAV supported for streaming"
            )
        return int(sample_rate), frames

    def encode_mp3_from_pcm_s16le(self, pcm_s16le: bytes, sample_rate: int) -> bytes:
        """Encode PCM S16LE bytes to MP3 format.

        Args:
            pcm_s16le: PCM data in signed 16-bit little-endian mono format
            sample_rate: Sample rate of the PCM data

        Returns:
            MP3 encoded bytes

        Raises:
            AudioProcessingError: If ffmpeg encoding fails
        """
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-f",
            "mp3",
            "-write_xing",
            "0",
            "-id3v2_version",
            "0",
            "-b:a",
            "64k",
            "pipe:1",
        ]
        completed = subprocess.run(
            cmd, input=pcm_s16le, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if completed.returncode != 0:
            raise AudioProcessingError(
                completed.stderr.decode("utf-8", errors="ignore")
            )
        return completed.stdout

    def get_silence_mp3(self, sample_rate: int, duration_s: float) -> bytes:
        """Get MP3 encoded silence.

        Args:
            sample_rate: Sample rate for silence
            duration_s: Duration in seconds

        Returns:
            MP3 encoded silence bytes
        """
        duration_s = max(0.01, float(duration_s))
        key = (int(sample_rate), float(duration_s))
        cached = self._silence_mp3_cache.get(key)
        if cached is not None:
            return cached

        frames = int(sample_rate * duration_s)
        pcm = b"\x00\x00" * frames
        mp3 = self.encode_mp3_from_pcm_s16le(pcm, sample_rate)
        self._silence_mp3_cache[key] = mp3
        return mp3

    def split_text_for_streaming(self, text: str) -> list[str]:
        """Split text into chunks for streaming.

        Args:
            text: Input text to split

        Returns:
            List of text chunks
        """
        text = re.sub(r"\s+", " ", text).strip()
        if text == "":
            return []
        if len(text) <= self.stream_segment_max_chars:
            return [text]

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        cur = ""

        for s in sentences:
            s = s.strip()
            if s == "":
                continue

            if len(s) > self.stream_segment_max_chars:
                for i in range(0, len(s), self.stream_segment_max_chars):
                    part = s[i:i + self.stream_segment_max_chars].strip()
                    if part:
                        if cur:
                            chunks.append(cur)
                            cur = ""
                        chunks.append(part)
                continue

            if cur == "":
                cur = s
            elif len(cur) + 1 + len(s) <= self.stream_segment_max_chars:
                cur = f"{cur} {s}"
            else:
                chunks.append(cur)
                cur = s

        if cur:
            chunks.append(cur)

        return chunks

    def create_streaming_generator(
        self,
        voice_state: dict,
        chunks: list[str],
        speed: float | None,
        temperature: float | None,
        engine: "TTSEngine",
        first_mp3: bytes | None = None,
    ) -> tuple[callable, queue.Queue[bytes | None], threading.Event]:
        """Create a streaming generator for audio synthesis.

        Args:
            voice_state: Voice state for synthesis
            chunks: Text chunks to synthesize
            speed: Speech speed
            temperature: Generation temperature
            engine: TTS engine instance
            first_mp3: Pre-generated first MP3 chunk to yield first

        Returns:
            Tuple of (generator function, queue, stop event)
        """
        q: queue.Queue[bytes | None] = queue.Queue(maxsize=8)
        stop_event = threading.Event()

        def _worker(rest: list[str], sample_rate: int) -> None:
            try:
                for part in rest:
                    if stop_event.is_set():
                        return
                    result = engine.generate_wav(voice_state, part, speed, temperature)
                    sr2, pcm2 = self.wav_bytes_to_pcm_s16le(result.wav_bytes)
                    if sr2 != sample_rate:
                        sample_rate = sr2
                    mp3 = self.encode_mp3_from_pcm_s16le(pcm2, sample_rate)
                    q.put(mp3)
            except Exception:
                logger.exception("TTS generation failed (stream worker)")
            finally:
                q.put(None)

        def _iter() -> Iterator[bytes]:
            silence_mp3 = self.get_silence_mp3(
                24000, self.stream_keepalive_silence_seconds
            )
            try:
                if first_mp3:
                    yield first_mp3
                while True:
                    try:
                        item = q.get(timeout=self.stream_keepalive_seconds)
                    except queue.Empty:
                        if stop_event.is_set():
                            return
                        yield silence_mp3
                        continue
                    if item is None:
                        return
                    if item:
                        yield item
            except GeneratorExit:
                stop_event.set()
                raise
            except Exception:
                stop_event.set()
                raise

        return _iter, q, stop_event
