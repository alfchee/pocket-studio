"""Response schemas for Pocket Studio API."""

from pydantic import BaseModel


class HealthInfo(BaseModel):
    """Health check response schema.

    Attributes:
        status: Health status (usually "ok")
        engine: Name of the active TTS engine
        sample_rate: Output sample rate
    """

    status: str
    engine: str
    sample_rate: int | None = None


class VoiceInfo(BaseModel):
    """Voice information schema.

    Attributes:
        voice_id: Unique identifier for the voice
        name: Human-readable voice name
        builtin: Whether this is a built-in voice
    """

    voice_id: str
    name: str
    builtin: bool = False


class CloneResponse(BaseModel):
    """Response schema for voice cloning.

    Attributes:
        voice_id: Unique identifier for the cloned voice
        name: Human-readable voice name
    """

    voice_id: str
    name: str


class ErrorResponse(BaseModel):
    """Error response schema.

    Attributes:
        detail: Error message
    """

    detail: str