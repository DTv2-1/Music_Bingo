"""
Music Bingo API Views - Django REST Framework
Refactored to use modular views structure from views/ package

All view functions are now organized in the views/ subdirectory:
- views/core_views.py: Health check, pool, session, task status, config
- views/card_views.py: Card generation and logo upload
- views/tts_views.py: Text-to-speech generation and announcements
- views/jingle_views.py: Jingle management and generation
- views/pub_quiz_views.py: Pub quiz functionality
- views/bingo_session_views.py: Bingo session management
"""

import os
import logging
from pathlib import Path
from google.cloud import storage

# Import TaskStatus model
from .models import TaskStatus

logger = logging.getLogger(__name__)

# GCS Configuration
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'music-bingo-cards')

def upload_to_gcs(local_file_path, destination_blob_name):
    """
    Upload a file to Google Cloud Storage and return a public URL
    Files are auto-deleted after 7 days via bucket lifecycle policy
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        
        # Upload the file
        blob.upload_from_filename(local_file_path)
        logger.info(f"✅ Uploaded {local_file_path} to gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
        
        # Make blob publicly readable
        blob.make_public()
        logger.info(f"✅ Made blob public: {blob.public_url}")
        
        # Return public URL
        return blob.public_url
    except Exception as e:
        logger.error(f"❌ Failed to upload to GCS: {e}")
        raise


# Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')

# Paths - Fix for Docker container structure
BASE_DIR = Path(__file__).resolve().parent.parent  # /app/api -> /app
DATA_DIR = BASE_DIR / 'data'  # /app/data
FRONTEND_DIR = BASE_DIR / 'frontend'  # /app/frontend

# Import all view functions from modular structure
from .views import (
    # Core views
    health_check,
    get_pool,
    get_session,
    get_task_status,
    get_config,
    
    # Card generation views
    generate_cards_async,
    upload_logo,
    
    # TTS views
    generate_tts,
    generate_tts_preview,
    get_announcements,
    get_ai_announcements,
    
    # Jingle views
    generate_jingle,
    get_jingle_status,
    download_jingle,
    generate_music_preview,
    list_jingles,
    manage_playlist,
    
    # Schedule views
    create_jingle_schedule,
    get_active_jingles,
    update_jingle_schedule,
    delete_jingle_schedule,
    
    # Venue views
    venue_config,
    
    # Session views
    bingo_sessions,
    bingo_session_detail,
    update_bingo_session_status,
)

# All views are now imported from the modular structure
# No view logic should be defined here - only imports and utility functions (like upload_to_gcs)
