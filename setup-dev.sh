#!/usr/bin/env bash
# setup-dev.sh — Local development setup for pocket-studio (Qwen3-TTS)
# Creates .venv and installs qwen3-tts dependencies using CPU-only PyTorch.
# Never installs into the system Python.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# Prefer python3.11 to match Docker images; fall back to python3
if command -v python3.11 &>/dev/null; then
    PYTHON="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
    echo "WARNING: python3.11 not found; using $(python3 --version). Docker images use Python 3.11."
else
    echo "ERROR: Python 3 is required but not found." >&2
    exit 1
fi

echo "Using $PYTHON ($(${PYTHON} --version))"

# Check for sox — required by librosa at runtime (not a Python package)
if ! command -v sox &>/dev/null; then
    echo ""
    echo "WARNING: sox is not installed. It is required by librosa for audio processing."
    echo "  Ubuntu/Debian: sudo apt-get install sox libsox-fmt-all"
    echo "  macOS:         brew install sox"
    echo "  Model download and TTS generation will fail without it."
    echo ""
fi

# Check that the local models directory is user-writable.
# Docker volumes create ./models as root; running the download script against it
# will fail with Permission denied. Fix with: sudo chown -R $USER ./models
MODELS_DIR="$PROJECT_ROOT/models"
if [ -d "$MODELS_DIR" ] && [ ! -w "$MODELS_DIR" ]; then
    echo ""
    echo "WARNING: $MODELS_DIR exists but is not writable by the current user."
    echo "This was likely created by Docker (as root). Fix it before downloading the model:"
    echo "  sudo chown -R \$USER $MODELS_DIR"
    echo ""
elif [ ! -d "$MODELS_DIR" ]; then
    mkdir -p "$MODELS_DIR"
fi

# Create venv if it does not exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Activate for the duration of this script
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Upgrading pip ..."
pip install --quiet --upgrade pip

echo "Installing base backend requirements ..."
pip install --quiet -r "$PROJECT_ROOT/backend/requirements.txt"

echo "Installing Qwen3-TTS requirements (CPU-only PyTorch) ..."
pip install --quiet \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r "$PROJECT_ROOT/backend/requirements-qwen3-tts.txt"

echo ""
echo "Setup complete."
echo ""
echo "Activate the venv:"
echo "  source .venv/bin/activate"
echo ""
echo "Download the model locally (HF_TOKEN only needed for gated repos):"
echo "  HF_HOME=./models python docker/download_model.py"
echo ""
echo "Run the backend:"
echo "  TTS_ENGINE=qwen3_tts HF_HOME=./models uvicorn backend.main:app --reload"
