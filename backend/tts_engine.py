import inspect
import io
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
    return DummyEngine()
