"""
Music Bingo API Views - Django REST Framework
Migrated from Flask to Django
"""

import os
import json
import logging
import threading
import uuid
import time
import subprocess
import io
from pathlib import Path
from datetime import datetime

from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from google.cloud import storage
from datetime import timedelta

# Import TaskStatus model
from .models import TaskStatus

# Import centralized configuration
from .utils.config import (
    AppConfig,
    BASE_DIR,
    DATA_DIR,
    FRONTEND_DIR,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    GCS_BUCKET_NAME,
    VENUE_NAME
)

# Import services
from .services import (
    upload_to_gcs, 
    GCSStorageService, 
    TTSService, 
    MusicGenerationService,
    JingleService,
    ScheduleService,
    BingoSessionService,
    CardGenerationService
)

# Import async tasks
from .tasks import run_card_generation_task, run_jingle_generation_task

# Import validators
from .validators import (
    validate_jingle_input,
    validate_tts_input,
    validate_card_generation_params,
    validate_session_status
)

logger = logging.getLogger(__name__)

@api_view(['GET'])
def health_check(request):
    logger.info("Health check endpoint called")
    return Response({'status': 'healthy', 'message': 'Music Bingo API (Django)'})

@api_view(['GET'])
def get_pool(request):
    try:
        logger.info(f"get_pool called - DATA_DIR: {DATA_DIR}")
        pool_path = DATA_DIR / 'pool.json'
        logger.info(f"Looking for pool at: {pool_path}, exists: {pool_path.exists()}")
        with open(pool_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Pool loaded successfully: {len(data.get('songs', []))} songs")
        return Response(data)
    except FileNotFoundError as e:
        logger.error(f"Pool file not found: {e}")
        return Response({'error': 'Pool file not found'}, status=404)
    except Exception as e:
        logger.error(f"Error loading pool: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def generate_cards_async(request):
    """Generate cards asynchronously (Django)"""
    try:
        data = request.data
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        pub_logo = data.get('pub_logo')
        social_media = data.get('social_media')
        include_qr = data.get('include_qr', False)
        game_number = data.get('game_number', 1)
        game_date = data.get('game_date')
        
        # Get prizes
        prize_4corners = data.get('prize_4corners', '')
        prize_first_line = data.get('prize_first_line', '')
        prize_full_house = data.get('prize_full_house', '')
        
        logger.info(f"Starting async card generation: {num_players} cards for '{venue_name}'")
        logger.info(f"  pub_logo: {pub_logo[:100] if pub_logo else 'None'}...")  # Truncate for readability
        logger.info(f"  pub_logo type: {type(pub_logo)}, length: {len(pub_logo) if pub_logo else 0}")
        logger.info(f"  social_media: {social_media}, include_qr: {include_qr}")
        logger.info(f"  prizes: {prize_4corners}, {prize_first_line}, {prize_full_house}")
        
        task_id = str(uuid.uuid4())
        
        # Create task in database
        task = TaskStatus.objects.create(
            task_id=task_id,
            task_type='card_generation',
            status='pending',
            progress=0,
            metadata={
                'venue_name': venue_name,
                'num_players': num_players,
                'game_number': game_number
            }
        )
        
        # Use CardGenerationService to prepare command
        card_service = CardGenerationService()
        cmd = card_service.prepare_generation_command(
            venue_name=venue_name,
            num_players=num_players,
            game_number=game_number,
            game_date=game_date,
            pub_logo=pub_logo,
            social_media=social_media,
            include_qr=include_qr,
            prize_4corners=prize_4corners,
            prize_first_line=prize_first_line,
            prize_full_house=prize_full_house
        )
        
        # Run task in background using task module
        run_card_generation_task(task_id, task, cmd, BASE_DIR)
        
        return Response({'task_id': task_id, 'status': 'pending'}, status=202)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_task_status(request, task_id):
    try:
        task = TaskStatus.objects.get(task_id=task_id)
    except TaskStatus.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)
    
    # Calculate elapsed time
    if task.completed_at:
        elapsed_seconds = (task.completed_at - task.started_at).total_seconds()
    else:
        elapsed_seconds = (timezone.now() - task.started_at).total_seconds()
    
    response = {
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'elapsed_time': round(elapsed_seconds, 2)
    }
    
    if task.current_step:
        response['current_step'] = task.current_step
    
    if task.status == 'completed' and task.result:
        response['result'] = task.result
    elif task.status == 'failed' and task.error:
        response['error'] = task.error
    
    return Response(response)

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

@api_view(['POST'])
@csrf_exempt
def upload_logo(request):
    """Upload pub logo"""
    try:
        logger.info(f"upload_logo called - FILES: {list(request.FILES.keys())}")
        logger.info(f"upload_logo - DATA_DIR: {DATA_DIR}")
        
        if 'logo' not in request.FILES:
            logger.warning("No 'logo' file in request.FILES")
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['logo']
        logger.info(f"File received: name={file.name}, size={file.size}")
        
        if not file.name:
            return Response({'error': 'No file selected'}, status=400)
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'}
        file_ext = file.name.rsplit('.', 1)[1].lower() if '.' in file.name else ''
        
        if file_ext not in allowed_extensions:
            return Response({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}, status=400)
        
        logos_dir = DATA_DIR / 'logos'
        logger.info(f"Creating logos dir: {logos_dir}")
        logos_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        safe_filename = f'pub_logo_{timestamp}.{file_ext}'
        file_path = logos_dir / safe_filename
        
        logger.info(f"Saving file to: {file_path}")
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        logo_url = f'/data/logos/{safe_filename}'
        logger.info(f"File saved successfully: {file_path}, URL: {logo_url}")
        
        return Response({
            'success': True,
            'url': logo_url,
            'filename': safe_filename
        })
        
    except Exception as e:
        logger.error(f"Error uploading logo: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_config(request):
    """Get public configuration"""
    return Response({'venue_name': VENUE_NAME})


# ============================================================================
# JINGLE GENERATION ENDPOINTS
# ============================================================================

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


# ============================================================================
# JINGLE SCHEDULE MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST', 'GET'])
def create_jingle_schedule(request):
    """
    Create a new jingle schedule or list all schedules
    POST /api/jingle-schedules - Create new schedule
    GET /api/jingle-schedules - List all schedules
    
    POST Body: {
        "jingle_name": "Tuesday Night Taco Promotion",
        "jingle_filename": "jingle_67890.mp3",
        "start_date": "2026-01-14",
        "end_date": "2026-03-31",
        "time_start": "17:00",
        "time_end": "22:00",
        "days_of_week": {
            "monday": false,
            "tuesday": true,
            ...
        },
        "repeat_pattern": "regular",
        "enabled": true,
        "priority": 10
    }
    
    Returns: {
        "success": true,
        "schedule_id": 1,
        "message": "Schedule created successfully"
    }
    """
    logger.info(f'\n{"="*60}')
    logger.info(f'{request.method} /api/jingle-schedules endpoint called')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request content-type: {request.content_type}')
    if request.method == 'GET':
        # List all schedules
        try:
            # Get venue_name from query params
            venue_name = request.GET.get('venue_name')
            session_id = request.GET.get('session_id')
            
            # Use ScheduleService to get schedules
            schedule_service = ScheduleService()
            schedules_list = schedule_service.get_schedules(
                venue_name=venue_name,
                session_id=session_id
            )
            
            logger.info(f'✅ Listed {len(schedules_list)} jingle schedules')
            for schedule in schedules_list:
                logger.info(f"  - {schedule['jingle_name']} (enabled: {schedule['enabled']}, priority: {schedule['priority']})")
            
            return Response({
                'schedules': schedules_list
            })
            
        except Exception as e:
            logger.error(f"Error listing jingle schedules: {e}", exc_info=True)
            return Response({
                'error': str(e)
            }, status=500)
    
    # POST: Create new schedule
    try:
        data = request.data
        
        # Use ScheduleService to create schedule
        schedule_service = ScheduleService()
        result = schedule_service.create_schedule(data)
        
        logger.info(f"Created jingle schedule #{result['schedule_id']}: {data.get('jingle_name')}")
        
        return Response(result, status=201)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['GET'])
def get_active_jingles(request):
    """
    Get all currently active jingle schedules
    GET /api/jingle-schedules/active
    
    Evaluates each schedule based on:
    - enabled flag
    - current date within date range
    - current time within time range (if specified)
    - current day of week matches selected days
    
    Returns schedules sorted by priority (highest first)
    
    Returns: {
        "active_jingles": [
            {
                "id": 1,
                "jingle_name": "Tuesday Night Taco Promotion",
                "jingle_filename": "jingle_67890.mp3",
                "interval": 6,
                "priority": 10
            }
        ]
    }
    """
    logger.info(f'\n{"="*60}')
    logger.info('📥 GET /api/jingle-schedules/active - Get active jingles endpoint called')
    logger.info(f'Request method: {request.method}')
    logger.info(f'Request path: {request.path}')
    try:
        # Get venue_name from query params
        venue_name = request.GET.get('venue_name')
        session_id = request.GET.get('session_id')
        
        # Use ScheduleService to get active schedules
        schedule_service = ScheduleService()
        active_schedules = schedule_service.get_active_schedules(
            venue_name=venue_name,
            session_id=session_id
        )
        
        logger.info(f'✅ Found {len(active_schedules)} active jingle schedules')
        for schedule in active_schedules:
            logger.info(f"  - {schedule['jingle_name']} (interval: {schedule['interval']}, priority: {schedule['priority']})")
        
        return Response({
            'active_jingles': active_schedules
        })
        
    except Exception as e:
        logger.error(f"Error getting active jingles: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['PUT'])
def update_jingle_schedule(request, schedule_id):
    """
    Update an existing jingle schedule
    PUT /api/jingle-schedules/<schedule_id>
    
    Body: {
        "enabled": false,
        "priority": 5,
        "end_date": "2026-06-30",
        ... (any fields to update)
    }
    
    Returns: {
        "success": true,
        "message": "Schedule updated successfully"
    }
    """
    try:
        from .models import JingleSchedule
        from datetime import datetime
        
        # Get schedule by ID
        try:
            schedule = JingleSchedule.objects.get(id=schedule_id)
        except JingleSchedule.DoesNotExist:
            return Response({
                'error': f'Schedule with id {schedule_id} not found'
            }, status=404)
        
        data = request.data
        
        # Update fields if provided
        if 'jingle_name' in data:
            schedule.jingle_name = data['jingle_name'].strip()
        
        if 'jingle_filename' in data:
            jingle_filename = data['jingle_filename'].strip()
            # Optionally verify file exists
            jingles_dir = DATA_DIR / 'jingles'
            jingle_path = jingles_dir / jingle_filename
            if not jingle_path.exists():
                logger.warning(f'Jingle file not found at {jingle_path}, but continuing anyway')
            schedule.jingle_filename = jingle_filename
        
        if 'start_date' in data:
            try:
                schedule.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }, status=400)
        
        if 'end_date' in data:
            if data['end_date']:
                try:
                    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                    if end_date < schedule.start_date:
                        return Response({
                            'error': 'End date must be after start date'
                        }, status=400)
                    schedule.end_date = end_date
                except ValueError:
                    return Response({
                        'error': 'Invalid end_date format. Use YYYY-MM-DD'
                    }, status=400)
            else:
                schedule.end_date = None
        
        if 'time_start' in data:
            if data['time_start']:
                try:
                    schedule.time_start = datetime.strptime(data['time_start'], '%H:%M').time()
                except ValueError:
                    return Response({
                        'error': 'Invalid time_start format. Use HH:MM'
                    }, status=400)
            else:
                schedule.time_start = None
        
        if 'time_end' in data:
            if data['time_end']:
                try:
                    schedule.time_end = datetime.strptime(data['time_end'], '%H:%M').time()
                except ValueError:
                    return Response({
                        'error': 'Invalid time_end format. Use HH:MM'
                    }, status=400)
            else:
                schedule.time_end = None
        
        # Validate time_end is after time_start
        if schedule.time_start and schedule.time_end and schedule.time_end <= schedule.time_start:
            return Response({
                'error': 'End time must be after start time'
            }, status=400)
        
        if 'days_of_week' in data:
            days = data['days_of_week']
            schedule.monday = days.get('monday', schedule.monday)
            schedule.tuesday = days.get('tuesday', schedule.tuesday)
            schedule.wednesday = days.get('wednesday', schedule.wednesday)
            schedule.thursday = days.get('thursday', schedule.thursday)
            schedule.friday = days.get('friday', schedule.friday)
            schedule.saturday = days.get('saturday', schedule.saturday)
            schedule.sunday = days.get('sunday', schedule.sunday)
            
            # Validate at least one day selected
            if not any([schedule.monday, schedule.tuesday, schedule.wednesday, 
                       schedule.thursday, schedule.friday, schedule.saturday, schedule.sunday]):
                return Response({
                    'error': 'At least one day of the week must be selected'
                }, status=400)
        
        if 'repeat_pattern' in data:
            pattern = data['repeat_pattern']
            if pattern not in ['occasional', 'regular', 'often']:
                return Response({
                    'error': 'Invalid repeat_pattern. Must be: occasional, regular, or often'
                }, status=400)
            schedule.repeat_pattern = pattern
        
        if 'enabled' in data:
            schedule.enabled = bool(data['enabled'])
        
        if 'priority' in data:
            priority = int(data['priority'])
            if priority < 0 or priority > 100:
                return Response({
                    'error': 'Priority must be between 0 and 100'
                }, status=400)
            schedule.priority = priority
        
        # Save changes
        schedule.save()
        
        logger.info(f"Updated jingle schedule #{schedule.id}: {schedule.jingle_name}")
        
        return Response({
            'success': True,
            'message': 'Schedule updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


@api_view(['DELETE'])
def delete_jingle_schedule(request, schedule_id):
    """
    Delete a jingle schedule
    DELETE /api/jingle-schedules/<schedule_id>
    
    Returns: {
        "success": true,
        "message": "Schedule deleted successfully"
    }
    """
    try:
        # Use ScheduleService to delete schedule
        schedule_service = ScheduleService()
        result = schedule_service.delete_schedule(schedule_id)
        
        logger.info(f"Deleted jingle schedule #{schedule_id}")
        
        return Response(result)
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting jingle schedule: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=500)


# ============================================================================
# VENUE CONFIGURATION ENDPOINTS
# ============================================================================

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
    from .models import VenueConfiguration
    
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


# ============================================================================
# BINGO SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST', 'GET'])
def bingo_sessions(request):
    """
    Create or list bingo sessions
    POST: Create new session
    GET: List all sessions (with optional venue filter)
    """
    from .models import BingoSession
    
    if request.method == 'POST':
        try:
            # Use BingoSessionService to create session
            session_service = BingoSessionService()
            result = session_service.create_session(request.data)
            
            logger.info(f"✅ Created bingo session: {result['session_id']} for {request.data.get('venue_name', '')}")
            
            return Response(result, status=201)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error creating bingo session: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    else:  # GET
        try:
            venue_name = request.GET.get('venue')
            
            # Use BingoSessionService to get sessions
            session_service = BingoSessionService()
            sessions_data = session_service.get_sessions_by_venue(venue_name) if venue_name else session_service.get_recent_sessions(limit=50)
            
            return Response({
                'sessions': sessions_data,
                'total': len(sessions_data)
            })
            
        except Exception as e:
            logger.error(f"Error listing bingo sessions: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)


@api_view(['GET', 'PUT', 'DELETE'])
def bingo_session_detail(request, session_id):
    """
    Get, update, or delete a specific bingo session
    """
    from .models import BingoSession
    
    try:
        session = BingoSession.objects.get(session_id=session_id)
    except BingoSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
    
    if request.method == 'GET':
        try:
            # Use BingoSessionService to get session details
            session_service = BingoSessionService()
            session_data = session_service.get_session_summary(session_id)
            
            logger.info(f"📖 Fetching bingo session {session_id}")
            
            return Response(session_data)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=404)
    
    elif request.method == 'PUT':
        try:
            data = request.data
            
            # Update allowed fields
            if 'songs_played' in data:
                session.songs_played = data['songs_played']
            if 'current_song_index' in data:
                session.current_song_index = data['current_song_index']
            if 'status' in data:
                session.status = data['status']
                if data['status'] == 'active' and not session.started_at:
                    session.started_at = datetime.now()
                elif data['status'] == 'completed' and not session.completed_at:
                    session.completed_at = datetime.now()
            
            session.save()
            
            return Response({
                'success': True,
                'message': 'Session updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating bingo session: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            session.delete()
            return Response({
                'success': True,
                'message': 'Session deleted successfully'
            })
        except Exception as e:
            logger.error(f"Error deleting bingo session: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)


@api_view(['PATCH'])
def update_bingo_session_status(request, session_id):
    """Update bingo session status (pending -> active -> completed)"""
    try:
        new_status = request.data.get('status')
        if not new_status:
            return Response({'error': 'Status is required'}, status=400)
        
        # Validate status using validator
        try:
            validate_session_status(new_status)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        
        # Use BingoSessionService to update status
        session_service = BingoSessionService()
        result = session_service.update_session_status(session_id, new_status)
        
        logger.info(f"Updated bingo session {session_id} status to: {new_status}")
        
        return Response(result)
        
    except ValueError as e:
        return Response({'error': str(e)}, status=400 if 'not found' not in str(e).lower() else 404)
    except Exception as e:
        logger.error(f"Error updating session status: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


