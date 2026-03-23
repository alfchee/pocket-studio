## Plan de Desarrollo (MVP → v1.0)

### Alcance MVP
- Clonación de voz zero-shot (audio 5–10s) y persistencia local del embedding.
- Generación TTS desde texto con selección de voz (predefinida o clonada).
- Parámetros: `speed` y `temperature`.
- Reproductor y descarga `.wav` 24kHz.
- Docker Compose con 2 contenedores (frontend + backend) y volumen `./voices`.

### Fase 0 — Base del repositorio
- Definir estructura `backend/`, `frontend/`, `docker/`, `docs/`.
- Añadir `docker-compose.yml` con redes, volúmenes y healthchecks.
- Añadir configuración de entorno (p.ej. `.env.example`) para rutas y límites.

### Fase 1 — Backend API (sin modelo)
- Crear servicio FastAPI con:
  - `POST /api/clone` (valida archivo, normaliza audio, devuelve `voice_id` simulado).
  - `GET /api/voices` (lee del volumen `./voices`).
  - `POST /api/generate` (devuelve wav de prueba).
  - `GET /api/health`.
- Definir esquema de persistencia en `./voices` (meta.json + placeholder embedding).
- Añadir pruebas básicas (pytest) para endpoints y validaciones.

### Fase 2 — Integración Pocket TTS
- Integrar librería/modelo `pocket-tts`:
  - Implementar extracción real de embedding y guardado `.safetensors`.
  - Implementar generación real wav 24kHz.
- Decidir backend de inferencia:
  - Priorizar `onnxruntime` si hay export/artefactos disponibles.
  - Mantener fallback con `torch` CPU.
- Afinar rendimiento (warmup, hilos, colas de trabajo si se requiere).

### Fase 3 — Frontend UI
- Crear SPA con:
  - Pantalla de clonación (subida de audio + nombre + listado de voces).
  - Pantalla de generación (texto largo, selector de voz, sliders para speed/temperature).
  - Reproductor integrado y botón de descarga.
- Integración con API mediante proxy `/api`.

### Fase 4 — End-to-end y empaquetado
- E2E manual guiado: clonar → generar → reproducir → descargar.
- Límites y ergonomía:
  - Validar longitud de texto y tamaño de archivo.
  - Mensajes de error claros (400/422) y estados de carga.
- Documentación:
  - README con instalación (Docker) y uso básico.

### Criterios de aceptación MVP
- `docker compose up` levanta frontend y backend sin pasos extra.
- `POST /api/clone` crea `voices/<voice_id>/voice.safetensors`.
- `POST /api/generate` responde `audio/wav` 24kHz.
- UI permite completar el flujo sin consola.

### Riesgos y mitigaciones
- Decodificación de mp3 inconsistente → usar `ffmpeg` en contenedor.
- Rendimiento CPU variable → exponer configuración de hilos y batch size.
- Peso del modelo/offline → soportar `./models` como volumen y descarga opcional.

