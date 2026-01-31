# Plan de Refactorización: views.py

**Fecha:** 31 de enero de 2026  
**Archivo:** `/backend/api/views.py` (1841 líneas)  
**Objetivo:** Dividir el archivo monolítico en módulos especializados para mejorar mantenibilidad, testabilidad y escalabilidad.

---

## 📊 Análisis del Estado Actual

### Problemas Identificados:
1. **Archivo monolítico:** 1841 líneas en un solo archivo
2. **Múltiples responsabilidades:** Mezcla lógica de negocio, validación, tareas async
3. **Duplicación de código:** Validaciones y manejo de errores repetidos
4. **Acoplamiento:** Dependencias directas con servicios externos (ElevenLabs, GCS)
5. **Difícil testeo:** Lógica de negocio mezclada con views
6. **Falta de separación de concerns:** Backend tasks dentro de views

### Estructura Actual:
```
views.py (1841 líneas)
├── Configuration & Utilities (74 líneas)
├── Core Bingo Views (432 líneas)
├── Jingle Generation (500+ líneas)
├── Jingle Schedule Management (550+ líneas)
├── Venue Configuration (100 líneas)
└── Bingo Session Management (185 líneas)
```

---

## 🎯 Estrategia de Refactorización

### Fase 1: Análisis y Preparación
- [x] Identificar todas las vistas y sus responsabilidades
- [ ] Crear tests para funcionalidades críticas (cobertura actual)
- [ ] Documentar dependencias entre módulos

### Fase 2: Extracción de Servicios
- [ ] Crear capa de servicios (service layer)
- [ ] Extraer lógica de negocio de las views
- [ ] Implementar patrones Repository para acceso a datos

### Fase 3: Modularización
- [ ] Dividir views.py en módulos especializados
- [ ] Crear estructura de paquetes
- [ ] Actualizar imports y URLs

### Fase 4: Mejoras Arquitectónicas
- [ ] Implementar validadores reutilizables
- [ ] Crear serializers específicos
- [ ] Implementar manejo centralizado de errores

### Fase 5: Testing y Documentación
- [ ] Escribir tests unitarios para servicios
- [ ] Tests de integración para APIs
- [ ] Actualizar documentación

---

## 📁 Nueva Estructura Propuesta

```
backend/api/
├── __init__.py
├── models.py                    # Existente
├── serializers/                 # NUEVO
│   ├── __init__.py
│   ├── bingo_serializers.py     # Serializers para bingo sessions
│   ├── jingle_serializers.py    # Serializers para jingles
│   ├── venue_serializers.py     # Serializers para venues
│   └── task_serializers.py      # Serializers para tasks
├── services/                    # NUEVO - Lógica de negocio
│   ├── __init__.py
│   ├── card_generation_service.py   # Generación de tarjetas
│   ├── jingle_service.py            # Generación de jingles
│   ├── tts_service.py               # Text-to-Speech con ElevenLabs
│   ├── music_service.py             # Generación de música
│   ├── storage_service.py           # Integración con GCS
│   ├── schedule_service.py          # Lógica de schedules
│   └── session_service.py           # Gestión de sesiones
├── validators/                  # NUEVO - Validaciones
│   ├── __init__.py
│   ├── jingle_validators.py
│   ├── schedule_validators.py
│   └── session_validators.py
├── tasks/                       # NUEVO - Tareas asíncronas
│   ├── __init__.py
│   ├── card_generation_tasks.py
│   └── jingle_generation_tasks.py
├── views/                       # Dividido por dominio
│   ├── __init__.py
│   ├── core_views.py            # health_check, get_pool, get_config
│   ├── card_views.py            # Card generation endpoints
│   ├── jingle_views.py          # Jingle generation & management
│   ├── schedule_views.py        # Jingle schedule CRUD
│   ├── venue_views.py           # Venue configuration
│   ├── session_views.py         # Bingo session management
│   └── tts_views.py             # TTS & announcements
├── utils/                       # NUEVO - Utilidades
│   ├── __init__.py
│   ├── config.py                # Configuración centralizada
│   ├── paths.py                 # Gestión de paths
│   └── response_helpers.py      # Response formatters
└── urls.py                      # Actualizar imports
```

---

## 🔧 Desglose Detallado por Módulo

### 1. **services/storage_service.py** (40-60 líneas)
**Responsabilidad:** Manejo de Google Cloud Storage

**Funciones a mover:**
- `upload_to_gcs()` (actual línea 37)
- Agregar: `delete_from_gcs()`, `get_public_url()`, `check_file_exists()`

**Mejoras:**
```python
class GCSStorageService:
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        self.client = storage.Client()
    
    def upload_file(self, local_path, destination_path):
        """Upload file and return public URL"""
        
    def upload_bytes(self, file_bytes, destination_path, content_type):
        """Upload bytes directly"""
        
    def get_signed_url(self, blob_name, expiration=3600):
        """Generate signed URL with expiration"""
```

---

### 2. **services/tts_service.py** (100-150 líneas)
**Responsabilidad:** Integración con ElevenLabs TTS

**Funciones a mover:**
- `generate_tts()` (línea 324)
- `generate_tts_preview()` (línea 370)
- Lógica de voice settings

**Mejoras:**
```python
class TTSService:
    def __init__(self, api_key=None, voice_id=None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.default_voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
    
    def generate_audio(self, text, voice_id=None, voice_settings=None):
        """Generate TTS audio"""
        
    def generate_preview(self, text, voice_id, settings):
        """Generate preview with custom settings"""
        
    def validate_text_length(self, text, max_chars=1000):
        """Validate text length"""
```

---

### 3. **services/music_service.py** (80-120 líneas)
**Responsabilidad:** Generación de música con IA

**Funciones a mover:**
- `generate_music_preview()` (línea 793)
- Lógica de generación de música en `generate_jingle()`

**Mejoras:**
```python
class MusicGenerationService:
    def __init__(self, api_key=None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
    
    def generate_music(self, prompt, duration_seconds):
        """Generate AI music"""
        
    def generate_preview(self, prompt, duration=5):
        """Generate short preview"""
        
    def validate_prompt(self, prompt):
        """Validate music prompt"""
```

---

### 4. **services/jingle_service.py** (150-200 líneas)
**Responsabilidad:** Orquestación de creación de jingles

**Funciones a mover:**
- Lógica de negocio de `generate_jingle()` (línea 516)
- Mixing de audio
- Gestión de archivos de jingles

**Mejoras:**
```python
class JingleService:
    def __init__(self, tts_service, music_service, storage_service):
        self.tts = tts_service
        self.music = music_service
        self.storage = storage_service
    
    def create_jingle(self, text, voice_id, music_prompt, voice_settings):
        """Create complete jingle (TTS + Music + Mix)"""
        
    def list_jingles(self, filters=None):
        """List available jingles"""
        
    def get_jingle_metadata(self, filename):
        """Get jingle metadata"""
        
    def delete_jingle(self, filename):
        """Delete jingle file"""
```

---

### 5. **services/schedule_service.py** (200-250 líneas)
**Responsabilidad:** Lógica de negocio para schedules

**Funciones a extraer:**
- Validación de schedules
- Evaluación de schedules activos
- Filtrado por venue/session

**Mejoras:**
```python
class ScheduleService:
    def create_schedule(self, schedule_data):
        """Create new jingle schedule with validation"""
        
    def get_active_schedules(self, venue_name=None, session_id=None):
        """Get currently active schedules"""
        
    def update_schedule(self, schedule_id, update_data):
        """Update schedule with validation"""
        
    def evaluate_schedule_now(self, schedule):
        """Check if schedule should be active now"""
        
    def get_schedules_by_priority(self, venue=None, session=None):
        """Get schedules sorted by priority"""
```

---

### 6. **services/card_generation_service.py** (150-200 líneas)
**Responsabilidad:** Generación de tarjetas de bingo

**Funciones a mover:**
- Lógica de negocio de `generate_cards_async()` (línea 97)
- Preparación de comandos
- Manejo de logos

**Mejoras:**
```python
class CardGenerationService:
    def prepare_generation_command(self, params):
        """Prepare command for card generation"""
        
    def validate_generation_params(self, params):
        """Validate generation parameters"""
        
    def handle_logo_data(self, logo_data):
        """Process and save logo data"""
        
    def execute_generation(self, command, task_id):
        """Execute generation command with progress tracking"""
```

---

### 7. **services/session_service.py** (150-200 líneas)
**Responsabilidad:** Gestión de sesiones de bingo

**Funciones a mover:**
- Lógica de negocio de session CRUD
- Validación de estados
- Gestión de logos

**Mejoras:**
```python
class BingoSessionService:
    def create_session(self, session_data):
        """Create new bingo session"""
        
    def update_session_status(self, session_id, new_status):
        """Update session status with validation"""
        
    def get_sessions_by_venue(self, venue_name):
        """Get all sessions for a venue"""
        
    def validate_session_transition(self, current_status, new_status):
        """Validate status transition"""
```

---

### 8. **tasks/jingle_generation_tasks.py** (200-250 líneas)
**Responsabilidad:** Tareas asíncronas para jingles

**Código a mover:**
- `background_jingle_generation()` (dentro de `generate_jingle`)
- Gestión de TaskStatus
- Progress tracking

**Mejoras:**
```python
class JingleGenerationTask:
    def __init__(self, task_id, jingle_service):
        self.task_id = task_id
        self.jingle_service = jingle_service
        self.task_status = TaskStatus.objects.get(task_id=task_id)
    
    def run(self, text, voice_id, music_prompt, voice_settings):
        """Execute jingle generation in background"""
        
    def update_progress(self, progress, step):
        """Update task progress"""
        
    def handle_completion(self, result):
        """Handle successful completion"""
        
    def handle_error(self, error):
        """Handle error state"""
```

---

### 9. **tasks/card_generation_tasks.py** (200-250 líneas)
**Responsabilidad:** Tareas asíncronas para tarjetas

**Código a mover:**
- `background_task()` (dentro de `generate_cards_async`)
- Progress tracking
- GCS upload

**Mejoras:**
```python
class CardGenerationTask:
    def __init__(self, task_id, card_service, storage_service):
        self.task_id = task_id
        self.card_service = card_service
        self.storage_service = storage_service
    
    def run(self, generation_params):
        """Execute card generation in background"""
        
    def parse_progress_output(self, output_line):
        """Parse progress from generation script output"""
        
    def upload_result_to_storage(self, pdf_path):
        """Upload generated PDF to GCS"""
```

---

### 10. **validators/schedule_validators.py** (80-100 líneas)
**Responsabilidad:** Validaciones de schedules

**Mejoras:**
```python
class ScheduleValidator:
    @staticmethod
    def validate_date_range(start_date, end_date):
        """Validate date range"""
        
    @staticmethod
    def validate_time_range(time_start, time_end):
        """Validate time range"""
        
    @staticmethod
    def validate_days_of_week(days_dict):
        """Ensure at least one day selected"""
        
    @staticmethod
    def validate_repeat_pattern(pattern):
        """Validate repeat pattern value"""
        
    @staticmethod
    def validate_jingle_file_exists(filename):
        """Check if jingle file exists"""
```

---

### 11. **validators/jingle_validators.py** (60-80 líneas)
**Responsabilidad:** Validaciones de jingles

```python
class JingleValidator:
    @staticmethod
    def validate_text(text, max_length=1000):
        """Validate jingle text"""
        
    @staticmethod
    def validate_music_prompt(prompt):
        """Validate music generation prompt"""
        
    @staticmethod
    def validate_voice_settings(settings):
        """Validate voice settings dictionary"""
        
    @staticmethod
    def validate_duration(duration):
        """Validate audio duration"""
```

---

### 12. **utils/config.py** (40-60 líneas)
**Responsabilidad:** Configuración centralizada

```python
class AppConfig:
    """Centralized application configuration"""
    
    # API Keys
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
    
    # GCS
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'music-bingo-cards')
    
    # Venue
    VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / 'data'
    FRONTEND_DIR = BASE_DIR / 'frontend'
    
    # Validation limits
    MAX_TEXT_LENGTH = 1000
    MAX_PLAYERS = 100
    MIN_JINGLE_DURATION = 5
    MAX_JINGLE_DURATION = 30
```

---

### 13. **utils/response_helpers.py** (50-70 líneas)
**Responsabilidad:** Helpers para respuestas HTTP

```python
class APIResponse:
    @staticmethod
    def success(data=None, message=None, status_code=200):
        """Standard success response"""
        
    @staticmethod
    def error(message, error_code=None, status_code=400):
        """Standard error response"""
        
    @staticmethod
    def task_created(task_id, status='pending'):
        """Response for async task creation"""
        
    @staticmethod
    def validation_error(errors):
        """Validation error response"""
```

---

### 14. **serializers/** (150-200 líneas total)
**Responsabilidad:** Django REST Framework serializers

```python
# serializers/jingle_serializers.py
class JingleCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    voice_id = serializers.CharField(required=False)
    music_prompt = serializers.CharField(max_length=500)
    voice_settings = serializers.JSONField(required=False)

# serializers/schedule_serializers.py
class JingleScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JingleSchedule
        fields = '__all__'

# serializers/session_serializers.py
class BingoSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BingoSession
        fields = '__all__'
```

---

### 15. **views/** (Dividido en 7 archivos, ~150-250 líneas cada uno)

#### **views/core_views.py** (50 líneas)
```python
@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy', 'message': 'Music Bingo API (Django)'})

@api_view(['GET'])
def get_pool(request):
    # Mantiene lógica simple de lectura
    pass

@api_view(['GET'])
def get_config(request):
    return Response({'venue_name': settings.VENUE_NAME})
```

#### **views/card_views.py** (150-200 líneas)
```python
from ..services.card_generation_service import CardGenerationService
from ..tasks.card_generation_tasks import CardGenerationTask
from ..serializers.task_serializers import CardGenerationSerializer

@api_view(['POST'])
def generate_cards_async(request):
    """Generate cards asynchronously"""
    serializer = CardGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    # Delegate to service
    card_service = CardGenerationService()
    task_id = card_service.create_generation_task(serializer.validated_data)
    
    # Start background task
    task = CardGenerationTask(task_id, card_service, storage_service)
    threading.Thread(target=task.run, args=(serializer.validated_data,)).start()
    
    return Response({'task_id': task_id}, status=202)

@api_view(['GET'])
def get_task_status(request, task_id):
    """Get generation task status"""
    # Simplified view logic
    pass
```

#### **views/jingle_views.py** (250-300 líneas)
```python
from ..services.jingle_service import JingleService
from ..services.tts_service import TTSService
from ..services.music_service import MusicGenerationService
from ..tasks.jingle_generation_tasks import JingleGenerationTask
from ..serializers.jingle_serializers import JingleCreateSerializer

@api_view(['POST'])
def generate_jingle(request):
    """Generate jingle (TTS + Music)"""
    # Use serializer for validation
    # Delegate to service
    # Start background task
    pass

@api_view(['GET'])
def list_jingles(request):
    """List all jingles"""
    jingle_service = JingleService()
    jingles = jingle_service.list_jingles()
    return Response({'jingles': jingles})

@api_view(['GET'])
def download_jingle(request, filename):
    """Download jingle file"""
    pass

@api_view(['GET', 'POST'])
def manage_playlist(request):
    """Manage jingle playlist"""
    pass
```

#### **views/schedule_views.py** (300-350 líneas)
```python
from ..services.schedule_service import ScheduleService
from ..serializers.schedule_serializers import JingleScheduleSerializer
from ..validators.schedule_validators import ScheduleValidator

@api_view(['POST', 'GET'])
def jingle_schedules(request):
    """Create or list jingle schedules"""
    if request.method == 'POST':
        serializer = JingleScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        schedule_service = ScheduleService()
        schedule = schedule_service.create_schedule(serializer.validated_data)
        return Response(serializer.data, status=201)
    else:
        # GET logic
        pass

@api_view(['GET'])
def get_active_jingles(request):
    """Get active jingle schedules"""
    schedule_service = ScheduleService()
    active = schedule_service.get_active_schedules(
        venue_name=request.GET.get('venue_name'),
        session_id=request.GET.get('session_id')
    )
    return Response({'active_jingles': active})

@api_view(['PUT'])
def update_jingle_schedule(request, schedule_id):
    """Update schedule"""
    pass

@api_view(['DELETE'])
def delete_jingle_schedule(request, schedule_id):
    """Delete schedule"""
    pass
```

#### **views/tts_views.py** (150-200 líneas)
```python
from ..services.tts_service import TTSService

@api_view(['POST'])
def generate_tts(request):
    """Generate TTS audio"""
    tts_service = TTSService()
    audio = tts_service.generate_audio(
        text=request.data.get('text'),
        voice_id=request.data.get('voice_id')
    )
    return HttpResponse(audio, content_type='audio/mpeg')

@api_view(['POST'])
def generate_tts_preview(request):
    """Generate TTS preview with custom settings"""
    pass

@api_view(['GET'])
def get_announcements(request):
    """Get announcements with venue name"""
    pass

@api_view(['GET'])
def get_ai_announcements(request):
    """Get AI-generated announcements"""
    pass

@api_view(['POST'])
def upload_logo(request):
    """Upload pub logo"""
    pass
```

#### **views/venue_views.py** (100-150 líneas)
```python
from ..serializers.venue_serializers import VenueConfigSerializer

@api_view(['GET', 'POST'])
def venue_config(request, venue_name):
    """Get or save venue configuration"""
    if request.method == 'GET':
        # Get config
        pass
    else:
        serializer = VenueConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        # Save config
        pass
```

#### **views/session_views.py** (200-250 líneas)
```python
from ..services.session_service import BingoSessionService
from ..serializers.session_serializers import BingoSessionSerializer

@api_view(['POST', 'GET'])
def bingo_sessions(request):
    """Create or list bingo sessions"""
    session_service = BingoSessionService()
    
    if request.method == 'POST':
        serializer = BingoSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        session = session_service.create_session(serializer.validated_data)
        return Response({'session_id': session.session_id}, status=201)
    else:
        # GET logic
        pass

@api_view(['GET', 'PUT', 'DELETE'])
def bingo_session_detail(request, session_id):
    """Get, update, or delete session"""
    pass

@api_view(['PATCH'])
def update_bingo_session_status(request, session_id):
    """Update session status"""
    session_service = BingoSessionService()
    session_service.update_status(session_id, request.data.get('status'))
    return Response({'success': True})
```

---

## 🔄 Actualización de URLs

**backend/api/urls.py** (después de refactor):
```python
from django.urls import path
from .views import (
    core_views,
    card_views,
    jingle_views,
    schedule_views,
    tts_views,
    venue_views,
    session_views
)

urlpatterns = [
    # Core
    path('health', core_views.health_check),
    path('pool', core_views.get_pool),
    path('config', core_views.get_config),
    
    # Card Generation
    path('generate-cards', card_views.generate_cards_async),
    path('tasks/<str:task_id>', card_views.get_task_status),
    
    # Jingles
    path('generate-jingle', jingle_views.generate_jingle),
    path('jingles', jingle_views.list_jingles),
    path('jingles/<str:filename>', jingle_views.download_jingle),
    path('jingle-tasks/<str:task_id>', jingle_views.get_jingle_status),
    path('playlist', jingle_views.manage_playlist),
    
    # Jingle Schedules
    path('jingle-schedules', schedule_views.jingle_schedules),
    path('jingle-schedules/active', schedule_views.get_active_jingles),
    path('jingle-schedules/<int:schedule_id>', schedule_views.update_jingle_schedule),
    path('jingle-schedules/<int:schedule_id>', schedule_views.delete_jingle_schedule),
    
    # TTS & Announcements
    path('generate-tts', tts_views.generate_tts),
    path('generate-tts-preview', tts_views.generate_tts_preview),
    path('announcements', tts_views.get_announcements),
    path('announcements-ai', tts_views.get_ai_announcements),
    path('upload-logo', tts_views.upload_logo),
    
    # Venue Configuration
    path('venue-config/<str:venue_name>', venue_views.venue_config),
    
    # Bingo Sessions
    path('bingo-sessions', session_views.bingo_sessions),
    path('bingo-sessions/<str:session_id>', session_views.bingo_session_detail),
    path('bingo-sessions/<str:session_id>/status', session_views.update_bingo_session_status),
]
```

---

## 📝 Plan de Implementación por Fases

### **FASE 1: Preparación (1-2 días)**
1. ✅ Crear plan de refactorización (este documento)
2. [ ] Configurar tests básicos para endpoints críticos
3. [ ] Crear branch: `refactor/views-modularization`
4. [ ] Backup del código actual

### **FASE 2: Extracción de Utilidades (1 día)**
1. [ ] Crear `utils/config.py` - mover configuraciones
2. [ ] Crear `utils/paths.py` - gestión de paths
3. [ ] Crear `utils/response_helpers.py`
4. [ ] Actualizar imports en `views.py`
5. [ ] Testing: verificar que todo funciona igual

### **FASE 3: Extracción de Servicios Core (2-3 días)**
1. [ ] Crear `services/storage_service.py` (GCS)
2. [ ] Crear `services/tts_service.py` (ElevenLabs TTS)
3. [ ] Crear `services/music_service.py` (Music generation)
4. [ ] Tests unitarios para cada servicio
5. [ ] Actualizar `views.py` para usar servicios

### **FASE 4: Extracción de Servicios de Dominio (2-3 días)**
1. [ ] Crear `services/jingle_service.py`
2. [ ] Crear `services/card_generation_service.py`
3. [ ] Crear `services/schedule_service.py`
4. [ ] Crear `services/session_service.py`
5. [ ] Tests unitarios para servicios de dominio

### **FASE 5: Extracción de Tasks Asíncronos (1-2 días)**
1. [ ] Crear `tasks/jingle_generation_tasks.py`
2. [ ] Crear `tasks/card_generation_tasks.py`
3. [ ] Mover lógica de background tasks
4. [ ] Tests de integración para tasks

### **FASE 6: Validadores y Serializers (1-2 días)**
1. [ ] Crear `validators/jingle_validators.py`
2. [ ] Crear `validators/schedule_validators.py`
3. [ ] Crear `validators/session_validators.py`
4. [ ] Crear todos los serializers en `serializers/`
5. [ ] Tests para validadores

### **FASE 7: División de Views (2-3 días)**
1. [ ] Crear estructura de paquete `views/`
2. [ ] Crear `views/core_views.py`
3. [ ] Crear `views/card_views.py`
4. [ ] Crear `views/jingle_views.py`
5. [ ] Crear `views/schedule_views.py`
6. [ ] Crear `views/tts_views.py`
7. [ ] Crear `views/venue_views.py`
8. [ ] Crear `views/session_views.py`
9. [ ] Actualizar `urls.py`
10. [ ] Testing de integración completo

### **FASE 8: Limpieza y Optimización (1-2 días)**
1. [ ] Eliminar código duplicado
2. [ ] Optimizar imports
3. [ ] Revisar manejo de errores
4. [ ] Documentación de código (docstrings)
5. [ ] Actualizar documentación del proyecto

### **FASE 9: Testing Final (1-2 días)**
1. [ ] Tests de integración end-to-end
2. [ ] Tests de regresión
3. [ ] Performance testing
4. [ ] Code review

### **FASE 10: Deployment (1 día)**
1. [ ] Merge a `main`
2. [ ] Deploy a staging
3. [ ] Smoke tests en staging
4. [ ] Deploy a producción
5. [ ] Monitoring post-deployment

---

## ✅ Checklist de Tareas Críticas

### Pre-refactor:
- [ ] Backup completo del código
- [ ] Tests de endpoints críticos funcionando
- [ ] Documentación de APIs existentes
- [ ] Plan de rollback definido

### Durante refactor:
- [ ] Mantener compatibilidad con URLs existentes
- [ ] No romper contratos de API
- [ ] Tests pasando después de cada cambio
- [ ] Commits atómicos y descriptivos

### Post-refactor:
- [ ] Todos los tests pasando
- [ ] Performance igual o mejor que antes
- [ ] Documentación actualizada
- [ ] Code coverage >= 80%

---

## 🎯 Beneficios Esperados

### Mantenibilidad:
- ✅ Archivos de ~150-250 líneas vs 1841 actual
- ✅ Responsabilidades claras por módulo
- ✅ Fácil localización de bugs

### Testabilidad:
- ✅ Servicios testables unitariamente
- ✅ Mocking simplificado
- ✅ Tests de integración más rápidos

### Escalabilidad:
- ✅ Fácil agregar nuevas features
- ✅ Reutilización de código
- ✅ Mejor separación de concerns

### Performance:
- ✅ Imports optimizados
- ✅ Lazy loading de servicios
- ✅ Mejor gestión de recursos

### Developer Experience:
- ✅ Navegación más fácil
- ✅ Onboarding más rápido
- ✅ Menos merge conflicts

---

## 🚨 Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Romper APIs existentes | Media | Alto | Tests de regresión, feature flags |
| Introducir bugs | Media | Alto | Code review, tests extensivos |
| Performance degradation | Baja | Medio | Benchmarking antes/después |
| Incompatibilidad con frontend | Baja | Alto | Mantener contratos de API |
| Tiempo de desarrollo mayor | Alta | Medio | Planificación por fases |

---

## 📊 Métricas de Éxito

### Antes del Refactor:
- **Líneas de código:** 1841 en un archivo
- **Complejidad ciclomática:** Alta
- **Test coverage:** ~40%
- **Tiempo de CI:** X minutos

### Después del Refactor (Objetivos):
- **Archivos totales:** ~25 archivos modulares
- **Líneas promedio por archivo:** <250
- **Complejidad ciclomática:** Baja/Media
- **Test coverage:** ≥80%
- **Tiempo de CI:** ≤X minutos

---

## 🔗 Referencias y Recursos

### Patrones de Diseño:
- Service Layer Pattern
- Repository Pattern
- Dependency Injection
- Factory Pattern

### Django Best Practices:
- [Django REST Framework - Best Practices](https://www.django-rest-framework.org/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [Django Design Patterns](https://django-design-patterns.readthedocs.io/)

### Testing:
- pytest-django
- factory_boy
- django-test-plus

---

## 📌 Notas Finales

Este refactor es una **inversión a largo plazo** en la calidad y mantenibilidad del código. Aunque tomará tiempo inicial, los beneficios se verán en:

1. **Desarrollo más rápido** de nuevas features
2. **Menos bugs** en producción
3. **Onboarding más fácil** de nuevos developers
4. **Mejor colaboración** en equipo (menos merge conflicts)
5. **Código más testeable** y confiable

**Tiempo estimado total:** 12-18 días de trabajo

**Prioridad:** Alta (deuda técnica crítica)

**Aprobación necesaria:** Product Owner / Tech Lead

---

**Documento creado:** 31 de enero de 2026  
**Autor:** GitHub Copilot  
**Estado:** ✅ Aprobado para implementación  
**Próximo paso:** Comenzar Fase 1 - Preparación
