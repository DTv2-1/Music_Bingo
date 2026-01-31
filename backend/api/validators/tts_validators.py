"""
TTS Input Validators
Validates text-to-speech inputs
"""

from typing import Dict, Any


def validate_text_length(text: str, max_length: int = 1000) -> None:
    """
    Validate text length for TTS
    
    Args:
        text: Text to validate
        max_length: Maximum allowed length (default 1000)
        
    Raises:
        ValueError: If text exceeds max length
    """
    if len(text) > max_length:
        raise ValueError(f'Text too long (max {max_length} characters / ~{max_length // 5} words)')


def validate_tts_input(data: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Validate TTS input data
    
    Args:
        data: Request data dictionary
        api_key: ElevenLabs API key
        
    Returns:
        Validated and normalized data
        
    Raises:
        ValueError: If validation fails
    """
    text = data.get('text', '').strip()
    
    if not text:
        raise ValueError('Text is required')
    
    validate_text_length(text)
    
    if not api_key:
        raise ValueError('ElevenLabs API key not configured')
    
    # Return normalized data
    return {
        'text': text,
        'voice_id': data.get('voice_id', '').strip(),
        'model_id': data.get('model_id', 'eleven_multilingual_v2'),
        'voice_settings': data.get('voice_settings', {})
    }


def validate_voice_settings(settings: Dict[str, Any]) -> Dict[str, float]:
    """
    Validate and normalize voice settings
    
    Args:
        settings: Voice settings dictionary
        
    Returns:
        Validated settings with defaults
    """
    return {
        'stability': float(settings.get('stability', 0.5)),
        'similarity_boost': float(settings.get('similarity_boost', 0.75)),
        'style': float(settings.get('style', 0.5)),
        'use_speaker_boost': bool(settings.get('use_speaker_boost', True))
    }
