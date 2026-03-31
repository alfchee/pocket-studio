import inspect
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wave

logger = logging.getLogger("pocket_studio")

# Empirically profiled characters-per-second rates for XTTS-v2
_XTTS_CPS: dict[str, float] = {
    "en": 14.0, "es": 16.0, "fr": 15.0, "de": 13.0,
    "it": 15.5, "pt": 15.5, "pl": 14.5, "tr": 13.5,
    "ru": 14.0, "nl": 14.0, "cs": 13.5, "ar": 13.0,
    "zh-cn": 6.0, "ja": 8.0, "hu": 13.5, "ko": 9.0, "hi": 13.0,
}

_XTTS_MAX_TTS_RATIO = 2.5   # ratio above which output is treated as a hallucination
_XTTS_SILENCE_WARN = 0.40   # fraction of silence that triggers a retry


def _strip_tts_silence(
    audio: "Any",
    sample_rate: int,
    threshold: float = 0.01,
    min_keep_ms: float = 50.0,
) -> "Any":
    """Remove near-zero boundary padding that XTTS-v2 always prepends/appends."""
    import numpy as np
    if len(audio) == 0:
        return audio
    min_keep = max(1, int(min_keep_ms / 1000.0 * sample_rate))
    above = np.where(np.abs(audio) > threshold)[0]
    if len(above) == 0:
        return audio[:min_keep]
    first, last = int(above[0]), int(above[-1]) + 1
    stripped = audio[first:last]
    return stripped if len(stripped) >= min_keep else audio


def _compress_internal_silence(
    audio: "Any",
    sample_rate: int,
    threshold: float = 0.005,
    max_silence_ms: float = 200.0,
    target_silence_ms: float = 100.0,
) -> "Any":
    """Shorten mid-sentence pauses longer than max_silence_ms down to target_silence_ms."""
    import numpy as np
    max_n = int(max_silence_ms / 1000.0 * sample_rate)
    target_n = int(target_silence_ms / 1000.0 * sample_rate)
    if target_n >= max_n:
        return audio
    is_silent = np.abs(audio) <= threshold
    chunks: list = []
    i, n = 0, len(audio)
    while i < n:
        if is_silent[i]:
            j = i
            while j < n and is_silent[j]:
                j += 1
            run = j - i
            keep = target_n if run > max_n else run
            chunks.append(audio[i: i + keep])
            i = j
        else:
            j = i
            while j < n and not is_silent[j]:
                j += 1
            chunks.append(audio[i:j])
            i = j
    return np.concatenate(chunks) if chunks else audio


def _peak_limited_rms_normalize(
    audio: "Any",
    target_rms: float = 0.08,
    target_peak: float = 0.95,
    max_gain: float = 10.0,
) -> "Any":
    """Normalize RMS while ensuring no sample exceeds target_peak (avoids clipping)."""
    import numpy as np
    rms = float(np.sqrt(np.mean(audio ** 2) + 1e-12))
    peak = float(np.max(np.abs(audio)) + 1e-12)
    if rms <= 1e-6:
        return audio
    gain = min(target_rms / rms, target_peak / peak, max_gain)
    return audio * gain


def write_wav_bytes_from_pcm_f32(pcm_f32: Any, sample_rate: int) -> bytes:
    try:
        import numpy as np
    except Exception as e:  # pragma: no cover
        raise RuntimeError("numpy is required to write wav bytes") from e

    if hasattr(pcm_f32, "detach"):
        pcm_f32 = pcm_f32.detach().cpu().numpy()
    pcm_f32 = np.asarray(pcm_f32)

    if pcm_f32.dtype != np.int16:
        pcm_f32 = np.clip(pcm_f32, -1.0, 1.0)
        pcm_i16 = (pcm_f32 * 32767.0).astype(np.int16)
    else:
        pcm_i16 = pcm_f32

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_i16.tobytes())
    return buf.getvalue()


@dataclass(frozen=True)
class EngineResult:
    sample_rate: int
    wav_bytes: bytes


class TTSEngine:
    name: str
    builtin_voices: list[str]
    sample_rate: int

    def clone_to_safetensors(self, reference_wav: Path, safetensors_path: Path) -> None:
        raise NotImplementedError

    def load_voice_state(self, voice_prompt: str | Path) -> Any:
        raise NotImplementedError

    def generate_wav(self, voice_state: Any, text: str, speed: float | None, temperature: float | None) -> EngineResult:
        raise NotImplementedError


class DummyEngine(TTSEngine):
    name = "dummy"
    builtin_voices = [
        "alba",
        "marius",
        "javert",
        "jean",
        "fantine",
        "cosette",
        "eponine",
        "azelma",
    ]
    sample_rate = 24000

    def clone_to_safetensors(self, reference_wav: Path, safetensors_path: Path) -> None:
        safetensors_path.write_bytes(b"PLACEHOLDER")

    def load_voice_state(self, voice_prompt: str | Path) -> Any:
        return {"voice": str(voice_prompt)}

    def generate_wav(self, voice_state: Any, text: str, speed: float | None, temperature: float | None) -> EngineResult:
        frames = int(1.0 * self.sample_rate)
        pcm = bytearray()
        for _ in range(frames):
            pcm.extend((0).to_bytes(2, byteorder="little", signed=True))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(bytes(pcm))
        return EngineResult(sample_rate=self.sample_rate, wav_bytes=buf.getvalue())


class PocketTTSEngine(TTSEngine):
    name = "pocket_tts"
    builtin_voices = [
        "alba",
        "marius",
        "javert",
        "jean",
        "fantine",
        "cosette",
        "eponine",
        "azelma",
    ]

    def __init__(self) -> None:
        from pocket_tts import TTSModel

        self._TTSModel = TTSModel
        self.model = TTSModel.load_model()
        self.sample_rate = int(getattr(self.model, "sample_rate", 24000))

        try:
            from pocket_tts import export_model_state, import_model_state

            self._export_model_state = export_model_state
            self._import_model_state = import_model_state
        except Exception:
            self._export_model_state = None
            self._import_model_state = None

    def clone_to_safetensors(self, reference_wav: Path, safetensors_path: Path) -> None:
        voice_state = self.model.get_state_for_audio_prompt(str(reference_wav))
        if self._export_model_state is None:
            raise RuntimeError("pocket_tts.export_model_state not available")
        self._export_model_state(voice_state, str(safetensors_path))

    def load_voice_state(self, voice_prompt: str | Path) -> Any:
        if isinstance(voice_prompt, Path) and voice_prompt.suffix == ".safetensors" and self._import_model_state is not None:
            return self._import_model_state(str(voice_prompt))
        return self.model.get_state_for_audio_prompt(str(voice_prompt))

    def generate_wav(self, voice_state: Any, text: str, speed: float | None, temperature: float | None) -> EngineResult:
        kwargs: dict[str, Any] = {}
        sig = inspect.signature(self.model.generate_audio)
        if speed is not None and "speed" in sig.parameters:
            kwargs["speed"] = speed
        if temperature is not None and "temperature" in sig.parameters:
            kwargs["temperature"] = temperature

        audio = self.model.generate_audio(voice_state, text, **kwargs)
        wav_bytes = write_wav_bytes_from_pcm_f32(audio, self.sample_rate)
        return EngineResult(sample_rate=self.sample_rate, wav_bytes=wav_bytes)


class XTTSEngine(TTSEngine):
    name = "xtts_v2"
    builtin_voices: list[str] = []

    def __init__(self) -> None:
        self._tts = None
        self.sample_rate = 24000
        self.supported_languages = [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh-cn",
            "ja",
            "hu",
            "ko",
            "hi",
        ]

    def _get_tts(self) -> Any:
        if self._tts is not None:
            return self._tts
        from TTS.api import TTS

        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
        sr = getattr(getattr(tts, "synthesizer", None), "output_sample_rate", None)
        self.sample_rate = int(sr) if sr else 24000
        langs = list(getattr(tts, "languages", []) or [])
        if langs:
            self.supported_languages = langs
        self._tts = tts
        return self._tts

    def clone_to_safetensors(self, reference_wav: Path, safetensors_path: Path) -> None:
        safetensors_path.write_bytes(b"XTTS_V2")

    def load_voice_state(self, voice_prompt: str | Path) -> Any:
        if isinstance(voice_prompt, Path):
            if voice_prompt.suffix == ".safetensors":
                reference = voice_prompt.parent / "reference.wav"
                if not reference.exists():
                    raise FileNotFoundError(str(reference))
                return {"speaker_wav": str(reference), "language": "es"}
            return {"speaker_wav": str(voice_prompt), "language": "es"}
        return {"speaker": voice_prompt, "language": "es"}

    def generate_wav(self, voice_state: Any, text: str, speed: float | None, temperature: float | None) -> EngineResult:
        import numpy as np

        if not isinstance(voice_state, dict):
            raise TypeError("XTTS engine expects dict voice_state")

        tts = self._get_tts()
        sig = inspect.signature(tts.tts)
        language = (voice_state.get("language") or "es").strip()

        def _build_kwargs(override_speed: float | None = None) -> dict[str, Any]:
            kw: dict[str, Any] = {"text": text}
            if "speaker_wav" in sig.parameters and voice_state.get("speaker_wav"):
                kw["speaker_wav"] = voice_state["speaker_wav"]
            elif "speaker" in sig.parameters and voice_state.get("speaker"):
                kw["speaker"] = voice_state["speaker"]
            if "language" in sig.parameters:
                kw["language"] = language
            spd = override_speed if override_speed is not None else speed
            if spd is not None and "speed" in sig.parameters:
                kw["speed"] = spd
            if temperature is not None and "temperature" in sig.parameters:
                kw["temperature"] = temperature
            return kw

        def _synthesize(override_speed: float | None = None) -> np.ndarray:
            kw = _build_kwargs(override_speed)
            try:
                raw = tts.tts(**kw)
            except TypeError:
                raw = tts.tts(text)
            arr = np.asarray(raw, dtype=np.float32)
            arr = _strip_tts_silence(arr, self.sample_rate)
            arr = _compress_internal_silence(arr, self.sample_rate)
            return arr

        effective_speed = speed if speed is not None else 1.0
        audio = _synthesize()

        # T4: silent output retry — mostly-silent clips at elevated speed, retry at 1.0
        silence_frac = float(np.mean(np.abs(audio) < 0.005))
        if silence_frac > _XTTS_SILENCE_WARN and effective_speed > 1.1:
            logger.warning(
                "XTTS silent output (silence=%.2f speed=%.2f), retrying at speed=1.0",
                silence_frac, effective_speed,
            )
            retry = _synthesize(override_speed=1.0)
            retry_silence = float(np.mean(np.abs(retry) < 0.005))
            if retry_silence < silence_frac:
                audio = retry
                silence_frac = retry_silence

        # T5: hallucination guard — audio far longer than CPS-expected duration
        cps = _XTTS_CPS.get(language, 13.0)
        expected_s = max(len(text) / cps, 0.1)
        actual_s = len(audio) / self.sample_rate
        if actual_s > expected_s * _XTTS_MAX_TTS_RATIO:
            if effective_speed > 1.0:
                logger.warning(
                    "XTTS hallucination (actual=%.2fs expected=%.2fs ratio=%.1f), retrying at speed=1.0",
                    actual_s, expected_s, actual_s / expected_s,
                )
                retry = _synthesize(override_speed=1.0)
                retry_s = len(retry) / self.sample_rate
                if retry_s <= expected_s * _XTTS_MAX_TTS_RATIO:
                    audio = retry
                    actual_s = retry_s
                else:
                    logger.warning("XTTS hallucination retry still too long (%.2fs), keeping retry", retry_s)
                    audio = retry
                    actual_s = retry_s
            else:
                logger.warning(
                    "XTTS hallucination at speed=1.0 (actual=%.2fs expected=%.2fs ratio=%.1f), cannot retry",
                    actual_s, expected_s, actual_s / expected_s,
                )

        # T10: peak-limited RMS normalization
        audio = _peak_limited_rms_normalize(audio)

        # T12: QA metrics
        silence_frac = float(np.mean(np.abs(audio) < 0.005))
        rms_db = 20.0 * float(np.log10(float(np.sqrt(np.mean(audio ** 2) + 1e-12)) + 1e-12))
        peak = float(np.max(np.abs(audio)))
        logger.info(
            "XTTS QA: text_len=%d duration=%.2fs expected=%.2fs silence=%.2f rms=%.1fdBFS peak=%.3f",
            len(text), actual_s, expected_s, silence_frac, rms_db, peak,
        )

        wav_bytes = write_wav_bytes_from_pcm_f32(audio, self.sample_rate)
        return EngineResult(sample_rate=self.sample_rate, wav_bytes=wav_bytes)


class Qwen3TTSEngine(TTSEngine):
    name = "qwen3_tts"
    sample_rate = 24000
    supported_languages = ["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"]
    builtin_voices: list[str] = []

    _LANG_MAP = {
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "ru": "Russian",
        "pt": "Portuguese",
        "es": "Spanish",
        "it": "Italian",
    }

    def __init__(self) -> None:
        import qwen_tts  # noqa: F401 – trigger ImportError early if not installed
        self._model = None

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        import torch
        from qwen_tts import Qwen3TTSModel

        model_id = os.getenv("QWEN3_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
        hf_token = os.getenv("HF_TOKEN")
        hf_home = os.getenv("HF_HOME", "/app/models")

        # Build kwargs - ensure we can download missing files
        kwargs = {
            "device_map": "cpu",
            "dtype": torch.float32,
            "trust_remote_code": True,
            "local_files_only": False,
            "force_download": False,
        }
        if hf_home:
            kwargs["cache_dir"] = hf_home
        if hf_token:
            kwargs["token"] = hf_token

        try:
            self._model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
            sr = getattr(self._model, "sample_rate", None)
            if sr:
                self.sample_rate = int(sr)
            return self._model
        except OSError as e:
            if "speech_tokenizer" in str(e) and "preprocessor_config.json" in str(e):
                # Model repo might be incomplete. Try with force_download=True to re-fetch everything
                import logging
                logger = logging.getLogger("pocket_studio")
                logger.warning(f"Model loading failed, retrying with force_download: {e}")
                kwargs["force_download"] = True
                self._model = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
                sr = getattr(self._model, "sample_rate", None)
                if sr:
                    self.sample_rate = int(sr)
                return self._model
            raise

    def clone_to_safetensors(self, reference_wav: Path, safetensors_path: Path) -> None:
        # Qwen3-TTS conditions on reference audio at generation time (like XTTSv2)
        safetensors_path.write_bytes(b"QWEN3_TTS")

    def load_voice_state(self, voice_prompt: str | Path) -> Any:
        if isinstance(voice_prompt, Path) and voice_prompt.suffix == ".safetensors":
            ref_wav = voice_prompt.parent / "reference.wav"
            if not ref_wav.exists():
                raise FileNotFoundError(str(ref_wav))
            return {"speaker_wav": str(ref_wav), "language": "en"}
        return {"speaker_wav": str(voice_prompt), "language": "en"}

    def generate_wav(self, voice_state: Any, text: str, speed: float | None, temperature: float | None) -> EngineResult:
        if not isinstance(voice_state, dict):
            raise TypeError("Qwen3-TTS engine expects dict voice_state")

        model = self._get_model()
        speaker_wav = voice_state.get("speaker_wav")
        lang_code = (voice_state.get("language") or "en").lower()
        if lang_code.startswith("zh"):
            lang_code = "zh"
        language = self._LANG_MAP.get(lang_code, "English")

        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=speaker_wav,
            ref_text=None,
        )
        wav_bytes = write_wav_bytes_from_pcm_f32(wavs[0], int(sr))
        return EngineResult(sample_rate=int(sr), wav_bytes=wav_bytes)


def create_engine(engine_name: str) -> TTSEngine:
    if engine_name == "pocket_tts":
        try:
            return PocketTTSEngine()
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "Pocket TTS dependencies are not installed. Rebuild with INSTALL_TTS_DEPS=1 or set TTS_ENGINE=dummy."
            ) from e
    if engine_name in {"xtts_v2", "xtts-v2", "xtts"}:
        try:
            return XTTSEngine()
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "XTTS dependencies are not installed. Rebuild with INSTALL_TTS_DEPS=1 or set TTS_ENGINE=dummy."
            ) from e
    if engine_name in {"qwen3_tts", "qwen3-tts", "qwen3"}:
        try:
            return Qwen3TTSEngine()
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "Qwen3-TTS dependencies are not installed. Install requirements-qwen3-tts.txt or set TTS_ENGINE=dummy."
            ) from e
    return DummyEngine()
