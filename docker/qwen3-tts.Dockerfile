# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Python dependencies
FROM python:3.11-slim AS python-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    sox \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
COPY backend/requirements-qwen3-tts.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
RUN pip install --user --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r requirements-qwen3-tts.txt && \
    python -c "from qwen_tts import Qwen3TTSModel; print('qwen3_tts import ok')"

# Stage 3: Final
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    sox \
    curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY backend/ .
COPY --from=frontend-builder /frontend/dist /app/static
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV TTS_ENGINE=qwen3_tts
ENV STATIC_DIR=/app/static
ENV HF_HOME=/app/models
ENV QWEN3_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-Base
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
