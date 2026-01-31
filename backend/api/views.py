"""
Music Bingo API Views - Django REST Framework

⚠️ This file now imports all views from modular packages.

All API views have been refactored into domain-specific modules:
- backend/api/views/core_views.py: Health check, pool data, task status, config
- backend/api/views/card_views.py: Card generation and logo upload
- backend/api/views/tts_views.py: Text-to-Speech operations and announcements
- backend/api/views/jingle_views.py: Jingle generation, listing, and playlist management
- backend/api/views/schedule_views.py: Jingle schedule CRUD operations
- backend/api/views/venue_views.py: Venue-specific configuration
- backend/api/views/session_views.py: Bingo session management

This provides better organization, maintainability, and testability.
"""

# Import all views from modular views package for backward compatibility
# This allows existing URL patterns to continue working without modification
# Using relative imports from within the api package
from .views.core_views import health_check, get_pool, get_task_status, get_config
from .views.card_views import generate_cards_async, upload_logo
from .views.tts_views import generate_tts, generate_tts_preview, get_announcements, get_ai_announcements
from .views.jingle_views import generate_jingle, get_jingle_status, download_jingle, generate_music_preview, list_jingles, manage_playlist
from .views.schedule_views import create_jingle_schedule, get_active_jingles, update_jingle_schedule, delete_jingle_schedule
from .views.venue_views import venue_config
from .views.session_views import bingo_sessions, bingo_session_detail, update_bingo_session_status

__all__ = [
    # Core
    'health_check', 'get_pool', 'get_task_status', 'get_config',
    # Card
    'generate_cards_async', 'upload_logo',
    # TTS
    'generate_tts', 'generate_tts_preview', 'get_announcements', 'get_ai_announcements',
    # Jingle
    'generate_jingle', 'get_jingle_status', 'download_jingle', 'generate_music_preview',
    'list_jingles', 'manage_playlist',
    # Schedule
    'create_jingle_schedule', 'get_active_jingles', 'update_jingle_schedule', 'delete_jingle_schedule',
    # Venue
    'venue_config',
    # Session
    'bingo_sessions', 'bingo_session_detail', 'update_bingo_session_status',
]

