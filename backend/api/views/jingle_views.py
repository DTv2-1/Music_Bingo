"""
Jingle Management Views

This module manages promotional jingles combining TTS + AI-generated music:
- generate_jingle: Create jingle with custom text and music (async task)
- get_jingle_status: Check jingle generation progress and status
- download_jingle: Download generated jingle files
- generate_music_preview: Generate short music previews (5s) for testing
- list_jingles: List all generated jingles with metadata
- manage_playlist: Get/update jingle playlist configuration

Jingle generation workflow:
1. Generate TTS voice announcement
2. Generate AI background music
3. Mix audio tracks (voice + music)
4. Upload to Google Cloud Storage
5. Return download URL

Supports ElevenLabs TTS and Music Generation APIs.
"""

import logging
import uuid
from django.http import HttpResponse, FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import TaskStatus
from ..services.jingle_service import JingleService
from ..services.music_service import MusicGenerationService
from ..validators import validate_jingle_input
from ..tasks import run_jingle_generation_task
from ..utils.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, DATA_DIR

logger = logging.getLogger(__name__)


@api_view(['POST'])
def generate_jingle(request):
    """
    Generate a jingle with TTS + AI music
    POST /api/generate-jingle
    Body: {
        "text": "Happy Hour 2x1 cocktails 5-7pm",
        "voice_id": "optional",
        "music_prompt": "upbeat pub guitar riff",
        "duration": 10
    }
    Returns: {task_id: "uuid"}
    """
    try:
        data = request.data
        
        # Validate input using validator
        try:
            validated_data = validate_jingle_input(data, ELEVENLABS_API_KEY)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        
        text = validated_data['text']
        voice_id = validated_data['voice_id'] or ELEVENLABS_VOICE_ID
        music_prompt = validated_data['music_prompt']
        voice_settings_payload = validated_data['voice_settings']
        
        logger.info(f"Generating jingle for text: '{text[:50]}...'")
        logger.info(f"Starting jingle generation: text='{text}', music_prompt='{music_prompt}', voice_settings={voice_settings_payload}")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status in database
        task = TaskStatus.objects.create(
            task_id=task_id,
            task_type='jingle_generation',
            status='pending',
            progress=0,
            current_step='initializing',
            metadata={
                'text': text,
                'voice_id': voice_id,
                'music_prompt': music_prompt,
                'voice_settings': voice_settings_payload
            }
        )
        
        # Run task in background using task module
        jingle_service = JingleService()
        run_jingle_generation_task(
            task_id=task_id,
            task_model=task,
            jingle_service=jingle_service,
            text=text,
            voice_id=voice_id,
            music_prompt=music_prompt,
            voice_settings=voice_settings_payload
        )
        
        return Response({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Jingle generation started'
        }, status=202)
        
    except Exception as e:
        logger.error(f"Error starting jingle generation: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_jingle_status(request, task_id):
    """
    Get jingle generation task status
    GET /api/jingle-tasks/<task_id>
    """
    try:
        task = TaskStatus.objects.get(task_id=task_id)
        
        # Calculate elapsed time
        if task.completed_at:
            elapsed_seconds = (task.completed_at - task.started_at).total_seconds()
        else:
            elapsed_seconds = (timezone.now() - task.started_at).total_seconds()
        
        response = {
            'task_id': task.task_id,
            'status': task.status,
            'progress': task.progress,
            'current_step': task.current_step,
            'elapsed_time': round(elapsed_seconds, 2)
        }
        
        if task.result:
            response['result'] = task.result
        if task.error:
            response['error'] = task.error
        
        return Response(response)
        
    except TaskStatus.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def download_jingle(request, filename):
    """
    Download generated jingle
    GET /api/jingles/<filename>
    """
    try:
        jingles_dir = DATA_DIR / 'jingles'
        file_path = jingles_dir / filename
        
        if not file_path.exists():
            raise Http404('Jingle not found')
        
        # Security check: prevent directory traversal
        if not str(file_path.resolve()).startswith(str(jingles_dir.resolve())):
            raise Http404('Invalid file path')
        
        logger.info(f"Serving jingle: {file_path}")
        
        response = FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Error serving jingle: {e}", exc_info=True)
        raise Http404('Error serving file')


@api_view(['POST'])
def generate_music_preview(request):
    """
    Generate a short music preview (5 seconds)
    POST /api/generate-music-preview
    Body: {
        "music_prompt": "upbeat pub guitar music",
        "duration": 5
    }
    """
    try:
        data = request.data
        music_prompt = data.get('music_prompt', 'upbeat background music')
        duration = int(data.get('duration', 5))
        
        logger.info(f"Generating music preview: '{music_prompt}', {duration}s")
        
        # Use Music Generation service
        music_service = MusicGenerationService()
        music_bytes = music_service.generate_preview(
            prompt=music_prompt,
            duration=duration
        )
        
        logger.info(f"Music preview generated: {len(music_bytes)} bytes")
        
        # Return audio directly
        return HttpResponse(music_bytes, content_type='audio/mpeg')
        
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating music preview: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def list_jingles(request):
    """
    List all generated jingles
    GET /api/jingles
    Returns: [{"filename": "...", "created": "...", "size": 12345, "metadata": {...}}, ...]
    """
    try:
        logger.info(f'\n{"="*60}')
        logger.info('📥 GET /api/jingles - List jingles endpoint called')
        logger.info(f'Request method: {request.method}')
        logger.info(f'Request path: {request.path}')
        
        # Use JingleService to list jingles
        jingle_service = JingleService()
        jingles = jingle_service.list_jingles()
        
        logger.info(f'✅ Found {len(jingles)} jingles')
        for jingle in jingles:
            logger.info(f"  - {jingle['filename']}")
        
        response = Response({'jingles': jingles})
        logger.info(f'Returning jingles response: {response.status_code}')
        return response
        
    except Exception as e:
        logger.error(f"Error listing jingles: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET', 'POST'])
def manage_playlist(request):
    """
    Get or update jingle playlist
    GET /api/playlist - Returns current playlist
    POST /api/playlist - Update playlist
    Body: {
        "jingles": ["file1.mp3", "file2.mp3"],
        "enabled": true,
        "interval": 3  // Play jingle every X rounds
    }
    """
    playlist_file = DATA_DIR / 'jingle_playlist.json'
    
    if request.method == 'GET':
        try:
            # Use JingleService to get playlist
            jingle_service = JingleService()
            playlist = jingle_service.get_playlist()
            return Response(playlist)
            
        except Exception as e:
            logger.error(f"Error loading playlist: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = request.data
            
            # Use JingleService to save playlist
            jingle_service = JingleService()
            result = jingle_service.save_playlist(
                jingles=data.get('jingles', []),
                enabled=data.get('enabled', False),
                interval=data.get('interval', 3)
            )
            
            return Response(result)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error saving playlist: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
