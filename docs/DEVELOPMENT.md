# Development Guide

This guide covers development practices, testing, and contribution guidelines for Pocket Studio.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Node.js 20+ (for frontend development)

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_HANDLE/pocket-studio.git
cd pocket-studio
```

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-tts.txt  # For TTS functionality
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running Tests

### Run All Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Run Tests with Coverage

```bash
cd backend
python -m pytest tests/ -v --cov=backend --cov-report=term-missing
```

### Run Specific Test File

```bash
cd backend
python -m pytest tests/test_api.py -v
```

### Test Organization

| File | Description |
|------|-------------|
| `tests/test_api.py` | API endpoint tests |
| `tests/test_config.py` | Configuration tests |
| `tests/test_schemas.py` | Schema validation tests |
| `tests/test_services.py` | Service layer tests |
| `tests/test_utils.py` | Utility function tests |

## Running the Application

### Using Docker (Recommended)

```bash
docker compose --profile xtts-v2 up --build
```

### Using Python Directly

```bash
cd backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Code Style

### Python

- Follow PEP 8
- Use type hints throughout
- Add docstrings to all public functions and classes
- Maximum line length: 100 characters

### Imports

Use absolute imports within the `backend` package:

```python
# Correct
from backend.config.settings import Settings
from backend.services.audio import AudioService

# Avoid
from .config import settings
```

## Project Structure

```
backend/
├── __init__.py           # Public API exports
├── main.py               # Application entry point
├── config/
│   ├── __init__.py
│   └── settings.py       # Settings management
├── schemas/
│   ├── __init__.py
│   ├── requests.py       # Request models
│   └── responses.py      # Response models
├── services/
│   ├── __init__.py
│   ├── audio.py          # Audio processing
│   └── voice.py          # Voice management
├── api/
│   ├── __init__.py
│   └── routes.py         # API routes
├── utils/
│   ├── __init__.py
│   └── logging.py        # Logging utilities
└── tests/
    ├── conftest.py       # Pytest fixtures
    ├── test_api.py
    ├── test_config.py
    ├── test_schemas.py
    ├── test_services.py
    └── test_utils.py
```

## Adding a New TTS Engine

1. Create a new class in `tts_engine.py` implementing `TTSEngine`:

```python
class MyTTSEngine(TTSEngine):
    @property
    def name(self) -> str:
        return "my_tts"

    @property
    def sample_rate(self) -> int:
        return 24000

    def clone_to_safetensors(self, ref_path: Path, output_path: Path) -> None:
        # Implementation
        pass

    def load_voice_state(self, voice_id: str | Path) -> dict:
        # Implementation
        pass

    def generate_wav(
        self,
        voice_state: dict,
        text: str,
        speed: float | None,
        temperature: float | None,
    ) -> GenerateResult:
        # Implementation
        pass
```

2. Register in `create_engine()` factory function

3. Add tests for the new engine

## Docker Development

### Build Image

```bash
docker compose build xtts-v2
```

### Run Container

```bash
docker compose --profile xtts-v2 up
```

### View Logs

```bash
docker compose logs -f xtts-v2
```

### Shell into Container

```bash
docker compose exec xtts-v2 bash
```

## Troubleshooting

### Tests Fail with Module Not Found

Ensure you're running tests from the correct directory:

```bash
cd backend
python -m pytest tests/ -v
```

### Docker Build Fails

Clear Docker cache and rebuild:

```bash
docker compose build --no-cache xtts-v2
```

### Port Already in Use

Check what's using port 8000:

```bash
lsof -i :8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## CI/CD

All tests must pass before merging. Run locally:

```bash
python -m pytest tests/ -v --cov=backend
```