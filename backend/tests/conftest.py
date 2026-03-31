"""Pytest configuration and fixtures for Pocket Studio tests."""

import os
import sys
from pathlib import Path

# Ensure project root is importable (parent of backend/)
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Clear any Docker-related environment variables that might interfere with tests
docker_vars = ['PORT', 'VOICES_DIR', 'OUTPUTS_DIR', 'MODELS_DIR', 'STATIC_DIR', 'HF_HOME', 'TTS_CACHE_DIR', 'TRANSFORMERS_CACHE']
for key in docker_vars:
    if key in os.environ:
        del os.environ[key]

# Clear pydantic-settings cache to ensure fresh settings
from backend.config import settings
if hasattr(settings, 'get_settings'):
    try:
        settings.get_settings.cache_clear()
    except Exception:
        pass
