"""
Text-to-Speech Service using ElevenLabs API
Handles voice generation, previews, and voice settings
"""

import logging
from typing import Optional, Dict, Any

import requests

from ..utils.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    AppConfig
)

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service using ElevenLabs API
    
    Features:
    - Generate TTS audio with custom voice settings
    - Preview generation with different voices
    - Text validation and length checking
    - Support for multiple models (multilingual, turbo)
    """
    
    # ElevenLabs API endpoints
    BASE_URL = 'https://api.elevenlabs.io/v1'
    
    def __init__(self, api_key: Optional[str] = None, default_voice_id: Optional[str] = None):
        """
        Initialize TTS Service
        
        Args:
            api_key: ElevenLabs API key (defaults to config)
            default_voice_id: Default voice ID to use (defaults to config)
        """
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.default_voice_id = default_voice_id or ELEVENLABS_VOICE_ID
        
        if not self.api_key:
            logger.warning("⚠️ ElevenLabs API key not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for ElevenLabs API"""
        return {
            'xi-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def validate_text_length(self, text: str, max_chars: Optional[int] = None) -> bool:
        """
        Validate text length for TTS
        
        Args:
            text: Text to validate
            max_chars: Maximum characters allowed (defaults to config)
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If text is too long
        """
        max_chars = max_chars or AppConfig.MAX_TEXT_LENGTH
        
        if len(text) > max_chars:
            raise ValueError(f"Text too long: {len(text)} characters (max: {max_chars})")
        
        return True
    
    def generate_audio(
        self,
        text: str,
        voice_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
        model_id: str = 'eleven_multilingual_v2',
        optimize_streaming: bool = True
    ) -> bytes:
        """
        Generate TTS audio from text
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (defaults to configured voice)
            voice_settings: Custom voice settings (stability, similarity_boost, etc.)
            model_id: ElevenLabs model to use
            optimize_streaming: Enable streaming optimization
            
        Returns:
            bytes: Audio content as MP3
            
        Raises:
            ValueError: If text validation fails
            requests.HTTPError: If API request fails
            
        Example:
            >>> service = TTSService()
            >>> audio = service.generate_audio("Hello world")
            >>> with open('output.mp3', 'wb') as f:
            ...     f.write(audio)
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        # Validate text
        self.validate_text_length(text)
        
        # Use default voice if not specified
        voice_id = voice_id or self.default_voice_id
        
        # Use default voice settings if not provided
        if voice_settings is None:
            voice_settings = AppConfig.DEFAULT_TTS_VOICE_SETTINGS.copy()
        
        # Build request URL
        url = f'{self.BASE_URL}/text-to-speech/{voice_id}'
        
        # Build payload
        payload = {
            'text': text,
            'model_id': model_id,
            'voice_settings': voice_settings,
            'output_format': AppConfig.TTS_OUTPUT_FORMAT
        }
        
        if optimize_streaming:
            payload['optimize_streaming_latency'] = 1
        
        logger.info(f"🎤 Generating TTS: {len(text)} chars, voice={voice_id}, model={model_id}")
        
        # Make request
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=30
        )
        
        if not response.ok:
            error_msg = f'ElevenLabs API error: {response.status_code}'
            logger.error(f"❌ {error_msg} - {response.text}")
            response.raise_for_status()
        
        audio_bytes = response.content
        logger.info(f"✅ TTS generated: {len(audio_bytes)} bytes")
        
        return audio_bytes
    
    def generate_preview(
        self,
        text: str,
        voice_id: str,
        voice_settings: Dict[str, Any]
    ) -> bytes:
        """
        Generate a preview with custom voice settings
        Useful for testing different voice configurations
        
        Args:
            text: Text to convert (usually short)
            voice_id: Voice ID to use
            voice_settings: Voice settings to test
            
        Returns:
            bytes: Audio content as MP3
            
        Example:
            >>> service = TTSService()
            >>> settings = {
            ...     'stability': 0.5,
            ...     'similarity_boost': 0.75,
            ...     'style': 0.5,
            ...     'use_speaker_boost': True
            ... }
            >>> audio = service.generate_preview("Test", "voice_id", settings)
        """
        logger.info(f"🎤 Generating TTS preview: voice={voice_id}, settings={voice_settings}")
        
        return self.generate_audio(
            text=text,
            voice_id=voice_id,
            voice_settings=voice_settings,
            model_id='eleven_multilingual_v2',
            optimize_streaming=True
        )
    
    def generate_turbo(
        self,
        text: str,
        voice_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate TTS using the faster Turbo model
        Good for real-time applications
        
        Args:
            text: Text to convert
            voice_id: Voice ID (defaults to configured voice)
            voice_settings: Voice settings (defaults to config)
            
        Returns:
            bytes: Audio content as MP3
        """
        return self.generate_audio(
            text=text,
            voice_id=voice_id,
            voice_settings=voice_settings,
            model_id=AppConfig.TTS_TURBO_MODEL_ID,
            optimize_streaming=True
        )
    
    def list_voices(self) -> Dict[str, Any]:
        """
        List all available voices from ElevenLabs
        
        Returns:
            dict: Available voices
            
        Example:
            >>> service = TTSService()
            >>> voices = service.list_voices()
            >>> for voice in voices['voices']:
            ...     print(voice['name'], voice['voice_id'])
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        url = f'{self.BASE_URL}/voices'
        
        response = requests.get(
            url,
            headers=self._get_headers(),
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_voice_settings(self, voice_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get default settings for a specific voice
        
        Args:
            voice_id: Voice ID (defaults to configured voice)
            
        Returns:
            dict: Voice settings
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        voice_id = voice_id or self.default_voice_id
        url = f'{self.BASE_URL}/voices/{voice_id}/settings'
        
        response = requests.get(
            url,
            headers=self._get_headers(),
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
