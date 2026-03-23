## Arquitectura Técnica (Propuesta)

### Objetivo
Aplicación auto-alojada y 100% local para:
- Clonar una voz a partir de 5–10s de audio y persistir un embedding reutilizable.
- Generar audio TTS en .wav (24kHz) a partir de texto y una voz (predefinida o clonada).

### Componentes
- **Frontend (React/TS)**: UI para cargar audio, seleccionar voz, configurar parámetros y reproducir/descargar resultados.
- **Backend (FastAPI/Python 3.11+)**: API REST para clonación, generación, listado de voces, y streaming/descarga de audio.
- **Volúmenes**:
  - `./voices`: persistencia de voces clonadas (embeddings + metadata).
  - `./outputs` (opcional): cache/persistencia de audios generados.
  - `./models` (opcional): pesos/artefactos del modelo para operar offline.

### Despliegue (Docker Compose)
- `backend`:
  - Expone `:8000` interno y se publica como `http://localhost:8000` (o sólo vía proxy).
  - Dependencias de sistema: `ffmpeg` para decodificar `.mp3` y normalizar audio.
- `frontend`:
  - Servidor estático (recomendado: Nginx) que sirve la SPA.
  - Proxy `/api/*` hacia el contenedor `backend` para evitar CORS en entorno local.

### Flujo de Datos
1. Usuario sube audio (wav/mp3) → `POST /api/clone`.
2. Backend:
   - Normaliza audio (mono, 24kHz) y valida duración (5–10s objetivo).
   - Extrae embedding de voz (formato `.safetensors`) y guarda en `./voices/<voice_id>/voice.safetensors`.
   - Guarda metadata (p.ej. `meta.json`) con nombre, fecha, duración, parámetros.
3. Usuario pega texto y selecciona `voice_id` → `POST /api/generate`.
4. Backend genera audio y responde:
   - Opción A (MVP): devuelve `audio/wav` como streaming.
   - Opción B (si se requiere): guarda en `./outputs` y devuelve URL de descarga.

### Contrato de API (MVP)

#### `POST /api/clone`
- **Input**: `multipart/form-data`
  - `file`: wav/mp3
  - `name` (opcional): nombre amigable
- **Output (JSON)**:
  - `voice_id`: string
  - `name`: string

#### `POST /api/generate`
- **Input (JSON)**:
  - `text`: string
  - `voice_id`: string
  - `speed` (opcional): number
  - `temperature` (opcional): number
- **Output**:
  - `200 audio/wav` (stream)

#### `GET /api/voices`
- **Output (JSON)**: lista de voces disponibles

#### `GET /api/health`
- **Output (JSON)**: estado del backend (para healthcheck de Docker)

### Persistencia
- Estructura sugerida:
  - `voices/<voice_id>/voice.safetensors`
  - `voices/<voice_id>/meta.json`
  - `voices/<voice_id>/reference.wav` (opcional, normalizado)

### Rendimiento (Intel i7 12th Gen)
- Minimizar overhead:
  - Precargar modelo al levantar el backend (warm start).
  - Controlar hilos: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, y afinidad si aplica.
- Inferencia:
  - Camino 1: `onnxruntime` (CPU) si el modelo lo soporta de forma estable.
  - Camino 2: `torch` CPU optimizado como fallback.

### Seguridad (local por defecto)
- Límite de tamaño de archivos en `POST /api/clone`.
- Validación de tipos y normalización con `ffmpeg`.
- Restringir origen/host por configuración (por defecto `localhost`).

