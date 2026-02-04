"""
Session Input Validators
Validates bingo session inputs
"""

from typing import Dict, Any, List


def validate_session_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate session creation data
    
    Args:
        data: Session data dictionary
        
    Returns:
        Validated and normalized data
        
    Raises:
        ValueError: If validation fails
    """
    venue_name = data.get('venue_name', '').strip()
    
    # Validate num_players
    num_players = data.get('num_players', 25)
    try:
        num_players = int(num_players)
        if num_players < 1:
            raise ValueError('Number of players must be at least 1')
        if num_players > 500:
            raise ValueError('Number of players cannot exceed 500')
    except (ValueError, TypeError):
        raise ValueError('Number of players must be a valid integer')
    
    # Validate decades
    decades = data.get('decades', ['1960s', '1970s', '1980s', '1990s'])
    if not isinstance(decades, list):
        raise ValueError('Decades must be a list')
    
    valid_decades = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
    for decade in decades:
        if decade not in valid_decades:
            raise ValueError(f'Invalid decade: {decade}. Must be one of: {", ".join(valid_decades)}')
    
    # Validate genres (optional)
    genres = data.get('genres', [])
    if genres is None:
        genres = []
    if not isinstance(genres, list):
        raise ValueError('Genres must be a list')
    
    valid_genres = ['Rock', 'Pop', 'Dance', 'Hard Rock', 'R&B/Soul', 'Hip-Hop/Rap', 'Alternative', 'Country']
    for genre in genres:
        if genre not in valid_genres:
            raise ValueError(f'Invalid genre: {genre}. Must be one of: {", ".join(valid_genres)}')
    
    # Return normalized data
    return {
        'venue_name': venue_name or 'Music Bingo',
        'host_name': data.get('host_name', '').strip(),
        'num_players': num_players,
        'voice_id': data.get('voice_id', 'JBFqnCBsd6RMkjVDRZzb').strip(),
        'decades': decades,
        'genres': genres,
        'logo_url': data.get('logo_url', ''),
        'social_media': data.get('social_media', '').strip(),
        'include_qr': bool(data.get('include_qr', False)),
        'prizes': data.get('prizes', {})
    }


def validate_session_status(status: str) -> None:
    """
    Validate session status value
    
    Args:
        status: Status string to validate
        
    Raises:
        ValueError: If status is invalid
    """
    valid_statuses = ['pending', 'active', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')


def validate_card_generation_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate card generation parameters
    
    Args:
        data: Card generation data dictionary
        
    Returns:
        Validated and normalized data
        
    Raises:
        ValueError: If validation fails
    """
    venue_name = data.get('venue_name', 'Music Bingo')
    
    # Validate num_players
    num_players = data.get('num_players', 25)
    try:
        num_players = int(num_players)
        if num_players < 1:
            raise ValueError('Number of players must be at least 1')
        if num_players > 500:
            raise ValueError('Number of players cannot exceed 500')
    except (ValueError, TypeError):
        raise ValueError('Number of players must be a valid integer')
    
    # Validate game_number
    game_number = data.get('game_number', 1)
    try:
        game_number = int(game_number)
        if game_number < 1:
            raise ValueError('Game number must be at least 1')
    except (ValueError, TypeError):
        raise ValueError('Game number must be a valid integer')
    
    return {
        'venue_name': venue_name,
        'num_players': num_players,
        'game_number': game_number,
        'game_date': data.get('game_date'),
        'pub_logo': data.get('pub_logo'),
        'decades': data.get('decades', []),
        'genres': data.get('genres', []),
        'social_media': data.get('social_media'),
        'include_qr': bool(data.get('include_qr', False)),
        'prize_4corners': data.get('prize_4corners', ''),
        'prize_first_line': data.get('prize_first_line', ''),
        'prize_full_house': data.get('prize_full_house', '')
    }
