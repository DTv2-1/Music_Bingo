# 🚀 Music Bingo - Plan de Expansión de Funcionalidades

**Fecha de creación**: 13 de enero de 2026  
**Versión**: 1.0  
**Estado del proyecto actual**: Music Bingo completamente funcional en producción

---

## 📋 Resumen Ejecutivo

Este documento detalla el plan de implementación para expandir Music Bingo con cuatro nuevas funcionalidades solicitadas por el cliente:

1. **Jingle Creation** - Generación de jingles publicitarios con IA
2. **Karaoke** - Sistema de karaoke con letras sincronizadas
3. **Pub Quiz** - Trivia musical interactiva
4. **Singles Blind Date** - Sistema de matching musical

---

## 🎯 Priorización por Impacto y Viabilidad

| Funcionalidad | Prioridad | Esfuerzo | Impacto Negocio | Sinergia con Sistema Actual |
|---------------|-----------|----------|-----------------|----------------------------|
| **Jingle Creation** | 🔴 ALTA | 2-3 semanas | Alto (nuevo revenue stream) | ⭐⭐⭐⭐⭐ Excelente |
| **Pub Quiz** | 🟡 MEDIA | 1 semana | Medio (engagement) | ⭐⭐⭐⭐ Muy buena |
| **Karaoke** | 🟡 MEDIA | 3-4 semanas | Alto (diversificación) | ⭐⭐⭐ Buena |
| **Singles Blind Date** | 🟢 BAJA | 6-8 semanas | Incierto (MVP requerido) | ⭐ Baja |

---

# 1️⃣ JINGLE CREATION - Generador de Jingles Publicitarios con IA

## 🎯 Objetivo del Proyecto

Permitir a los dueños de pubs crear jingles publicitarios profesionales de 10 segundos de manera autónoma, combinando:
- Texto personalizado convertido a voz (TTS)
- Música de fondo generada por IA
- Mezcla automática y masterización

**Ejemplo de uso**: "Every Wednesday Evening, Happy Hour two for one cocktails between 5pm and 7pm"

---

## 🏗️ Arquitectura Técnica

### Componentes del Sistema

#### **Backend - Django API**
- **Nuevo endpoint**: `/api/generate-jingle`
- **Método**: POST (asíncrono)
- **Tecnologías**:
  - ElevenLabs Text-to-Speech API (ya integrada)
  - ElevenLabs Music Generation API (nuevo)
  - Pydub para mezcla de audio (nuevo)
  - FFmpeg para procesamiento (nuevo)

#### **Frontend - Nueva Sección en UI**
- **Archivo nuevo**: `frontend/jingle.html`
- **Modal integrado** en `game.html` o página independiente
- **Formulario interactivo** con preview en tiempo real
- **Descarga directa** de MP3 generado

#### **Almacenamiento**
- **Carpeta nueva**: `data/jingles/`
- **Estructura**: `{venue_name}_{timestamp}_{uuid}.mp3`
- **Gestión**: Limpieza automática de archivos antiguos (>30 días)

---

## 📊 Flujo de Usuario Detallado

### Paso 1: Acceso al Generador
1. Usuario hace clic en "Create Jingle" desde dashboard
2. Sistema valida autenticación del venue
3. Se abre modal/página con formulario

### Paso 2: Configuración de Texto
1. **Input principal**: Área de texto para mensaje (máx 150 caracteres)
2. **Validación en tiempo real**: contador de caracteres
3. **Sugerencias**: Templates predefinidos
   - Happy Hour
   - Special Events
   - Food Promotions
   - Live Music Nights

### Paso 3: Selección de Voz
1. **Dropdown de voces** con preview de 3 segundos
2. **Opciones**:
   - British Male (formal)
   - British Female (friendly)
   - American Energetic (upbeat)
   - Irish Casual (local)
3. **Botón "Test Voice"** para escuchar muestra

### Paso 4: Configuración Musical
1. **Selector de género musical**:
   - Upbeat Pub Rock
   - Jazzy Piano
   - Irish Folk Guitar
   - Electronic Dance
   - Acoustic Indie
2. **Slider de intensidad**: Subtle → Energetic
3. **Preview de 5 segundos** del estilo seleccionado

### Paso 5: Generación y Preview
1. Botón "Generate Jingle"
2. **Barra de progreso** con estados:
   - Generating voice... (30%)
   - Creating music... (60%)
   - Mixing audio... (80%)
   - Finalizing... (100%)
3. **Tiempo estimado**: 15-30 segundos

### Paso 6: Revisión y Descarga
1. **Player integrado** con waveform visual
2. **Opciones**:
   - Download MP3
   - Regenerate (nuevos parámetros)
   - Save to Library
   - Share via Email

---

## 🔧 Tareas de Implementación Backend

### Tarea 1.1: Configuración de Dependencias
- Agregar `pydub` a `requirements.txt`
- Agregar `ffmpeg-python` a `requirements.txt`
- Instalar FFmpeg en el servidor (DigitalOcean App Platform)
- Documentar proceso de instalación en `DEPLOYMENT.md`

### Tarea 1.2: Integración ElevenLabs Music API
- Investigar endpoints de Music Generation API
- Crear función `generate_music_background(prompt, duration)`
- Implementar manejo de errores y reintentos
- Validar duración mínima/máxima (10 segundos)
- Agregar variable de entorno para límites de uso

### Tarea 1.3: Sistema de Mezcla de Audio
- Crear módulo `backend/api/audio_mixer.py`
- Implementar función `mix_tts_with_music(tts_bytes, music_bytes)`
- Configurar parámetros:
  - Volumen TTS: 100%
  - Volumen música: -6dB (background)
  - Fade in/out: 500ms
  - Normalización de audio
- Agregar compresión MP3 (128kbps)

### Tarea 1.4: Endpoint Asíncrono `/api/generate-jingle`
- Crear view `generate_jingle()` en `views.py`
- Recibir parámetros:
  - `text` (string, requerido)
  - `voice_id` (string, opcional, default del venue)
  - `music_prompt` (string, opcional)
  - `music_genre` (enum, opcional)
  - `duration` (int, default 10)
- Generar UUID único para el jingle
- Crear tarea asíncrona en `tasks_storage`
- Devolver `task_id` inmediatamente

### Tarea 1.5: Worker de Procesamiento
- Crear función `background_jingle_generation(task_id, params)`
- Implementar flujo secuencial:
  1. Llamar a ElevenLabs TTS
  2. Llamar a ElevenLabs Music
  3. Mezclar con pydub
  4. Guardar en `data/jingles/`
  5. Actualizar estado del task
- Manejar errores con mensajes descriptivos
- Implementar logging detallado

### Tarea 1.6: Endpoint de Estado `/api/jingle-tasks/<task_id>`
- Reutilizar sistema existente de `get_task_status()`
- Extender con campos específicos:
  - `progress_percentage` (0-100)
  - `current_step` (tts/music/mixing/finalizing)
  - `audio_url` (cuando esté completo)
  - `duration_seconds` (duración final)
- Implementar polling cada 2 segundos desde frontend

### Tarea 1.7: Endpoint de Descarga `/api/jingles/<uuid>`
- Servir archivo MP3 con `FileResponse`
- Headers correctos: `Content-Type: audio/mpeg`
- Implementar descarga directa vs streaming
- Seguridad: validar que el venue tenga acceso

### Tarea 1.8: Sistema de Limpieza Automática
- Crear comando Django `cleanup_old_jingles`
- Ejecutar diariamente via cron job
- Eliminar archivos >30 días
- Mantener log de eliminaciones
- Notificar si espacio en disco <10%

---

## 🎨 Tareas de Implementación Frontend

### Tarea 2.1: Estructura HTML del Generador
- Crear `frontend/jingle.html` o modal en `game.html`
- Diseño de 4 pasos (wizard):
  - Step 1: Text Input
  - Step 2: Voice Selection
  - Step 3: Music Style
  - Step 4: Generate & Download
- Navegación con botones "Previous"/"Next"
- Indicador de progreso visual (breadcrumbs)

### Tarea 2.2: Formulario de Texto
- Input textarea con contador de caracteres
- Validación en tiempo real (min 10, max 150 chars)
- Dropdown de templates predefinidos
- Botón "Use Template" para insertar
- Información tooltip sobre mejores prácticas

### Tarea 2.3: Selector de Voces
- Cargar lista de voces desde `/api/config`
- Crear cards con preview de cada voz
- Implementar `playVoicePreview(voice_id)` con Howler.js
- Marcar voz seleccionada visualmente
- Guardar preferencia en localStorage

### Tarea 2.4: Selector Musical
- Galería de géneros con iconos
- Preview de 5 segundos al hacer hover
- Slider de intensidad (1-10)
- Visualización del estilo seleccionado
- Botón "Surprise Me" para aleatorio

### Tarea 2.5: Lógica de Generación en `jingle.js`
- Función `generateJingle()` para enviar POST
- Recibir `task_id` y iniciar polling
- Actualizar barra de progreso con WebSocket o polling
- Manejar errores con mensajes user-friendly
- Mostrar tiempo restante estimado

### Tarea 2.6: Player de Preview
- Integrar Howler.js para reproducción
- Waveform visual con canvas o librería
- Controles: Play/Pause/Stop
- Timeline con timestamp actual
- Botón de volumen con slider

### Tarea 2.7: Sistema de Descarga
- Botón "Download MP3" con loading state
- Generar nombre descriptivo del archivo
- Implementar descarga directa con `<a download>`
- Opción "Save to My Jingles" para biblioteca
- Compartir por email (opcional)

### Tarea 2.8: Biblioteca de Jingles
- Nueva sección "My Jingles" en dashboard
- Listar todos los jingles generados del venue
- Preview rápido inline
- Re-download y eliminar
- Filtros por fecha y género musical

---

## 🧪 Testing y Validación

### Tests Unitarios Backend
- Test de generación TTS con ElevenLabs
- Test de generación musical con diferentes prompts
- Test de mezcla de audio con pydub
- Test de manejo de errores (API down, timeout)
- Test de almacenamiento y limpieza de archivos

### Tests de Integración
- Flujo completo end-to-end
- Test de concurrencia (múltiples jingles simultáneos)
- Test de límites de uso (rate limiting)
- Test de performance (tiempo de generación)

### Tests Frontend
- Validación de formularios
- Navegación entre pasos del wizard
- Reproducción de previews
- Descarga de archivos
- Manejo de estados de carga

### Tests de Usuario (UAT)
- Pub owner genera jingle real
- Validar calidad de audio
- Verificar usabilidad del formulario
- Confirmar descarga funciona en todos los browsers
- Testear en mobile

---

## 📈 Métricas de Éxito

### KPIs Técnicos
- Tiempo de generación promedio: <30 segundos
- Tasa de éxito: >95%
- Uptime del servicio: >99%
- Tamaño promedio de archivo: <500KB

### KPIs de Negocio
- Jingles generados por venue/mes
- Tasa de re-generación (insatisfacción)
- Venues que adoptan la funcionalidad
- Feedback score (1-5 estrellas)

---

## 💰 Modelo de Monetización

### Opciones de Pricing
1. **Incluido en plan**: 5 jingles/mes gratis
2. **Pay-per-jingle**: £2 por jingle adicional
3. **Pack de 20**: £30 (descuento 25%)
4. **Enterprise**: Jingles ilimitados

### Control de Límites
- Tabla en base de datos: `jingle_usage`
- Campos: `venue_id`, `month`, `count`, `plan_limit`
- Bloqueo cuando se alcanza límite
- Upsell modal para comprar más

---

## 🚧 Riesgos y Mitigaciones

### Riesgo 1: Costo de APIs
- **Problema**: ElevenLabs cobra por generación
- **Mitigación**: Implementar límites estrictos, caching de voces comunes

### Riesgo 2: Tiempo de Generación Largo
- **Problema**: Usuario espera >1 minuto
- **Mitigación**: Optimizar prompts, usar async correctamente, feedback visual

### Riesgo 3: Calidad de Audio Inconsistente
- **Problema**: Mezcla suena mal con algunos prompts
- **Mitigación**: Normalización automática, presets testeados, opción de re-generar

### Riesgo 4: Abuso del Sistema
- **Problema**: Venue genera 100 jingles para "testear"
- **Mitigación**: Rate limiting, captcha opcional, límites por plan

---

## 📅 Timeline Estimado

### Semana 1: Backend Core
- Días 1-2: Setup ElevenLabs Music API
- Días 3-4: Implementar mixer con pydub
- Día 5: Endpoint asíncrono + tests

### Semana 2: Frontend + Integración
- Días 1-2: UI del generador (HTML/CSS)
- Días 3-4: Lógica JavaScript + player
- Día 5: Integración end-to-end

### Semana 3: Testing + Refinamiento
- Días 1-2: Tests completos
- Días 3-4: Bug fixes y optimizaciones
- Día 5: Deploy a staging + UAT

### Total: **2-3 semanas** con 1 desarrollador full-time

---

# 2️⃣ PUB QUIZ - Sistema de Trivia Musical Interactivo

## 🎯 Objetivo del Proyecto

Transformar el sistema de Music Bingo en un quiz musical interactivo donde los participantes responden preguntas sobre canciones, artistas y décadas mientras escuchan fragmentos de música.

**Ventaja competitiva**: Reutilizar el 80% de la infraestructura existente (pool de canciones, sistema de audio, anuncios AI con trivia).

---

## 🏗️ Arquitectura Técnica

### Componentes Reutilizables
- ✅ `data/pool.json` - Ya contiene 250+ canciones
- ✅ `data/announcements_ai.json` - Ya tiene trivia para cada canción
- ✅ Sistema de audio con Howler.js
- ✅ Backend Django con endpoints de canciones
- ✅ Sistema de TTS para anunciar respuestas

### Componentes Nuevos
- **Archivo**: `frontend/quiz.html`
- **Lógica**: `frontend/quiz.js`
- **Endpoint**: `/api/quiz/generate-round` (opcional)
- **Storage**: localStorage para leaderboard

---

## 📊 Flujo de Usuario Detallado

### Modo de Juego: Individual vs Teams

#### **Modo Individual**
1. Jugador entra a `quiz.html`
2. Ingresa nickname
3. Selecciona dificultad (Easy/Medium/Hard)
4. Responde 10 preguntas
5. Ve su score y ranking

#### **Modo Teams**
1. Host crea sesión de quiz
2. Genera código de sala (6 dígitos)
3. Jugadores se unen con código
4. Host controla avance de preguntas
5. Leaderboard en tiempo real

---

## 🎮 Tipos de Preguntas

### Tipo 1: Identificación de Canción
- **Formato**: Reproducir 5 segundos de intro
- **Pregunta**: "¿Qué canción es esta?"
- **Opciones**: 4 títulos (1 correcto, 3 distractores)
- **Puntos**: 10 puntos
- **Tiempo**: 15 segundos para responder

### Tipo 2: Identificación de Artista
- **Formato**: Reproducir chorus de 8 segundos
- **Pregunta**: "¿Quién interpreta esta canción?"
- **Opciones**: 4 artistas (misma década/género)
- **Puntos**: 15 puntos
- **Tiempo**: 15 segundos

### Tipo 3: Década Musical
- **Formato**: Reproducir 10 segundos
- **Pregunta**: "¿De qué década es esta canción?"
- **Opciones**: 4 décadas (ej: 70s, 80s, 90s, 2000s)
- **Puntos**: 5 puntos
- **Tiempo**: 10 segundos

### Tipo 4: Trivia Cultural
- **Formato**: Reproducir fragmento + mostrar trivia de `announcements_ai.json`
- **Pregunta**: Extraída del campo `trivia`
- **Opciones**: 4 respuestas generadas por IA
- **Puntos**: 20 puntos (más difícil)
- **Tiempo**: 20 segundos

### Tipo 5: Speed Round
- **Formato**: Solo 2 segundos de audio
- **Pregunta**: "¿Canción A o Canción B?"
- **Opciones**: 2 opciones
- **Puntos**: 5 puntos
- **Tiempo**: 5 segundos (rápido)

---

## 🔧 Tareas de Implementación Backend

### Tarea 3.1: Endpoint de Generación de Quiz
- Crear `/api/quiz/generate-round`
- Parámetros:
  - `num_questions` (default: 10)
  - `difficulty` (easy/medium/hard)
  - `decades` (array de décadas a incluir)
  - `question_types` (array de tipos de pregunta)
- Lógica:
  1. Seleccionar canciones aleatorias de `pool.json`
  2. Generar distractores inteligentes (mismo género/década)
  3. Incluir trivia de `announcements_ai.json`
  4. Devolver JSON con preguntas estructuradas

### Tarea 3.2: Generación de Distractores Inteligentes
- Crear función `generate_distractors(correct_answer, pool, count=3)`
- Para artistas: filtrar por misma década
- Para canciones: filtrar por mismo género
- Evitar respuestas obvias (muy diferentes)
- Aleatorizar orden de opciones

### Tarea 3.3: Sistema de Scoring
- Crear modelo `QuizScore` en Django
- Campos:
  - `venue_id`
  - `player_name`
  - `score`
  - `accuracy` (%)
  - `avg_time` (segundos por pregunta)
  - `timestamp`
- Endpoint `/api/quiz/leaderboard?venue_id=X`

### Tarea 3.4: Validación de Respuestas
- Endpoint `/api/quiz/check-answer`
- Parámetros:
  - `question_id`
  - `selected_answer`
  - `time_taken` (segundos)
- Devolver:
  - `is_correct` (boolean)
  - `correct_answer` (string)
  - `points_earned` (int)
  - `explanation` (trivia adicional)

### Tarea 3.5: Sistema de Sesiones Multi-jugador (Opcional)
- Crear modelo `QuizSession`
- Usar WebSockets o polling para sincronización
- Host controla avance de preguntas
- Todos los jugadores ven la misma pregunta simultáneamente

---

## 🎨 Tareas de Implementación Frontend

### Tarea 4.1: Pantalla de Inicio
- Header: "Music Pub Quiz"
- Formulario de entrada:
  - Nickname (requerido)
  - Selección de dificultad
  - Checkboxes de décadas
- Botón "Start Quiz"
- Mostrar leaderboard del día

### Tarea 4.2: Interfaz de Pregunta
- Sección superior: Número de pregunta (1/10)
- Centro: Pregunta en texto grande
- Reproductor de audio con waveform animado
- 4 botones de opciones (A, B, C, D)
- Timer visual (countdown circular)
- Indicador de puntos actuales

### Tarea 4.3: Lógica de Juego en `quiz.js`
- Función `loadQuestion(index)` para cargar pregunta
- Reproducir fragmento de audio automáticamente
- Iniciar countdown al terminar audio
- Función `selectAnswer(option)` para registrar respuesta
- Calcular puntos basado en tiempo restante
- Avanzar automáticamente a siguiente pregunta

### Tarea 4.4: Feedback Visual
- Respuesta correcta: Botón verde + animación de confetti
- Respuesta incorrecta: Botón rojo + mostrar respuesta correcta
- Reproducir audio completo (15 segundos) después de responder
- Mostrar trivia adicional si existe
- Delay de 5 segundos antes de siguiente pregunta

### Tarea 4.5: Pantalla de Resultados
- Mostrar score final
- Precisión (% respuestas correctas)
- Tiempo promedio por pregunta
- Comparación con leaderboard
- Botones:
  - "Play Again"
  - "View Leaderboard"
  - "Share Score"

### Tarea 4.6: Leaderboard
- Tabla con top 10 jugadores del día
- Columnas: Rank, Nombre, Score, Precisión
- Highlight del jugador actual
- Filtros: Hoy, Esta Semana, Todos los Tiempos
- Reseteo automático mensual

### Tarea 4.7: Modo Multijugador (Opcional)
- Host genera código de sala
- Otros jugadores ingresan código
- Lobby muestra jugadores conectados
- Host inicia quiz
- Sincronización de preguntas
- Leaderboard en tiempo real

---

## 🧪 Testing y Validación

### Tests Backend
- Test de generación de quiz con diferentes parámetros
- Test de generación de distractores
- Test de validación de respuestas
- Test de cálculo de scoring
- Test de leaderboard con múltiples jugadores

### Tests Frontend
- Test de reproducción de audio
- Test de countdown timer
- Test de selección de respuestas
- Test de navegación entre preguntas
- Test de persistencia de datos en localStorage

### Tests de Usuario
- Jugador completa quiz completo
- Verificar dificultad progresiva
- Validar que leaderboard actualiza
- Testear en mobile y desktop

---

## 📈 Métricas de Éxito

### KPIs
- Quizzes completados por venue/semana
- Tasa de finalización (% que terminan 10 preguntas)
- Precisión promedio de jugadores
- Tiempo promedio por quiz
- Re-engagement (jugadores que regresan)

---

## 📅 Timeline Estimado

### Semana 1: Backend + Lógica de Quiz
- Días 1-2: Endpoint de generación + distractores
- Días 3-4: Sistema de scoring + leaderboard
- Día 5: Tests unitarios

### Semana 2: Frontend
- Días 1-2: UI de quiz (HTML/CSS)
- Días 3-4: Lógica de juego (quiz.js)
- Día 5: Integración + tests

### Total: **1-2 semanas** (aprovechando infraestructura existente)

---

# 3️⃣ KARAOKE - Sistema de Karaoke con Letras Sincronizadas

## 🎯 Objetivo del Proyecto

Agregar modo karaoke al sistema Music Bingo, mostrando letras sincronizadas con la música para que los clientes del pub puedan cantar.

**Desafío técnico**: iTunes API no provee lyrics sincronizadas, requiere integración con servicios externos.

---

## 🏗️ Arquitectura Técnica

### Componentes Reutilizables
- ✅ Sistema de reproducción de audio (Howler.js)
- ✅ Pool de canciones con preview URLs
- ✅ UI de diseño profesional

### Componentes Nuevos
- **API de Letras**: Musixmatch API o Genius API
- **Parser LRC**: Para formato de subtítulos sincronizados
- **Componente de Display**: Letras con highlight
- **Sistema de Cola**: Queue de canciones solicitadas

---

## 📊 Flujo de Usuario Detallado

### Rol 1: Operador del Pub (DJ/Host)
1. Accede a `karaoke.html` desde dashboard
2. Ve lista de canciones disponibles con letras
3. Puede buscar por título, artista o década
4. Ve cola de canciones solicitadas
5. Controla reproducción (Play/Pause/Skip)
6. Activa/desactiva visualización de letras

### Rol 2: Cliente del Pub (Cantante)
1. Escanea QR code en mesa o accede a URL
2. Ve catálogo de canciones disponibles
3. Solicita canción (agrega a cola)
4. Ingresa su nombre para anuncio
5. Espera su turno (ve posición en cola)
6. Recibe notificación cuando es su turno

---

## 🎤 Características del Modo Karaoke

### Display de Letras
- **Font grande** y legible (min 36px)
- **Highlight de línea actual** (color amarillo/dorado)
- **Preview de siguiente línea** (gris translúcido)
- **Scroll automático** suave
- **Fade in/out** entre líneas
- **Kanji + Romaji** para idiomas asiáticos (opcional)

### Control de Audio
- **Ajuste de pitch** (+/- 3 semitonos)
- **Control de tempo** (80% - 120%)
- **Volumen instrumental vs vocal** (si disponible)
- **Reverb opcional** para micrófono externo

### Sistema de Puntuación (Opcional)
- **Detección de pitch** con Web Audio API
- **Comparación con pitch original**
- **Score de 0-100** basado en precisión
- **Rating de estrellas** (1-5)
- **Hall of Fame** de mejores performances

---

## 🔧 Tareas de Implementación Backend

### Tarea 5.1: Integración con API de Letras

#### Opción A: Musixmatch API
- **Ventajas**: Base de datos más grande, letras sincronizadas (LRC)
- **Desventajas**: Costo ($499/mes plan comercial)
- **Endpoints**:
  - `matcher.lyrics.get` - Obtener letra por canción/artista
  - `track.subtitle.get` - Obtener subtítulos sincronizados (LRC)
- **Rate limits**: 2000 llamadas/día (plan free)

#### Opción B: Genius API
- **Ventajas**: Gratis para uso no comercial
- **Desventajas**: No tiene letras sincronizadas (solo texto plano)
- **Endpoints**:
  - `search` - Buscar canción
  - `songs/:id` - Obtener letra (requiere scraping adicional)

#### Opción C: LyricsOVH (Free, Comunidad)
- **Ventajas**: Completamente gratis, sin autenticación
- **Desventajas**: Sin sincronización, menos canciones
- **Endpoint**: `https://api.lyrics.ovh/v1/{artist}/{title}`

**Recomendación**: Usar Musixmatch para versión premium, LyricsOVH para demo/MVP.

### Tarea 5.2: Sistema de Caché de Letras
- Crear tabla `lyrics_cache` en Django
- Campos:
  - `song_id` (foreign key a pool.json)
  - `plain_lyrics` (text)
  - `synced_lyrics_lrc` (text, formato LRC)
  - `language` (string)
  - `last_fetched` (timestamp)
- Evitar re-fetching de APIs externas
- TTL de 90 días para refresh

### Tarea 5.3: Parser de Formato LRC
- Crear función `parse_lrc(lrc_string)` en Python
- Formato LRC: `[mm:ss.xx]Letra de la línea`
- Devolver array de objetos:
  ```
  [
    {timestamp: 0.5, text: "Intro instrumental"},
    {timestamp: 5.2, text: "Primera línea..."},
    {timestamp: 9.8, text: "Segunda línea..."}
  ]
  ```
- Manejar múltiples formatos (algunos usan centésimas, otros milésimas)

### Tarea 5.4: Endpoint `/api/karaoke/get-lyrics`
- Parámetros:
  - `song_id` (requerido)
  - `format` (plain/lrc, default: lrc)
- Lógica:
  1. Buscar en caché local
  2. Si no existe, llamar a API externa
  3. Guardar en caché
  4. Parsear LRC si necesario
  5. Devolver JSON estructurado

### Tarea 5.5: Sistema de Cola de Canciones
- Crear modelo `KaraokeQueue`
- Campos:
  - `venue_id`
  - `song_id`
  - `requester_name`
  - `position` (order)
  - `status` (waiting/playing/completed/skipped)
  - `requested_at`
- Endpoints:
  - POST `/api/karaoke/request-song` - Agregar a cola
  - GET `/api/karaoke/queue?venue_id=X` - Ver cola
  - POST `/api/karaoke/next` - Marcar como completada, avanzar
  - DELETE `/api/karaoke/queue/:id` - Cancelar solicitud

### Tarea 5.6: Sistema de Notificaciones
- Cuando falta 1 canción para tu turno: enviar notificación
- Opciones de notificación:
  - WebSocket (tiempo real)
  - Polling cada 30 segundos
  - SMS (Twilio, costo adicional)
- Anuncio TTS: "Next up: [Nombre] will sing [Canción]"

---

## 🎨 Tareas de Implementación Frontend

### Tarea 6.1: Pantalla Principal de Karaoke
- **Header**: Logo del venue + "Karaoke Mode"
- **Sección izquierda** (30%): Cola de canciones
- **Sección central** (70%): Display de letras
- **Footer**: Controles de reproducción

### Tarea 6.2: Catálogo de Canciones
- Listar canciones con indicador de "Lyrics Available"
- Filtros:
  - Por década
  - Por género
  - Por idioma
  - Solo canciones con letras sincronizadas
- Buscador con autocompletado
- Botón "Request" para agregar a cola

### Tarea 6.3: Display de Letras Sincronizadas
- Canvas o DIV con CSS para letras
- Lógica en `karaoke.js`:
  - Cargar array de timestamps desde backend
  - Sincronizar con `Howler.currentTime()`
  - Actualizar highlight cada 100ms
  - Scroll automático para mantener línea actual centrada
- Transiciones suaves entre líneas
- Opción de fullscreen

### Tarea 6.4: Cola Visual (Queue Display)
- Lista ordenada de canciones
- Cada item muestra:
  - Posición (#1, #2, etc)
  - Título y artista
  - Nombre del solicitante
  - Botón de cancelar (si es tuya)
- Highlight de canción actual (verde)
- Auto-scroll cuando avanza

### Tarea 6.5: Controles del Operador
- Botones grandes:
  - ▶️ Play / ⏸️ Pause
  - ⏭️ Skip
  - 🔄 Restart
- Sliders:
  - Volume
  - Pitch (+/- 3 semitonos)
  - Tempo (80-120%)
- Toggle:
  - Show Lyrics (On/Off)
  - Auto-Advance Queue

### Tarea 6.6: Interfaz de Solicitud (Cliente)
- Versión mobile-first
- Pantalla de búsqueda simplificada
- Formulario de solicitud:
  - "Your name" (input text)
  - Confirmación
- Ticket virtual con número de cola
- Actualización en tiempo real de posición

### Tarea 6.7: Sistema de Puntuación (Fase 2, Opcional)
- Integrar Web Audio API para análisis de pitch
- Detectar pitch del micrófono
- Comparar con pitch de la canción original
- Mostrar score en tiempo real (medidor visual)
- Pantalla de resultado final con rating

---

## 🧪 Testing y Validación

### Tests Backend
- Test de integración con Musixmatch/Genius API
- Test de parser LRC con diferentes formatos
- Test de sistema de caché
- Test de cola de canciones (CRUD completo)
- Test de manejo de errores (lyrics no disponibles)

### Tests Frontend
- Test de sincronización de letras con audio
- Test de scroll automático
- Test de actualización de cola en tiempo real
- Test de controles de pitch/tempo
- Test de fullscreen en diferentes browsers

### Tests de Usuario
- Operador agrega canciones a cola
- Cliente solicita canción desde mobile
- Verificar sincronización precisa de letras
- Validar que notificaciones funcionan
- Testear skip y restart

---

## 📈 Métricas de Éxito

### KPIs Técnicos
- Precisión de sincronización: < 200ms de diferencia
- Canciones con letras disponibles: > 80% del pool
- Latencia de búsqueda: < 1 segundo
- Uptime del sistema: > 99%

### KPIs de Negocio
- Solicitudes de karaoke por noche
- Duración promedio de sesión
- Satisfacción del cliente (encuesta post-karaoke)
- Adoption rate (% venues que activan modo karaoke)

---

## 💰 Consideraciones de Costo

### APIs de Letras
- **Musixmatch**: $499/mes (comercial)
- **Genius**: Gratis (limitado)
- **LyricsOVH**: Gratis (comunidad)

### Recomendación de Monetización
- Cobrar £5/mes adicionales por modo karaoke
- Plan híbrido: Letras básicas gratis, sincronizadas premium

---

## 🚧 Riesgos y Mitigaciones

### Riesgo 1: Letras No Disponibles
- **Problema**: Solo 60% de canciones tienen lyrics
- **Mitigación**: Filtrar catálogo, permitir upload manual

### Riesgo 2: Sincronización Imprecisa
- **Problema**: LRC no coincide con preview de iTunes
- **Mitigación**: Offset manual, calibración por canción

### Riesgo 3: Copyright de Letras
- **Problema**: Mostrar letras puede violar copyright
- **Mitigación**: Usar APIs licenciadas, disclaimer legal

---

## 📅 Timeline Estimado

### Semana 1: Backend + API Integration
- Días 1-2: Integración Musixmatch/Genius
- Días 3-4: Parser LRC + caché
- Día 5: Sistema de cola

### Semana 2: Frontend Core
- Días 1-2: Display de letras + sincronización
- Días 3-4: Cola y controles
- Día 5: Integración end-to-end

### Semana 3: Features Avanzados
- Días 1-2: Interfaz de cliente (mobile)
- Días 3-4: Notificaciones y anuncios
- Día 5: Tests y refinamiento

### Semana 4: Testing + Deploy
- Días 1-3: UAT con venue real
- Días 4-5: Bug fixes y optimizaciones

### Total: **3-4 semanas**

---

# 4️⃣ SINGLES BLIND DATE - Sistema de Matching Musical

## 🎯 Objetivo del Proyecto

Crear una experiencia de "Tinder musical" donde solteros se conectan basándose en sus gustos musicales, con interacción en vivo en el pub.

**Alcance**: Funcionalidad social que se desvía del core de Music Bingo. Requiere validación de product-market fit antes de desarrollo completo.

---

## 🏗️ Arquitectura Conceptual

### Componentes Principales
- **Sistema de Usuarios**: Registro, perfiles, fotos
- **Motor de Matching**: Algoritmo basado en gustos musicales
- **Chat**: Mensajería entre matches
- **Eventos en Vivo**: "Speed Dating Musical" en el pub
- **Gamificación**: Insignias, rankings de compatibilidad

---

## 📊 Flujo de Usuario Detallado

### Fase 1: Onboarding
1. Usuario descarga app o accede a web
2. Registro con email/teléfono
3. Upload de 3-5 fotos
4. Edad, género, preferencias de búsqueda
5. Bio breve (opcional)

### Fase 2: Test Musical
1. Usuario escucha 30 fragmentos de canciones (5 seg cada uno)
2. Califica cada canción: ❤️ Love / 👍 Like / 👎 Dislike
3. Sistema detecta géneros/décadas favoritas
4. Algoritmo crea "perfil musical"

### Fase 3: Swiping
1. Ver perfiles de otros usuarios
2. Información mostrada:
   - Fotos
   - Edad, nombre, bio
   - Top 5 géneros musicales
   - Canción favorita (se reproduce al swipe right)
3. Swipe left (no) / right (sí)
4. Si hay match mutuo: "It's a Match!"

### Fase 4: Chat
1. Conversación desbloqueada tras match
2. Rompehielos automático: "What do you think about [canción]?"
3. Opción de "enviar canción" en chat
4. Sugerencia de playlist compartida

### Fase 5: Evento en Vivo (Diferenciador Clave)
1. Venue organiza "Singles Night" mensual
2. Matches se encuentran en persona
3. Juegos musicales para romper hielo:
   - "Name That Tune" en parejas
   - "Duet Karaoke Challenge"
   - "Back-to-Back Questions" sobre música
4. Premios para mejor pareja musical

---

## 🔧 Tareas de Implementación Backend

### Tarea 7.1: Sistema de Usuarios y Autenticación
- Crear modelos Django:
  - `User` (extender AbstractUser)
  - `Profile` (datos personales)
  - `MusicProfile` (gustos musicales)
- Implementar JWT authentication
- Endpoints:
  - POST `/api/auth/register`
  - POST `/api/auth/login`
  - GET `/api/users/me`
  - PUT `/api/users/me/profile`

### Tarea 7.2: Sistema de Test Musical
- Crear endpoint `/api/music-test/start`
- Seleccionar 30 canciones diversas (diferentes géneros/décadas)
- Endpoint `/api/music-test/rate`:
  - Parámetros: `song_id`, `rating` (love/like/dislike)
  - Guardar en tabla `UserSongRating`
- Algoritmo de análisis:
  - Calcular preferencias de género (%)
  - Detectar décadas favoritas
  - Identificar nichos (ej: "synthpop 80s", "grunge 90s")
  - Guardar en `MusicProfile`

### Tarea 7.3: Algoritmo de Matching
- Crear función `calculate_compatibility(user_a, user_b)`
- Factores de scoring:
  1. **Género overlap** (40%): Intersección de géneros favoritos
  2. **Década overlap** (20%): Décadas en común
  3. **Song matches** (30%): Canciones que ambos marcaron "love"
  4. **Niche bonus** (10%): Si comparten géneros raros
- Score de 0-100 (compatibilidad musical)
- Filtros adicionales:
  - Edad (rango configurable)
  - Distancia geográfica
  - Género de interés

### Tarea 7.4: Sistema de Swiping
- Endpoint `/api/matches/candidates`:
  - Devolver 10 perfiles candidatos
  - Ordenados por compatibilidad
  - Excluir ya vistos/rechazados
- Endpoint `/api/matches/swipe`:
  - Parámetros: `target_user_id`, `action` (like/pass)
  - Si ambos dieron like: crear `Match` y notificar
- Tabla `Swipe`:
  - `from_user`, `to_user`, `action`, `timestamp`

### Tarea 7.5: Sistema de Chat
- Opciones de implementación:
  - **Django Channels** + WebSocket (complejo)
  - **Firebase Realtime Database** (más simple)
  - **Stream Chat API** (solución SaaS)
- Tabla `Message`:
  - `match_id`, `sender_id`, `content`, `timestamp`
- Funcionalidad especial: "Send Song"
  - Adjuntar `song_id` a mensaje
  - Reproducir preview inline en chat

### Tarea 7.6: Sistema de Eventos en Vivo
- Crear modelo `SinglesEvent`:
  - `venue_id`, `date`, `max_attendees`, `ticket_price`
- Endpoint `/api/events/upcoming`
- Registro: POST `/api/events/:id/register`
- Check-in en venue con QR code
- Generación de "games" para parejas asistentes

---

## 🎨 Tareas de Implementación Frontend

### Tarea 8.1: Onboarding Flow
- Pantallas secuenciales:
  1. Welcome + Explicación
  2. Registro (email/password)
  3. Upload de fotos (drag & drop)
  4. Información personal
  5. Inicio del test musical
- Progreso visual (stepper)

### Tarea 8.2: Test Musical Interactivo
- UI tipo "Tinder for Music"
- Card central con:
  - Artwork de la canción
  - Play button (auto-play 5 seg)
  - 3 botones: ❤️ Love / 👍 Like / 👎 Dislike
- Contador: "Song 15 of 30"
- Animaciones al swipe

### Tarea 8.3: Pantalla de Perfil Musical
- Resumen visual de resultados:
  - Gráfico de radar con géneros
  - Top 5 artistas
  - Top 5 canciones
  - Insignias (ej: "80s Expert", "Rock Lover")
- Opción de retomar test (actualizar perfil)

### Tarea 8.4: Interfaz de Swiping
- Diseño tipo Tinder:
  - Stack de cards
  - Swipe gesture (touch/mouse)
  - Botones alternativos: ✕ (pass) / ❤️ (like)
- Info en card:
  - Foto principal (tap para ver más)
  - Nombre, edad
  - Compatibility score (ej: "89% Musical Match")
  - Top 3 géneros en común
- Audio preview al swipe right

### Tarea 8.5: Pantalla de Matches
- Lista de matches con últimos mensajes
- Badge de mensajes no leídos
- Filtros: Todos / Nuevos / Archivados
- Tap para abrir chat

### Tarea 8.6: Interfaz de Chat
- Diseño tipo WhatsApp/Messenger
- Burbujas de mensajes (enviados/recibidos)
- Botón "🎵 Send Song"
- Preview de canciones compartidas (mini player)
- Sugerencia de "Meet at [Venue Name] for Singles Night"

### Tarea 8.7: Página de Eventos
- Calendario de Singles Nights
- Cada evento muestra:
  - Fecha, hora, venue
  - Número de inscritos
  - Precio de entrada
- Botón "Register"
- Confirmación con QR code para check-in

---

## 🧪 Testing y Validación

### Tests Backend
- Test de algoritmo de matching con datos sintéticos
- Test de creación de matches mutuos
- Test de chat (envío/recepción de mensajes)
- Test de registro a eventos
- Test de permisos y privacidad

### Tests Frontend
- Test de swipe gesture
- Test de reproducción de audio en cards
- Test de notificaciones de match
- Test de chat en tiempo real
- Test mobile y desktop

### Tests de Usuario (UAT)
- 20-30 usuarios beta para test musical
- Validar que algoritmo genera matches relevantes
- Testear evento en vivo en 1 venue piloto
- Recoger feedback sobre usabilidad

---

## 📈 Métricas de Éxito (MVP)

### KPIs de Producto
- Usuarios registrados por venue
- Tasa de completación del test musical
- Matches generados por usuario
- Mensajes enviados por match
- Conversión a evento en vivo (%)

### KPIs de Negocio
- Ticket sales para Singles Nights
- Engagement (DAU/MAU)
- Retención a 30 días
- Net Promoter Score (NPS)

---

## 💰 Modelo de Monetización

### Opción 1: Freemium
- **Gratis**:
  - Test musical
  - Swipes ilimitados
  - Matches ilimitados
  - Chat básico
- **Premium** (£9.99/mes):
  - Ver quién te dio like
  - Rewind swipes
  - Boost (aparecer primero)
  - Filtros avanzados

### Opción 2: Pay-per-Event
- App gratis
- Cobrar solo por entradas a Singles Nights (£10-15)
- Revenue share con venues (70/30)

### Opción 3: Venue Subscription
- Venue paga £50/mes
- Organizan 1 evento mensual
- Promoción en la app
- Herramientas de gestión de evento

---

## 🚧 Riesgos y Mitigaciones

### Riesgo 1: Baja Adopción (Cold Start Problem)
- **Problema**: Pocas personas = pocos matches = abandono
- **Mitigación**:
  - Lanzamiento por venue (1 pub a la vez)
  - Evento de launch con incentivos
  - Marketing agresivo local

### Riesgo 2: Competencia con Tinder/Bumble
- **Problema**: Apps establecidas con millones de usuarios
- **Mitigación**:
  - Nicho específico (música + eventos en vivo)
  - Comunidad local (pub-centric)
  - Experiencia física (eventos)

### Riesgo 3: Moderación de Contenido
- **Problema**: Fotos/mensajes inapropiados
- **Mitigación**:
  - Moderación manual inicial
  - Reportes de usuarios
  - IA para detectar contenido NSFW (AWS Rekognition)

### Riesgo 4: Seguridad y Privacidad
- **Problema**: Datos personales sensibles
- **Mitigación**:
  - Encriptación end-to-end en chat
  - No mostrar apellidos completos
  - Verificación de identidad para eventos

---

## 📅 Timeline Estimado (MVP)

### Mes 1: Backend Core
- Semanas 1-2: Sistema de usuarios + autenticación
- Semanas 3-4: Test musical + algoritmo de matching

### Mes 2: Frontend MVP
- Semanas 1-2: Onboarding + test musical
- Semanas 3-4: Swiping + pantalla de matches

### Mes 3: Chat + Eventos
- Semanas 1-2: Implementación de chat
- Semanas 3-4: Sistema de eventos

### Mes 4: Testing + Launch
- Semanas 1-2: UAT con usuarios beta
- Semanas 3-4: Bug fixes + primer evento piloto

### Total: **4 meses** (más complejo, requiere equipo)

---

## 🎯 Recomendación Final

**NO DESARROLLAR hasta validar demanda**:
1. Encuesta a clientes de venues: ¿Usarían esta app?
2. Organizar 1 evento "manual" (sin app) para testear interés
3. Si hay >50 registros en primer evento → considerar MVP
4. Si no, enfocar recursos en Jingles/Quiz/Karaoke

---

# 📊 RESUMEN COMPARATIVO DE LAS 4 FUNCIONALIDADES

| Funcionalidad | Prioridad | Esfuerzo | ROI | Sinergia | Decisión |
|---------------|-----------|----------|-----|----------|----------|
| **🎤 Jingle Creation** | 🔴 Alta | 2-3 semanas | Alto | ⭐⭐⭐⭐⭐ | ✅ DESARROLLAR YA |
| **📝 Pub Quiz** | 🟡 Media | 1-2 semanas | Medio | ⭐⭐⭐⭐ | ✅ DESARROLLAR DESPUÉS |
| **🎤 Karaoke** | 🟡 Media | 3-4 semanas | Alto | ⭐⭐⭐ | ⏸️ CONSIDERAR (costo APIs) |
| **💑 Singles Blind Date** | 🟢 Baja | 4 meses | Incierto | ⭐ | ❌ POSPONER (validar primero) |

---

# 🛣️ ROADMAP RECOMENDADO

## Q1 2026 (Enero - Marzo)
- ✅ **Jingle Creation** (Semanas 1-3)
- ✅ **Pub Quiz** (Semanas 4-5)
- ✅ Deploy y marketing de nuevas features

## Q2 2026 (Abril - Junio)
- 🔍 Validar demanda de Karaoke (encuestas)
- 🔍 Validar demanda de Singles (evento piloto)
- 💰 Monetizar Jingles y Quiz
- 📈 Análisis de métricas

## Q3 2026 (Julio - Septiembre)
- ⚖️ Decisión: Karaoke vs Singles basado en Q2
- 🚀 Desarrollo de feature elegida
- 🌍 Expansión a más venues

## Q4 2026 (Octubre - Diciembre)
- 🎉 Completar 4 funcionalidades
- 📊 Análisis anual
- 🗺️ Planear 2027

---

# 🎓 LECCIONES APRENDIDAS Y MEJORES PRÁCTICAS

## Principios de Desarrollo
1. **Reutilizar antes de reinventar**: Aprovechar infraestructura existente
2. **MVP primero, features después**: Validar antes de invertir meses
3. **Datos existentes son oro**: announcements_ai.json abre camino a Quiz
4. **Monetización clara**: Cada feature debe tener modelo de ingresos

## Criterios de Priorización
- **Sinergia** > Novedad
- **Tiempo de desarrollo** < 1 mes = priorizar
- **Impacto en negocio** > Coolness factor
- **Validación de mercado** antes de commitment

---

**Fin del Documento**

_Última actualización: 13 de enero de 2026_
