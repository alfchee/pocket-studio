import inspect
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wave


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
        if not isinstance(voice_state, dict):
            raise TypeError("XTTS engine expects dict voice_state")

        tts = self._get_tts()
        sig = inspect.signature(tts.tts)
        kwargs: dict[str, Any] = {}
        kwargs["text"] = text

        if "speaker_wav" in sig.parameters and voice_state.get("speaker_wav"):
            kwargs["speaker_wav"] = voice_state["speaker_wav"]
        elif "speaker" in sig.parameters and voice_state.get("speaker"):
            kwargs["speaker"] = voice_state["speaker"]

        language = (voice_state.get("language") or "es").strip()
        if "language" in sig.parameters:
            kwargs["language"] = language
        if speed is not None and "speed" in sig.parameters:
            kwargs["speed"] = speed
        if temperature is not None and "temperature" in sig.parameters:
            kwargs["temperature"] = temperature

        try:
            audio = tts.tts(**kwargs)
        except TypeError:
            audio = tts.tts(text)
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
