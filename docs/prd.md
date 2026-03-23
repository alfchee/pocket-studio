# PRD: Estudio "Podcast-in-a-Box" (Local & Private)

## 1. Resumen del Producto

Una solución auto-alojada y compacta que permite a creadores de contenido (podcasters) generar voz sintética de alta calidad y realizar clonación de voz (Voice Cloning) de forma 100% local. Utiliza el modelo Pocket TTS (100M) para garantizar que el procesamiento ocurra en tiempo real incluso sin una GPU dedicada.

## 2. Objetivos

1. Privacidad Total: Los datos de voz y guiones nunca salen de la red local.
2. Baja Fricción: Una interfaz donde solo se pegue el texto y se obtenga el audio.
3. Portabilidad: Despliegue mediante Docker para evitar problemas de dependencias en Windows/Intel.

## 3. Persona de Usuario 

- Primario: 
Podcaster  con equipo Intel i7, que busca agilizar la post-producción o crear segmentos narrados sin necesidad de grabar cada toma.

## 4. Requisitos Funcionales 

- (MVP)RF01: Clonación de Voz (Zero-Shot)
El sistema debe permitir cargar un archivo de audio (.wav/.mp3) de entre 5 y 10 segundos. El sistema debe extraer un "embedding" de voz (un archivo .safetensors) para ser reutilizado.
- RF02: Síntesis de Texto a Voz (TTS)
  - El usuario puede ingresar texto plano o guiones largos. 
  - Opción para seleccionar entre voces predefinidas o voces clonadas previamente. 
  - Control de parámetros básicos: Velocidad (Speed) y Estabilidad (Temperature).
- RF03: Gestión de Audio
  - Reproductor integrado para previsualizar el resultado.
  - Botón de descarga para el archivo final en formato .wav de alta calidad (24kHz).

## 5. Arquitectura Técnica

### Stack Tecnológico

- **Model Core:** pocket-tts (100M params).
- **Backend:** FastAPI (Python 3.11+).
- **Frontend:** React application (TypeScript + Reactstrap + Easy-peasy).
- **Orquestación:** Docker + Docker Compose.
- **Optimización CPU:** Uso de onnxruntime o torch (modo CPU) optimizado para instrucciones AVX-512 de Intel 12va Gen.

## Estructura del Contenedor

- Container A (Backend): Expone endpoints REST (/clone, /generate, /voices).
- Container B (Frontend): Interfaz visual que consume la API.
- Volúmenes: Carpeta compartida ./voices para persistir las voces clonadas de tu papá.

## 6. Diseño de la API (Endpoints Clave)

| Método | Endpoint | Descripción |
| --- | --- | --- |
| POST | /api/clone | Sube audio de referencia y devuelve un voice_id. |
| POST | /api/generate | Recibe texto + voice_id y devuelve el stream de audio.| 
|GET | /api/voices | Lista las voces disponibles en el volumen local. |

## 7. Requisitos de Rendimiento (Intel i7 12th Gen)

- Latencia (TTFB): El audio debe empezar a generarse en menos de 300ms.
- Real-Time Factor (RTF): Debe ser inferior a 0.5 (generar 1 minuto de audio en menos de 30 segundos).
- Consumo CPU: No debe exceder los 4 núcleos de CPU.

## 8. Roadmap Futuro

- v1.1: Integración con RSS para subir el audio directamente a plataformas de Podcast.
- v1.2: Soporte para diálogos entre dos voces (Entrevistas automáticas).
- v1.3: Limpieza de audio automática (denoiser) antes de la clonación.
