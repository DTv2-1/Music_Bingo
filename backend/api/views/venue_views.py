"""
Venue Configuration Views

This module manages venue-specific configuration settings:
- venue_config: Get/save venue configuration (GET/POST)

Configuration Options:
- num_players: Default number of players for sessions
- voice_id: ElevenLabs voice ID for announcements
- selected_decades: Music era preferences (60s, 70s, 80s, 90s)
- pub_logo: Venue logo URL for branding
- social_platform: Social media platform (Instagram, Facebook, etc.)
- social_username: Social media handle
- include_qr: Enable QR codes on cards
- prize_4corners: 4-corners prize description
- prize_first_line: First line prize description
- prize_full_house: Full house prize description

Each venue can have unique settings for personalized gaming experience.
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def venue_config(request, venue_name):
    """
    Get or save venue-specific configuration
    GET /api/venue-config/<venue_name> - Get configuration
    POST /api/venue-config/<venue_name> - Save/update configuration
    
    POST Body: {
        "num_players": 25,
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "selected_decades": ["60s", "70s", "80s", "90s"],
        "pub_logo": "https://example.com/logo.png",
        "social_platform": "instagram",
        "social_username": "mypub",
        "include_qr": true,
        "prize_4corners": "£10 voucher",
        "prize_first_line": "£15 voucher",
        "prize_full_house": "£50 cash prize"
    }
    """
    from ..models import VenueConfiguration
    
    if request.method == 'GET':
        try:
            config = VenueConfiguration.objects.get(venue_name=venue_name)
            return Response({
                'success': True,
                'config': {
                    'venue_name': config.venue_name,
                    'num_players': config.num_players,
                    'voice_id': config.voice_id,
                    'selected_decades': config.selected_decades,
                    'pub_logo': config.pub_logo,
                    'social_platform': config.social_platform,
                    'social_username': config.social_username,
                    'include_qr': config.include_qr,
                    'prize_4corners': config.prize_4corners,
                    'prize_first_line': config.prize_first_line,
                    'prize_full_house': config.prize_full_house,
                    'updated_at': config.updated_at.isoformat()
                }
            })
        except VenueConfiguration.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Configuration not found for this venue'
            }, status=404)
        except Exception as e:
            logger.error(f"Error fetching venue config: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = request.data
            
            # Update or create configuration
            config, created = VenueConfiguration.objects.update_or_create(
                venue_name=venue_name,
                defaults={
                    'num_players': data.get('num_players', 25),
                    'voice_id': data.get('voice_id', 'JBFqnCBsd6RMkjVDRZzb'),
                    'selected_decades': data.get('selected_decades', ['60s', '70s', '80s', '90s']),
                    'pub_logo': data.get('pub_logo', ''),
                    'social_platform': data.get('social_platform', 'instagram'),
                    'social_username': data.get('social_username', ''),
                    'include_qr': data.get('include_qr', False),
                    'prize_4corners': data.get('prize_4corners', ''),
                    'prize_first_line': data.get('prize_first_line', ''),
                    'prize_full_house': data.get('prize_full_house', '')
                }
            )
            
            action = 'created' if created else 'updated'
            logger.info(f"Venue configuration {action} for: {venue_name}")
            
            return Response({
                'success': True,
                'message': f'Configuration {action} successfully',
                'config': {
                    'venue_name': config.venue_name,
                    'num_players': config.num_players,
                    'voice_id': config.voice_id,
                    'selected_decades': config.selected_decades,
                    'pub_logo': config.pub_logo,
                    'social_platform': config.social_platform,
                    'social_username': config.social_username,
                    'include_qr': config.include_qr,
                    'prize_4corners': config.prize_4corners,
                    'prize_first_line': config.prize_first_line,
                    'prize_full_house': config.prize_full_house
                }
            })
            
        except Exception as e:
            logger.error(f"Error saving venue config: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
