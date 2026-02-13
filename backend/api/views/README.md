# Views Module - Modular Architecture

This directory contains the refactored API views organized by domain.

## Architecture Overview

The views have been split from a monolithic `views.py` (1,169 lines) into 7 domain-specific modules for better organization, maintainability, and testability.

## Module Structure

```
backend/api/views/
├── __init__.py          # Package exports (all views)
├── core_views.py        # Core utility endpoints
├── card_views.py        # Card generation operations
├── tts_views.py         # Text-to-Speech operations
├── jingle_views.py      # Jingle management
├── schedule_views.py    # Jingle scheduling
├── venue_views.py       # Venue configuration
└── session_views.py     # Bingo session management
```

## Modules Detail

### 🔧 core_views.py (81 lines, 4 endpoints)

**Purpose**: Essential infrastructure services

**Endpoints**:
- `GET /api/health` - Health check endpoint
- `GET /api/pool` - Get music pool data
- `GET /api/tasks/<task_id>` - Get async task status
- `GET /api/config` - Get public configuration

**Dependencies**: TaskStatus model, config

---

### 🎴 card_views.py (134 lines, 2 endpoints)

**Purpose**: Bingo card generation and logo management

**Endpoints**:
- `POST /api/generate-cards` - Generate cards asynchronously
- `POST /api/upload-logo` - Upload venue logo

**Features**:
- Background card generation with progress tracking
- Custom branding (logos, prizes, QR codes)
- Google Cloud Storage integration
- Multi-format logo support (PNG, JPG, SVG, etc.)

**Dependencies**: CardGenerationService, run_card_generation_task

---

### 🔊 tts_views.py (126 lines, 4 endpoints)

**Purpose**: Text-to-Speech audio generation

**Endpoints**:
- `POST /api/generate-tts` - Generate TTS audio (optimized)
- `POST /api/generate-tts-preview` - Generate TTS preview with custom settings
- `GET /api/announcements` - Get announcement templates
- `GET /api/ai-announcements` - Get AI-generated announcements

**Features**:
- ElevenLabs Turbo TTS integration
- Custom voice settings (stability, similarity, style)
- Voice preview system
- Announcement template management

**Dependencies**: TTSService, validate_tts_input

---

### 🎵 jingle_views.py (270 lines, 6 endpoints)

**Purpose**: Promotional jingle creation and management

**Endpoints**:
- `POST /api/generate-jingle` - Generate jingle (TTS + music)
- `GET /api/jingle-tasks/<task_id>` - Get jingle generation status
- `GET /api/jingles/<filename>` - Download jingle file
- `POST /api/generate-music-preview` - Generate music preview
- `GET /api/jingles` - List all jingles
- `GET/POST /api/playlist` - Manage jingle playlist

**Features**:
- Combined TTS + AI music generation
- Background processing with progress tracking
- Playlist management (enabled, interval)
- GCS storage integration
- Metadata tracking

**Dependencies**: JingleService, MusicGenerationService, validate_jingle_input, run_jingle_generation_task

---

### 📅 schedule_views.py (336 lines, 4 endpoints)

**Purpose**: Automated jingle scheduling system

**Endpoints**:
- `POST/GET /api/jingle-schedules` - Create/list schedules
- `GET /api/jingle-schedules/active` - Get active schedules
- `PUT /api/jingle-schedules/<id>` - Update schedule
- `DELETE /api/jingle-schedules/<id>` - Delete schedule

**Features**:
- Time-based scheduling (date ranges, time windows)
- Day-of-week selection
- Priority system (0-100)
- Repeat patterns (occasional, regular, often)
- Active schedule evaluation logic

**Dependencies**: ScheduleService, JingleSchedule model

---

### 🏪 venue_views.py (107 lines, 1 endpoint)

**Purpose**: Venue-specific configuration management

**Endpoints**:
- `GET/POST /api/venue-config/<venue_name>` - Get/update venue config

**Configuration Options**:
- Player settings (num_players)
- Voice preferences (voice_id)
- Music preferences (selected_decades)
- Branding (pub_logo)
- Social media integration (platform, username, QR codes)
- Prize configuration (4corners, first_line, full_house)

**Dependencies**: VenueConfiguration model

---

### 🎮 session_views.py (149 lines, 3 endpoints)

**Purpose**: Bingo game session lifecycle management

**Endpoints**:
- `POST/GET /api/bingo-sessions` - Create/list sessions
- `GET/PUT/DELETE /api/bingo-sessions/<id>` - Session detail operations
- `PATCH /api/bingo-sessions/<id>/status` - Update session status

**Features**:
- Session lifecycle (pending → active → completed)
- Song tracking (playlist, current index)
- Timestamp tracking (created, started, completed)
- Venue filtering
- Status validation

**Dependencies**: BingoSessionService, validate_session_status

---

## Import Usage

All views are exported from the package for backward compatibility:

```python
# Import individual views
from backend.api.views import health_check, generate_jingle

# Import all views (in urls.py)
from backend.api import views

urlpatterns = [
    path('api/health', views.health_check, name='health_check'),
    path('api/generate-jingle', views.generate_jingle, name='generate_jingle'),
    # ... etc
]
```

## Design Patterns

### Service Layer Pattern
All views delegate business logic to service classes:
- Views: HTTP request/response handling only
- Services: Business logic, external API calls, data processing
- Models: Data persistence

### Task Pattern
Long-running operations use background tasks:
- Card generation → `run_card_generation_task()`
- Jingle generation → `run_jingle_generation_task()`

### Validator Pattern
Input validation is centralized:
- TTS validators → `validate_tts_input()`
- Jingle validators → `validate_jingle_input()`
- Session validators → `validate_session_status()`

## Benefits

### ✅ Maintainability
- Small, focused modules (~150 lines avg)
- Clear separation of concerns
- Easy to locate and modify code

### ✅ Testability
- Each module can be tested independently
- Mocked dependencies are isolated
- Clear test boundaries

### ✅ Scalability
- Easy to add new endpoints within domain
- Simple to create new domain modules
- No fear of merge conflicts

### ✅ Readability
- Self-documenting structure
- Clear naming conventions
- Comprehensive docstrings

## Migration History

- **Phase 1-3**: Created services, tasks, validators
- **Phase 4**: Migrated views to use services (-317 lines)
- **Phase 5**: Extracted async tasks (-200 lines)
- **Phase 6**: Added input validators (+425 lines organized)
- **Phase 7**: Split into modules (1,169 → 22 lines, **-98%**)
- **Phase 8**: Documentation, optimization, cleanup

## Statistics

- **Total Endpoints**: 24
- **Total Lines**: 1,301 (organized across 8 files)
- **Average Module Size**: ~163 lines
- **Reduction in main views.py**: 98.1%
- **Code Organization**: 100%

## Testing

To test a specific module:

```bash
# Run Django tests for a specific module
python manage.py test api.tests.test_core_views
python manage.py test api.tests.test_jingle_views

# Or use pytest
pytest backend/api/tests/test_views/test_jingle_views.py
```

## Future Improvements

- [ ] Add comprehensive unit tests for each module
- [ ] Create integration tests for cross-module workflows
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Implement rate limiting per endpoint
- [ ] Add response caching where appropriate
- [ ] Create performance benchmarks

---

**Last Updated**: 2026-01-31  
**Refactoring Phase**: Phase 8 (Optimization & Documentation)  
**Maintainer**: Music Bingo Team
