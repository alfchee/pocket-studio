"""Request schemas for Pocket Studio API."""

from pydantic import BaseModel, Field, model_validator


class GenerateRequest(BaseModel):
    """Request schema for audio generation.

    Attributes:
        text: Text to synthesize
        voice_id: ID of a previously cloned voice
        speaker_wav_path: Path to a speaker reference audio file
        language: Language code for synthesis
        speed: Speech speed factor
        temperature: Generation temperature
    """

    text: str = Field(min_length=1)
    voice_id: str | None = Field(default=None, min_length=1)
    speaker_wav_path: str | None = Field(default=None, min_length=1)
    language: str | None = Field(default=None, min_length=2, max_length=10)
    speed: float | None = Field(default=None, ge=0.1, le=10.0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def _validate_voice_source(self) -> "GenerateRequest":
        """Validate that either voice_id or speaker_wav_path is provided."""
        voice_id = (self.voice_id or "").strip()
        speaker_wav_path = (self.speaker_wav_path or "").strip()

        if voice_id == "" and speaker_wav_path == "":
            raise ValueError("Either voice_id or speaker_wav_path is required")

        self.voice_id = voice_id or None
        self.speaker_wav_path = speaker_wav_path or None
        self.language = (self.language or "").strip() or None

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Hello, world!",
                    "voice_id": "my-voice",
                    "language": "en",
                    "speed": 1.0,
                    "temperature": 0.8,
                }
            ]
        }
    }