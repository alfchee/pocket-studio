import io
import os
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


def _make_wav_bytes(duration_s: float = 6.0, sample_rate: int = 24000) -> bytes:
    frames = int(duration_s * sample_rate)
    pcm = bytearray()
    for _ in range(frames):
        pcm.extend((0).to_bytes(2, byteorder="little", signed=True))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm))
    return buf.getvalue()


@pytest.fixture()
def voices_dir(tmp_path: Path) -> Path:
    voices = tmp_path / "voices"
    os.environ["VOICES_DIR"] = str(voices)
    os.environ["MAX_AUDIO_UPLOAD_SIZE_MB"] = "5"
    os.environ["MAX_TEXT_LENGTH"] = "5000"
    os.environ["TTS_ENGINE"] = "dummy"
    return voices


@pytest.fixture()
def client(voices_dir: Path) -> TestClient:
    app = create_app()
    return TestClient(app)


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_clone_and_list_voices(client: TestClient, voices_dir: Path) -> None:
    wav_bytes = _make_wav_bytes()
    files = {"file": ("ref.wav", wav_bytes, "audio/wav")}
    data = {"name": "test-voice"}
    res = client.post("/api/clone", files=files, data=data)
    assert res.status_code == 200
    payload = res.json()
    assert "voice_id" in payload
    assert payload["name"] == "test-voice"

    voice_path = voices_dir / payload["voice_id"]
    assert (voice_path / "reference.wav").exists()
    assert (voice_path / "voice.safetensors").exists()
    assert (voice_path / "meta.json").exists()

    res2 = client.get("/api/voices")
    assert res2.status_code == 200
    voices = res2.json()
    assert any(v["voice_id"] == payload["voice_id"] for v in voices)
    assert any(v.get("builtin") is True for v in voices)


def test_generate_requires_known_voice(client: TestClient) -> None:
    res = client.post("/api/generate", json={"text": "hi", "voice_id": "missing"})
    assert res.status_code == 404


def test_generate_returns_wav(client: TestClient) -> None:
    wav_bytes = _make_wav_bytes()
    res = client.post("/api/clone", files={"file": ("ref.wav", wav_bytes, "audio/wav")})
    voice_id = res.json()["voice_id"]

    res2 = client.post("/api/generate", json={"text": "hello", "voice_id": voice_id})
    assert res2.status_code == 200
    assert res2.headers["content-type"].startswith("audio/wav")
    assert len(res2.content) > 44


def test_generate_stream_returns_mp3(client: TestClient) -> None:
    wav_bytes = _make_wav_bytes()
    res = client.post("/api/clone", files={"file": ("ref.wav", wav_bytes, "audio/wav")})
    voice_id = res.json()["voice_id"]

    res2 = client.post("/api/generate_stream", json={"text": "hello. world.", "voice_id": voice_id})
    assert res2.status_code == 200
    assert res2.headers["content-type"].startswith("audio/mpeg")
    assert len(res2.content) > 10
