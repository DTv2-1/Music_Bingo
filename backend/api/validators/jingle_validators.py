"""
Jingle Input Validators
Validates jingle generation inputs
"""

from typing import Dict, Any


def validate_jingle_input(
    data: Dict[str, Any],
    api_key: str,
    max_text_length: int = 1000
) -> Dict[str, Any]:
    """
    Validate jingle generation input
    
    Args:
        data: Request data dictionary
        api_key: ElevenLabs API key
        max_text_length: Maximum text length
        
    Returns:
        Validated and normalized data
        
    Raises:
        ValueError: If validation fails
    """
    text = data.get('text', '').strip()
    
    # Validate text
    if not text:
        raise ValueError('Text is required')
    
    if len(text) > max_text_length:
        raise ValueError(f'Text too long (max {max_text_length} characters / ~{max_text_length // 5} words)')
    
    # Validate API key
    if not api_key:
        raise ValueError('ElevenLabs API key not configured')
    
    # Get voice settings with defaults
    voice_settings = data.get('voiceSettings', {})
    voice_settings_payload = {
        'stability': voice_settings.get('stability', 0.5),
        'similarity_boost': voice_settings.get('similarity_boost', 0.75),
        'style': voice_settings.get('style', 0.5),
        'use_speaker_boost': voice_settings.get('use_speaker_boost', True)
    }
    
    # Return normalized data
    return {
        'text': text,
        'voice_id': data.get('voice_id', '').strip(),
        'music_prompt': data.get('music_prompt', 'upbeat energetic pub background music').strip(),
        'voice_settings': voice_settings_payload
    }


def validate_playlist_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate jingle playlist data
    
    Args:
        data: Playlist data dictionary
        
    Returns:
        Validated playlist data
        
    Raises:
        ValueError: If validation fails
    """
    jingles = data.get('jingles', [])
    
    if not isinstance(jingles, list):
        raise ValueError('Jingles must be a list')
    
    interval = data.get('interval', 3)
    try:
        interval = int(interval)
        if interval < 1:
            raise ValueError('Interval must be at least 1')
    except (ValueError, TypeError):
        raise ValueError('Interval must be a valid integer')
    
    return {
        'jingles': jingles,
        'enabled': bool(data.get('enabled', False)),
        'interval': interval
    }
