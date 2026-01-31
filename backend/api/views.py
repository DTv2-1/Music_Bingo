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

# Import all views from modular package for backward compatibility
# This allows existing URL patterns to continue working without modification
from .views import *  # noqa: F401, F403


