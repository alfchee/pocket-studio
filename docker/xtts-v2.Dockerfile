# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Python dependencies and download XTTS-v2 model
FROM python:3.11-slim AS python-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
COPY backend/requirements-tts.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
RUN pip install --user --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r requirements-tts.txt && \
    python -c "from TTS.api import TTS; print('coqui TTS import ok')"

COPY docker/download_verify.py /app/download_verify.py
RUN python /app/download_verify.py \
    --model-name "tts_models/multilingual/multi-dataset/xtts_v2" \
    --cache-dir /app/models \
    --max-retries 3 || exit 1

RUN echo "Verifying XTTS-v2 model files:" && \
    find /app/models -type f \( -name "*.pth" -o -name "*.safetensors" -o -name "*.json" \) 2>/dev/null | head -20 || echo "Model files check complete"

# Stage 3: Final
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=python-builder /root/.local /root/.local
COPY --from=python-builder /app/models /app/models
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV TTS_ENGINE=xtts_v2
ENV STATIC_DIR=/app/static
ENV COQUI_TOS_AGREED=1
ENV TTS_CACHE_DIR=/app/models
ENV HF_HOME=/app/models/hf
ENV TRANSFORMERS_CACHE=/app/models/hf
COPY backend /app/backend
COPY --from=frontend-builder /frontend/dist /app/static
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
