# 🔧 Plan de Refactorización — `pub_quiz_views.py` (1925 líneas → ~6 archivos)

**Fecha:** 12 Febrero 2026  
**Estado actual:** 1 archivo monolítico de 1925 líneas  
**Objetivo:** Distribuir en las carpetas existentes (`views/`, `services/`, `utils/`) siguiendo el patrón ya establecido en el proyecto (como `session_views.py` + `session_service.py`)

---

## 📊 Análisis del Archivo Actual

| Sección | Líneas | Responsabilidad |
|---------|--------|-----------------|
| Imports + Helpers | 1-72 | `get_session_by_code_or_id()`, imports duplicados |
| Admin (CRUD sesiones) | 73-170 | `get_sessions`, `create_quiz_session` |
| Registro + QR | 171-365 | `get_session_details`, `check_existing_team`, `register_team`, `generate_qr_code` |
| Generación preguntas | 366-565 | `generate_quiz_questions` (200 líneas) |
| Control quiz en vivo | 566-870 | `quiz_host_data`, `start_quiz`, `get_all_questions`, `get_team_stats`, `sync_question_to_players`, `start_countdown`, `reset_quiz`, `delete_session`, `bulk_delete_sessions` |
| Next question | 936-1060 | `next_question` (130 líneas con prints duplicados) |
| Auto-advance | 1060-1125 | `toggle_auto_advance`, `pause_auto_advance`, `set_auto_advance_time` |
| SSE Player stream | 1126-1310 | `quiz_stream` (185 líneas) |
| SSE Host stream | 1311-1515 | `host_stream` (205 líneas) |
| Respuestas/Buzz | 1516-1670 | `get_question_answer`, `submit_answer`, `record_buzz`, `submit_all_answers` |
| Puntuación | 1675-1700 | `award_points`, `initialize_quiz_genres` |
| TTS | 1710-1820 | `generate_quiz_tts` |
| Answer Sheets PDF | 1820-1925 | `generate_answer_sheets` |

### Problemas detectados:
- ❌ Import duplicado de `logger` (líneas 29 y 72)
- ❌ Import de `pub_quiz_generator` en medio del archivo (línea 71)
- ❌ `print()` duplicados en `next_question` (líneas 948-958 son copia de 942-947)
- ❌ Import de `transaction` y `timezone` duplicado a mitad del archivo (línea 1528)
- ❌ Import de `logging` redundante dentro de funciones
- ❌ Logs excesivos de debug que deberían ser `logger.debug` no `logger.info`

---

## 🗂️ Estructura Propuesta

```
backend/api/
├── views/
│   ├── __init__.py                    # ← Actualizar con nuevos imports
│   ├── pub_quiz_session_views.py      # CRUD sesiones (crear, listar, borrar, reset)
│   ├── pub_quiz_registration_views.py # Registro equipos, QR, géneros
│   ├── pub_quiz_game_views.py         # Control en vivo (start, next, auto-advance, sync)
│   ├── pub_quiz_answer_views.py       # Respuestas, buzz, puntuación
│   ├── pub_quiz_stream_views.py       # SSE streams (player + host)
│   └── pub_quiz_tts_views.py          # TTS + Answer Sheets PDF
│
├── services/
│   ├── __init__.py                    # ← Actualizar con nuevos imports
│   └── pub_quiz_service.py            # Lógica de negocio extraída
│
├── utils/
│   └── pub_quiz_helpers.py            # get_session_by_code_or_id + helpers comunes
│
├── pub_quiz_models.py                 # ✅ Se queda (ya está bien)
├── pub_quiz_generator.py              # ✅ Se queda (ya está bien)
└── pub_quiz_views.py                  # ❌ Se elimina al final
```

---

## 📋 Pasos de Ejecución (Orden)

### Fase 1: Crear base (utils + service)

#### Paso 1.1 — `utils/pub_quiz_helpers.py`
Extraer helpers reutilizables:
```python
# Contenido:
- get_session_by_code_or_id(session_identifier)  # Helper principal
- serialize_question(question)                     # Serializar pregunta a dict
- serialize_team(team)                             # Serializar equipo a dict
- get_timing_config(session)                       # Config de timing reutilizable
```
**Líneas originales:** 38-70, más fragmentos repetidos por todo el archivo  
**Impacto:** Elimina ~80 líneas duplicadas de serialización

#### Paso 1.2 — `services/pub_quiz_service.py`
Extraer lógica de negocio pesada:
```python
class PubQuizService:
    # Session management
    @staticmethod
    def create_session(data) -> PubQuizSession
    
    @staticmethod
    def reset_session(session) -> None
    
    @staticmethod
    def delete_session(session) -> None
    
    # Question generation
    @staticmethod
    def generate_questions(session, question_types, difficulty_mix) -> dict
    
    # Game flow
    @staticmethod
    def advance_to_next_question(session) -> dict
    
    @staticmethod
    def start_quiz(session) -> dict
    
    # Answers & scoring
    @staticmethod
    def submit_answer(question, team, answer_text, is_multiple_choice) -> dict
    
    @staticmethod
    def submit_batch_answers(session, team, answers) -> dict
    
    @staticmethod
    def check_answer_correctness(question, answer_text, is_multiple_choice) -> bool
    
    # Stats
    @staticmethod
    def get_host_update_data(session) -> dict
    
    @staticmethod
    def get_team_stats(session, team) -> dict
```
**Líneas originales:** Lógica extraída de múltiples funciones  
**Impacto:** Las views pasan de ~50-200 líneas a ~10-20 líneas cada una

---

### Fase 2: Crear las views modulares

#### Paso 2.1 — `views/pub_quiz_session_views.py` (~100 líneas)
```python
# Funciones:
- get_sessions(request)                           # GET lista de sesiones
- create_quiz_session(request)                     # POST crear sesión
- delete_session(request, session_id)              # DELETE borrar sesión
- bulk_delete_sessions(request)                    # DELETE masivo
- reset_quiz(request, session_id)                  # POST reset quiz
```
**Líneas originales:** 73-170, 840-935

#### Paso 2.2 — `views/pub_quiz_registration_views.py` (~100 líneas)
```python
# Funciones:
- get_session_details(request, session_id)         # GET detalles sesión
- check_existing_team(request, session_id)         # GET verificar equipo
- register_team(request, session_id)               # POST registrar equipo
- generate_qr_code(request, session_id)            # GET código QR
- initialize_quiz_genres(request)                  # POST init géneros
```
**Líneas originales:** 171-365

#### Paso 2.3 — `views/pub_quiz_game_views.py` (~200 líneas)
```python
# Funciones:
- quiz_host_data(request, session_id)              # GET datos host
- start_quiz(request, session_id)                  # POST iniciar quiz
- get_all_questions(request, session_id)           # GET todas las preguntas
- sync_question_to_players(request, session_id)    # POST sync pregunta
- start_countdown(request, session_id)             # POST iniciar countdown
- next_question(request, session_id)               # POST siguiente pregunta
- toggle_auto_advance(request, session_id)         # POST toggle auto-advance
- pause_auto_advance(request, session_id)          # POST pausar auto-advance
- set_auto_advance_time(request, session_id)       # POST set tiempo
- generate_quiz_questions(request, session_id)     # POST generar preguntas
```
**Líneas originales:** 366-570, 780-840, 936-1125

#### Paso 2.4 — `views/pub_quiz_answer_views.py` (~80 líneas)
```python
# Funciones:
- get_question_answer(request, question_id)        # GET respuesta
- submit_answer(request, question_id)              # POST responder
- record_buzz(request, question_id)                # POST buzz
- submit_all_answers(request, session_id)          # POST batch respuestas
- award_points(request, team_id)                   # POST dar puntos
- get_team_stats(request, session_id, team_id)     # GET stats equipo
```
**Líneas originales:** 1516-1700

#### Paso 2.5 — `views/pub_quiz_stream_views.py` (~250 líneas)
```python
# Funciones:
- quiz_stream(request, session_id)                 # SSE para jugadores
- host_stream(request, session_id)                 # SSE para host
```
**Líneas originales:** 1126-1515  
**Nota:** Los SSE streams son complejos y deben quedar juntos porque comparten lógica similar

#### Paso 2.6 — `views/pub_quiz_tts_views.py` (~120 líneas)
```python
# Funciones:
- generate_quiz_tts(request)                       # POST generar TTS
- generate_answer_sheets(request)                  # POST generar PDF
```
**Líneas originales:** 1710-1925

---

### Fase 3: Actualizar imports y routing

#### Paso 3.1 — Actualizar `views/__init__.py`
Agregar bloque de imports del pub quiz (siguiendo patrón existente)

#### Paso 3.2 — Actualizar `services/__init__.py`
Agregar `PubQuizService`

#### Paso 3.3 — Actualizar `urls.py`
Cambiar de `pub_quiz_views.function_name` a `views.function_name` (consistente con el resto)

#### Paso 3.4 — Eliminar `pub_quiz_views.py`
Solo después de verificar que todo funciona

---

### Fase 4: Limpieza (durante la refactorización)

| Limpieza | Detalle |
|----------|---------|
| 🧹 Eliminar `print()` duplicados | ~30 prints en `next_question` → usar `logger.debug` |
| 🧹 Eliminar imports duplicados | `logger`, `timezone`, `transaction` definidos 2-3 veces |
| 🧹 Reducir logging excesivo | `logger.info` → `logger.debug` para mensajes de sync/SSE |
| 🧹 Eliminar imports dentro de funciones | `import logging` dentro de `create_quiz_session`, etc. |
| 🧹 Unificar serialización | Usar helpers de `pub_quiz_helpers.py` en vez de dicts inline |

---

## 📊 Resultado Esperado

| Archivo | Líneas Est. | Responsabilidad |
|---------|-------------|-----------------|
| `utils/pub_quiz_helpers.py` | ~60 | Helpers + serialización |
| `services/pub_quiz_service.py` | ~250 | Lógica de negocio |
| `views/pub_quiz_session_views.py` | ~80 | CRUD sesiones |
| `views/pub_quiz_registration_views.py` | ~90 | Registro + QR |
| `views/pub_quiz_game_views.py` | ~150 | Control del juego |
| `views/pub_quiz_answer_views.py` | ~70 | Respuestas + puntos |
| `views/pub_quiz_stream_views.py` | ~200 | SSE streams |
| `views/pub_quiz_tts_views.py` | ~100 | TTS + PDF |
| **Total** | **~1000** | **~48% reducción** |

La reducción viene de:
- Eliminar ~200 líneas de prints/logs duplicados
- Eliminar ~100 líneas de imports/código duplicado
- Extraer ~300 líneas de lógica repetida a helpers/service
- Código más limpio y conciso en general

---

## ⚠️ Riesgos y Precauciones

1. **SSE streams** — Son stateful (tienen generators). No mover lógica interna fuera del generator.
2. **`_player_question_positions`** — Es un dict global. Asegurarse de que se importe correctamente en `pub_quiz_stream_views.py`.
3. **`urls.py`** — Tiene 28 rutas de pub quiz. Hay que cambiarlas todas de una vez.
4. **Tests** — Verificar que `test_sse_integration.py` sigue funcionando.
5. **Imports circulares** — `services/` importa `models`, `views/` importa `services/` y `utils/`. No crear ciclos.

---

## 🚦 Orden de Ejecución Recomendado

```
1. [utils/pub_quiz_helpers.py]     ← Crear primero (sin dependencias)
2. [services/pub_quiz_service.py]  ← Depende solo de models + helpers
3. [views/pub_quiz_answer_views.py]     ← Más simple, pocas dependencias
4. [views/pub_quiz_registration_views.py] ← Independiente
5. [views/pub_quiz_session_views.py]    ← Independiente
6. [views/pub_quiz_tts_views.py]        ← Independiente
7. [views/pub_quiz_game_views.py]       ← Depende de service
8. [views/pub_quiz_stream_views.py]     ← Más complejo, hacer al final
9. [urls.py + __init__.py]              ← Rewiring
10. [Eliminar pub_quiz_views.py]        ← Solo tras verificar
```

Cada paso se puede hacer como un commit independiente que no rompe nada, porque `pub_quiz_views.py` sigue existiendo hasta el paso 10.

---

## ✅ Checklist de Verificación (post-refactor)

- [ ] `python manage.py check` sin errores
- [ ] Todas las 28 URLs de pub quiz responden
- [ ] SSE player stream conecta y recibe preguntas
- [ ] SSE host stream conecta y recibe updates
- [ ] Crear sesión funciona
- [ ] Registrar equipo funciona
- [ ] Generar preguntas funciona
- [ ] TTS funciona
- [ ] `test_sse_integration.py` pasa
- [ ] No hay imports circulares
- [ ] `pub_quiz_views.py` eliminado
