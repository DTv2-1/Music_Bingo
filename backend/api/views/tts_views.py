"""
Text-to-Speech (TTS) Views
"""

import logging
import json
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..services.tts_service import TTSService
from ..validators import validate_tts_input
from ..utils.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, DATA_DIR, VENUE_NAME

logger = logging.getLogger(__name__)


@api_view(['POST'])
def generate_tts(request):
    """Proxy for ElevenLabs TTS"""
    try:
        # Validate input using validator
        try:
            validated_data = validate_tts_input(request.data, ELEVENLABS_API_KEY)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        
        text = validated_data['text']
        voice_id = validated_data['voice_id'] or ELEVENLABS_VOICE_ID
        
        # Use TTS service
        tts_service = TTSService()
        
        # Custom voice settings for turbo mode
        voice_settings = {
            'stability': 0.35,
            'similarity_boost': 0.85,
            'style': 0.5,
            'use_speaker_boost': True
        }
        
        audio_bytes = tts_service.generate_turbo(
            text=text,
            voice_id=voice_id,
            voice_settings=voice_settings
        )
        
        return HttpResponse(audio_bytes, content_type='audio/mpeg')
        
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating TTS: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def generate_tts_preview(request):
    """Generate TTS preview with custom voice settings"""
    try:
        text = request.data.get('text', '')
        voice_id = request.data.get('voice_id', ELEVENLABS_VOICE_ID)
        voice_settings = request.data.get('voice_settings', {})
        
        if not text:
            return Response({'error': 'No text provided'}, status=400)
        
        # Use provided settings or defaults
        settings_payload = {
            'stability': voice_settings.get('stability', 0.5),
            'similarity_boost': voice_settings.get('similarity_boost', 0.75),
            'style': voice_settings.get('style', 0.5),
            'use_speaker_boost': voice_settings.get('use_speaker_boost', True)
        }
        
        logger.info(f"Generating TTS preview: voice={voice_id}, settings={settings_payload}")
        
        # Use TTS service
        tts_service = TTSService()
        audio_bytes = tts_service.generate_preview(
            text=text,
            voice_id=voice_id,
            voice_settings=settings_payload
        )
        
        return HttpResponse(audio_bytes, content_type='audio/mpeg')
        
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating TTS preview: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_announcements(request):
    """Get announcements with venue name"""
    try:
        logger.info("get_announcements called")
        announcements_path = DATA_DIR / 'announcements.json'
        logger.info(f"Looking for announcements at: {announcements_path}, exists: {announcements_path.exists()}")
        with open(announcements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['venue_name'] = VENUE_NAME
        logger.info(f"Announcements loaded with venue: {VENUE_NAME}")
        return Response(data)
    except FileNotFoundError as e:
        logger.error(f"Announcements not found: {e}")
        return Response({'error': 'Announcements not found'}, status=404)
    except Exception as e:
        logger.error(f"Error loading announcements: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_ai_announcements(request):
    """Get AI-generated announcements"""
    try:
        ai_path = DATA_DIR / 'announcements_ai.json'
        with open(ai_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
    except FileNotFoundError:
        return Response({'error': 'AI announcements not generated yet'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
