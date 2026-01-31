"""
Centralized configuration for Music Bingo API
All environment variables and constants in one place
"""

import os
from pathlib import Path


class AppConfig:
    """Centralized application configuration"""
    
    # ============================================================================
    # API KEYS & EXTERNAL SERVICES
    # ============================================================================
    
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
    
    # ============================================================================
    # GOOGLE CLOUD STORAGE
    # ============================================================================
    
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'music-bingo-cards')
    
    # ============================================================================
    # VENUE CONFIGURATION
    # ============================================================================
    
    VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')
    
    # ============================================================================
    # FILE PATHS
    # ============================================================================
    
    # Docker WORKDIR is /app, files are copied as: COPY backend/ . COPY data/ ./data/
    # So from /app/api/utils/config.py we need to go to /app/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent  # /app/api/utils -> /app
    DATA_DIR = BASE_DIR / 'data'  # /app/data
    FRONTEND_DIR = BASE_DIR / 'frontend'  # /app/frontend
    
    # ============================================================================
    # VALIDATION LIMITS
    # ============================================================================
    
    # Text & Content
    MAX_TEXT_LENGTH = 1000  # Maximum characters for jingle text
    MAX_MUSIC_PROMPT_LENGTH = 500  # Maximum characters for music prompt
    
    # Players & Cards
    MAX_PLAYERS = 100
    MIN_PLAYERS = 1
    DEFAULT_NUM_PLAYERS = 25
    
    # Jingle Duration
    MIN_JINGLE_DURATION = 5  # seconds
    MAX_JINGLE_DURATION = 30  # seconds
    DEFAULT_JINGLE_DURATION = 10  # seconds
    
    # Schedule Priority
    MIN_PRIORITY = 0
    MAX_PRIORITY = 100
    DEFAULT_PRIORITY = 0
    
    # ============================================================================
    # FILE UPLOAD SETTINGS
    # ============================================================================
    
    ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'}
    MAX_LOGO_SIZE_MB = 10  # Maximum logo file size in MB
    
    # ============================================================================
    # TTS SETTINGS
    # ============================================================================
    
    # Default voice settings for ElevenLabs TTS
    DEFAULT_TTS_VOICE_SETTINGS = {
        'stability': 0.5,
        'similarity_boost': 0.75,
        'style': 0.5,
        'use_speaker_boost': True
    }
    
    # TTS Model configuration
    TTS_MODEL_ID = 'eleven_multilingual_v2'
    TTS_TURBO_MODEL_ID = 'eleven_turbo_v2_5'
    TTS_OUTPUT_FORMAT = 'mp3_44100_128'
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    @classmethod
    def get_data_path(cls, *subdirs):
        """
        Get a path within the data directory
        
        Args:
            *subdirs: Path components (e.g., 'jingles', 'file.mp3')
            
        Returns:
            Path: Resolved path within DATA_DIR
            
        Example:
            >>> AppConfig.get_data_path('jingles', 'file.mp3')
            Path('/app/data/jingles/file.mp3')
        """
        return cls.DATA_DIR.joinpath(*subdirs)
    
    @classmethod
    def validate_api_keys(cls):
        """
        Validate that required API keys are configured
        
        Returns:
            dict: Dictionary with validation results
            
        Example:
            >>> AppConfig.validate_api_keys()
            {'elevenlabs': True, 'gcs': True}
        """
        return {
            'elevenlabs': bool(cls.ELEVENLABS_API_KEY),
            'gcs': bool(cls.GCS_BUCKET_NAME),
        }
    
    @classmethod
    def is_production(cls):
        """Check if running in production environment"""
        return os.getenv('ENVIRONMENT', 'development') == 'production'
    
    @classmethod
    def is_development(cls):
        """Check if running in development environment"""
        return os.getenv('ENVIRONMENT', 'development') == 'development'


# Convenience exports
BASE_DIR = AppConfig.BASE_DIR
DATA_DIR = AppConfig.DATA_DIR
FRONTEND_DIR = AppConfig.FRONTEND_DIR
ELEVENLABS_API_KEY = AppConfig.ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID = AppConfig.ELEVENLABS_VOICE_ID
GCS_BUCKET_NAME = AppConfig.GCS_BUCKET_NAME
VENUE_NAME = AppConfig.VENUE_NAME
