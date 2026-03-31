# Pocket Studio Documentation

Welcome to the Pocket Studio documentation! This directory contains comprehensive guides and reference documentation.

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Main project overview and quick start |
| [API.md](API.md) | Complete API reference with examples |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design decisions |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development guide and testing documentation |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branching strategy and CI/CD pipeline |

## Quick Links

### For Users
- [Quick Start Guide](../README.md#-get-started-zero-config)
- [API Reference](API.md)
- [Supported Languages](../README.md#-multilingual-power--powered-by-xtts-v2)

### For Developers
- [Architecture Overview](ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)
- [Testing Documentation](DEVELOPMENT.md#testing)

## Project Structure

```
pocket-studio/
├── backend/
│   ├── api/           # FastAPI routes
│   ├── config/        # Settings management
│   ├── schemas/       # Pydantic models
│   ├── services/      # Business logic
│   ├── utils/         # Utilities
│   ├── main.py        # Application entry point
│   └── tts_engine.py  # TTS engine interfaces
├── docker/            # Docker configurations
├── docs/              # This documentation
├── frontend/          # React frontend
└── tests/            # Test suite
```

## Getting Help

If you encounter issues:
1. Check the [FAQ](../README.md#-faq) in the main README
2. Review the [Development Guide](DEVELOPMENT.md)
3. Open an issue on GitHub