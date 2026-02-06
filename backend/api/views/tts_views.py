"""
Text-to-Speech (TTS) Views

This module provides text-to-speech functionality using ElevenLabs API:
- generate_tts: Generate TTS audio with optimized voice settings (Turbo mode)
- generate_tts_preview: Generate TTS preview with custom voice parameters
- get_announcements: Retrieve standard announcement templates
- get_ai_announcements: Get AI-generated announcement variations

Used for creating custom game announcements, promotional messages, and jingles.
Supports voice customization (stability, similarity, style, speaker boost).
"""

import logging
import json
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..services.tts_service import TTSService
from ..validators import validate_tts_input
from ..utils.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, DATA_DIR, VENUE_NAME, OPENAI_API_KEY

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
    """Get AI-generated announcements (legacy - uses cached file)"""
    try:
        ai_path = DATA_DIR / 'announcements_ai.json'
        with open(ai_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
    except FileNotFoundError:
        return Response({'error': 'AI announcements not generated yet'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_session_announcements(request):
    """
    Get announcements for a specific session with the correct voice_id.
    This generates announcements dynamically based on session voice settings.
    
    Query params:
    - session_id: The session ID to get voice_id from
    - voice_id: Optional override voice_id
    """
    from ..models import BingoSession
    
    try:
        session_id = request.GET.get('session_id')
        voice_id_override = request.GET.get('voice_id')
        
        if not session_id:
            return Response({'error': 'session_id required'}, status=400)
        
        # Get session to find voice_id
        try:
            session = BingoSession.objects.get(session_id=session_id)
            voice_id = voice_id_override or session.voice_id
            
            if not voice_id:
                # Fallback to default voice if session doesn't have one
                voice_id = ELEVENLABS_VOICE_ID
                logger.warning(f"Session {session_id} has no voice_id, using default")
        except BingoSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        
        # For now, return the cached announcements with a note about the voice
        # In the future, this could generate announcements on-the-fly
        ai_path = DATA_DIR / 'announcements_ai.json'
        
        try:
            with open(ai_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add metadata about which voice should be used
            response_data = {
                **data,
                '_metadata': {
                    'session_id': session_id,
                    'voice_id': voice_id,
                    'note': 'Announcements loaded from cache. Voice setting noted for future TTS generation.'
                }
            }
            
            logger.info(f"📢 Loaded announcements for session {session_id} with voice_id {voice_id}")
            return Response(response_data)
            
        except FileNotFoundError:
            return Response({'error': 'AI announcements not generated yet'}, status=404)
    
    except Exception as e:
        logger.error(f"Error loading session announcements: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def generate_track_announcement(request):
    """
    Generate a unique AI-powered announcement for a track using OpenAI.
    
    POST body:
    {
        "title": "Song Title",
        "artist": "Artist Name",
        "release_year": 1985,
        "genre": "Rock"
    }
    
    Returns: { "announcement": "Generated interesting intro text" }
    """
    try:
        import openai
        
        # Validate required fields
        title = request.data.get('title')
        artist = request.data.get('artist')
        release_year = request.data.get('release_year')
        genre = request.data.get('genre', 'music')
        
        if not all([title, artist, release_year]):
            return Response({'error': 'title, artist, and release_year are required'}, status=400)
        
        if not OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured, using fallback")
            return Response({'error': 'OpenAI API not configured'}, status=503)
        
        # Configure OpenAI
        openai.api_key = OPENAI_API_KEY
        
        # Determine decade
        decade = f"{(release_year // 10) * 10}s"
        
        # Create prompt for OpenAI
        prompt = f"""Generate a SHORT, energetic, and interesting 1-sentence introduction for a music bingo game announcement. 

Song: "{title}" by {artist}
Year: {release_year} ({decade})
Genre: {genre}

Requirements:
- DO NOT mention the song title or artist name
- Keep it under 20 words
- Make it fun and engaging for a pub quiz atmosphere
- Include interesting context about the era, genre, or music style
- Vary the structure (don't always start with "Get ready for...")
- Examples of good styles:
  * "This {decade} {genre} anthem still gets crowds singing along"
  * "Straight from the {decade} dance floors to your cards"
  * "A chart-topping sensation that defined {decade} radio"
  * "Time for a legendary track that broke records in {release_year}"

Generate ONE announcement (just the text, no quotes or extra formatting):"""
        
        logger.info(f"🤖 Generating AI announcement for: {title} by {artist} ({release_year})")
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an energetic music bingo host creating short, engaging track introductions. Never mention song titles or artist names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,  # High creativity for variation
            max_tokens=50
        )
        
        announcement = response.choices[0].message.content.strip()
        
        # Remove any quotes if present
        announcement = announcement.strip('"').strip("'")
        
        logger.info(f"✅ Generated announcement: {announcement}")
        
        return Response({'announcement': announcement})
        
    except Exception as e:
        logger.error(f"Error generating track announcement: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
