"""
Modular Views Package

This package organizes API views by domain:
- core_views: Health check, pool data, task status, config
- card_views: Card generation and logo upload
- tts_views: Text-to-Speech operations and announcements
- jingle_views: Jingle generation, listing, and playlist management
- schedule_views: Jingle schedule CRUD operations
- venue_views: Venue-specific configuration
- session_views: Bingo session management
"""

# Core utilities
from .core_views import (
    health_check,
    get_pool,
    get_session,
    get_task_status,
    get_config
)

# Card generation
from .card_views import (
    generate_cards_async,
    upload_logo
)

# Text-to-Speech
from .tts_views import (
    generate_tts,
    generate_tts_preview,
    get_announcements,
    get_ai_announcements
)

# Jingle management
from .jingle_views import (
    generate_jingle,
    get_jingle_status,
    download_jingle,
    generate_music_preview,
    list_jingles,
    manage_playlist
)

# Schedule management
from .schedule_views import (
    create_jingle_schedule,
    get_active_jingles,
    update_jingle_schedule,
    delete_jingle_schedule
)

# Venue configuration
from .venue_views import (
    venue_config
)

# Session management
from .session_views import (
    bingo_sessions,
    bingo_session_detail,
    update_bingo_session_status
)
__all__ = [
    # Core
    'health_check',
    'get_pool',
    'get_session',
    'get_task_status',
    'get_config',tus',
    'get_config',
    # Card
    'generate_cards_async',
    'upload_logo',
    # TTS
    'generate_tts',
    'generate_tts_preview',
    'get_announcements',
    'get_ai_announcements',
    # Jingle
    'generate_jingle',
    'get_jingle_status',
    'download_jingle',
    'generate_music_preview',
    'list_jingles',
    'manage_playlist',
    # Schedule
    'create_jingle_schedule',
    'get_active_jingles',
    'update_jingle_schedule',
    'delete_jingle_schedule',
    # Venue
    'venue_config',
    # Session
    'bingo_sessions',
    'bingo_session_detail',
    'update_bingo_session_status',
]
