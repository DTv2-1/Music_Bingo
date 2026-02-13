"""
AI Music Generation Service using ElevenLabs Sound Generation API
Handles background music creation for jingles
"""

import logging
import io
from typing import Optional

import requests
from pydub import AudioSegment
from pydub.generators import Sine

from ..utils.config import (
    ELEVENLABS_API_KEY,
    AppConfig
)

logger = logging.getLogger(__name__)


class MusicGenerationService:
    """
    AI Music Generation service using ElevenLabs Sound Generation API
    
    Features:
    - Generate AI music from text prompts
    - Preview generation for testing prompts
    - Fallback to simple tones if API fails
    - Duration validation
    """
    
    # ElevenLabs API endpoints
    BASE_URL = 'https://api.elevenlabs.io/v1'
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Music Generation Service
        
        Args:
            api_key: ElevenLabs API key (defaults to config)
        """
        self.api_key = api_key or ELEVENLABS_API_KEY
        
        if not self.api_key:
            logger.warning("⚠️ ElevenLabs API key not configured")
    
    def _get_headers(self) -> dict:
        """Get standard headers for ElevenLabs API"""
        return {
            'xi-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def validate_prompt(self, prompt: str, max_chars: Optional[int] = None) -> bool:
        """
        Validate music generation prompt
        
        Args:
            prompt: Music prompt to validate
            max_chars: Maximum characters (defaults to config)
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If prompt is invalid
        """
        max_chars = max_chars or AppConfig.MAX_MUSIC_PROMPT_LENGTH
        
        if not prompt or not prompt.strip():
            raise ValueError("Music prompt cannot be empty")
        
        if len(prompt) > max_chars:
            raise ValueError(f"Prompt too long: {len(prompt)} characters (max: {max_chars})")
        
        return True
    
    def validate_duration(self, duration: int) -> bool:
        """
        Validate music duration
        
        Args:
            duration: Duration in seconds
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If duration is out of range
        """
        if duration < AppConfig.MIN_JINGLE_DURATION:
            raise ValueError(f"Duration too short: {duration}s (min: {AppConfig.MIN_JINGLE_DURATION}s)")
        
        if duration > AppConfig.MAX_JINGLE_DURATION:
            raise ValueError(f"Duration too long: {duration}s (max: {AppConfig.MAX_JINGLE_DURATION}s)")
        
        return True
    
    def generate_music(
        self,
        prompt: str,
        duration_seconds: int,
        use_fallback_on_error: bool = True
    ) -> bytes:
        """
        Generate AI music from text prompt
        
        Args:
            prompt: Text description of desired music (e.g., "upbeat pub guitar music")
            duration_seconds: Length of music in seconds
            use_fallback_on_error: Use simple tone if API fails (default: True)
            
        Returns:
            bytes: Audio content as MP3
            
        Raises:
            ValueError: If parameters are invalid
            requests.HTTPError: If API request fails and fallback disabled
            
        Example:
            >>> service = MusicGenerationService()
            >>> music = service.generate_music("energetic guitar riff", 10)
            >>> with open('music.mp3', 'wb') as f:
            ...     f.write(music)
        """
        if not self.api_key:
            if use_fallback_on_error:
                logger.warning("⚠️ API key not configured, using fallback tone")
                return self._generate_fallback_tone(duration_seconds)
            raise ValueError("ElevenLabs API key not configured")
        
        # Validate parameters
        self.validate_prompt(prompt)
        self.validate_duration(duration_seconds)
        
        # Build request
        url = f'{self.BASE_URL}/sound-generation'
        payload = {
            'text': prompt,
            'duration_seconds': duration_seconds
        }
        
        logger.info(f"🎵 Generating music: '{prompt}' ({duration_seconds}s)")
        
        try:
            # Make request
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60  # Music generation can take longer
            )
            
            if not response.ok:
                error_msg = f'ElevenLabs Music API error: {response.status_code}'
                logger.error(f"❌ {error_msg} - {response.text}")
                
                if use_fallback_on_error:
                    logger.warning("⚠️ Using fallback tone due to API error")
                    return self._generate_fallback_tone(duration_seconds)
                
                response.raise_for_status()
            
            music_bytes = response.content
            logger.info(f"✅ Music generated: {len(music_bytes)} bytes")
            
            return music_bytes
            
        except requests.RequestException as e:
            logger.error(f"❌ Music generation failed: {e}")
            
            if use_fallback_on_error:
                logger.warning("⚠️ Using fallback tone due to request error")
                return self._generate_fallback_tone(duration_seconds)
            
            raise
    
    def generate_preview(
        self,
        prompt: str,
        duration: int = 5
    ) -> bytes:
        """
        Generate a short music preview for testing prompts
        
        Args:
            prompt: Music description
            duration: Duration in seconds (default: 5)
            
        Returns:
            bytes: Audio content as MP3
            
        Example:
            >>> service = MusicGenerationService()
            >>> preview = service.generate_preview("jazz piano")
        """
        # Ensure duration is within preview range
        duration = max(AppConfig.MIN_JINGLE_DURATION, min(duration, 10))
        
        logger.info(f"🎵 Generating music preview: '{prompt}' ({duration}s)")
        
        return self.generate_music(
            prompt=prompt,
            duration_seconds=duration,
            use_fallback_on_error=True
        )
    
    def _generate_fallback_tone(self, duration_seconds: int) -> bytes:
        """
        Generate a simple fallback tone when API is unavailable
        
        Args:
            duration_seconds: Duration in seconds
            
        Returns:
            bytes: Simple tone as MP3
        """
        logger.info(f"🎵 Generating fallback tone: {duration_seconds}s")
        
        try:
            # Generate a simple 440Hz tone (A4)
            tone = Sine(440).to_audio_segment(duration=duration_seconds * 1000)
            
            # Apply gain reduction to make it quieter
            tone = tone.apply_gain(-20)
            
            # Export to MP3
            output = io.BytesIO()
            tone.export(output, format='mp3')
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Failed to generate fallback tone: {e}")
            raise
    
    def estimate_generation_time(self, duration_seconds: int) -> int:
        """
        Estimate time required to generate music
        
        Args:
            duration_seconds: Music duration
            
        Returns:
            int: Estimated generation time in seconds
            
        Note:
            This is approximate. Actual time depends on API load.
        """
        # Rough estimate: ~2-3 seconds per second of music
        return duration_seconds * 3
