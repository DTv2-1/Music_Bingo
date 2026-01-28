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

# Import TaskStatus model
from .models import TaskStatus

logger = logging.getLogger(__name__)

# Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')

# Paths - Fix for Docker container structure
# Docker WORKDIR is /app, files are copied as: COPY backend/ . COPY data/ ./data/
# So from /app/api/views.py we need to go to /app/data/
BASE_DIR = Path(__file__).resolve().parent.parent  # /app/api -> /app
DATA_DIR = BASE_DIR / 'data'  # /app/data
FRONTEND_DIR = BASE_DIR / 'frontend'  # /app/frontend

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
        logger.info(f"  pub_logo: {pub_logo}, social_media: {social_media}, include_qr: {include_qr}")
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
        
        def background_task():
            try:
                logger.info(f"Task {task_id}: Processing started")
                task.status = 'processing'
                task.save(update_fields=['status'])
                
                script_path = BASE_DIR / 'generate_cards.py'
                cmd = [
                    'python3', str(script_path),
                    '--venue_name', venue_name,
                    '--num_players', str(num_players),
                    '--game_number', str(game_number)
                ]
                
                if game_date:
                    cmd.extend(['--game_date', game_date])
                
                if pub_logo:
                    # Convert relative URL to absolute path
                    if pub_logo.startswith('/data/'):
                        logo_path = str(BASE_DIR / pub_logo[1:])  # Remove leading /
                        cmd.extend(['--pub_logo', logo_path])
                        logger.info(f"Task {task_id}: Using pub logo: {logo_path}")
                    elif pub_logo.startswith('http'):
                        cmd.extend(['--pub_logo', pub_logo])
                        logger.info(f"Task {task_id}: Using pub logo URL: {pub_logo}")
                
                if social_media:
                    cmd.extend(['--social_media', social_media])
                    logger.info(f"Task {task_id}: Adding social media QR: {social_media}")
                
                if include_qr:
                    cmd.extend(['--include_qr', 'true'])
                    logger.info(f"Task {task_id}: QR code enabled")
                
                # Add prizes if provided
                if prize_4corners:
                    cmd.extend(['--prize_4corners', prize_4corners])
                if prize_first_line:
                    cmd.extend(['--prize_first_line', prize_first_line])
                if prize_full_house:
                    cmd.extend(['--prize_full_house', prize_full_house])
                
                logger.info(f"Task {task_id}: Running command: {' '.join(cmd)}")
                
                # Run with real-time output capture for progress tracking
                process = subprocess.Popen(
                    cmd,
                    cwd=str(BASE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                stdout_lines = []
                stderr_lines = []
                
                # Read output line by line for progress tracking
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        stdout_lines.append(line)
                        logger.info(f"Task {task_id}: {line}")
                        
                        # Parse structured progress from output (PROGRESS: XX)
                        if line.startswith('PROGRESS:'):
                            try:
                                progress_str = line.split('PROGRESS:')[1].strip()
                                progress_val = int(float(progress_str))
                                task.progress = progress_val
                                task.save(update_fields=['progress'])
                                logger.info(f"Task {task_id}: Progress updated to {progress_val}%")
                            except Exception as e:
                                logger.warning(f"Task {task_id}: Failed to parse progress: {e}")
                        # Also parse emoji format for backwards compatibility
                        elif '📊 Progress:' in line:
                            try:
                                progress_str = line.split('Progress:')[1].split('%')[0].strip()
                                task.progress = int(float(progress_str))
                                task.save(update_fields=['progress'])
                            except:
                                pass
                
                # Get any remaining stderr
                stderr_output = process.stderr.read()
                if stderr_output:
                    stderr_lines.append(stderr_output)
                
                return_code = process.poll()
                
                # Create result object similar to subprocess.run
                class Result:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                
                result = Result(return_code, '\n'.join(stdout_lines), '\n'.join(stderr_lines))
                
                if result.returncode != 0:
                    logger.error(f"Task {task_id}: Failed with error: {result.stderr}")
                    task.status = 'failed'
                    task.error = result.stderr
                    task.completed_at = timezone.now()
                    task.save(update_fields=['status', 'error', 'completed_at'])
                    return
                
                logger.info(f"Task {task_id}: Completed successfully")
                task.status = 'completed'
                task.progress = 100
                task.result = {
                    'success': True,
                    'download_url': '/data/cards/music_bingo_cards.pdf'
                }
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'progress', 'result', 'completed_at'])
            except Exception as e:
                logger.error(f"Task {task_id}: Exception: {str(e)}")
                task.status = 'failed'
                task.error = str(e)
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'error', 'completed_at'])
        
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        
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
    if not ELEVENLABS_API_KEY:
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)
    
    try:
        text = request.data.get('text', '')
        voice_id = request.data.get('voice_id', ELEVENLABS_VOICE_ID)
        
        if not text:
            return Response({'error': 'No text provided'}, status=400)
        
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        
        response = requests.post(
            url,
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.35,
                    'similarity_boost': 0.85,
                    'style': 0.5,
                    'use_speaker_boost': True
                },
                'optimize_streaming_latency': 1,
                'output_format': 'mp3_44100_128'
            }
        )
        
        if not response.ok:
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
        
        return HttpResponse(response.content, content_type='audio/mpeg')
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def generate_tts_preview(request):
    """Generate TTS preview with custom voice settings"""
    if not ELEVENLABS_API_KEY:
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)
    
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
        
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        
        response = requests.post(
            url,
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_multilingual_v2',
                'voice_settings': settings_payload,
                'optimize_streaming_latency': 1,
                'output_format': 'mp3_44100_128'
            },
            timeout=30
        )
        
        if not response.ok:
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
        
        return HttpResponse(response.content, content_type='audio/mpeg')
        
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
        from .audio_mixer import mix_tts_with_music
        
        data = request.data
        text = data.get('text', '').strip()
        voice_id = data.get('voice_id', ELEVENLABS_VOICE_ID)
        music_prompt = data.get('music_prompt', 'upbeat energetic pub background music')
        
        # No text truncation - let TTS handle the full text
        # Duration will be calculated dynamically after TTS generation
        
        logger.info(f"Generating jingle for text: '{text[:50]}...'")
        
        # Get voice settings (with defaults)
        voice_settings = data.get('voiceSettings', {})
        voice_settings_payload = {
            'stability': voice_settings.get('stability', 0.5),
            'similarity_boost': voice_settings.get('similarity_boost', 0.75),
            'style': voice_settings.get('style', 0.5),
            'use_speaker_boost': voice_settings.get('use_speaker_boost', True)
        }
        
        # Validation
        if not text:
            return Response({'error': 'Text is required'}, status=400)
        
        if len(text) > 1000:
            return Response({'error': 'Text too long (max 1000 characters / ~200 words)'}, status=400)
        
        if not ELEVENLABS_API_KEY:
            return Response({'error': 'ElevenLabs API key not configured'}, status=500)
        
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
                'prompt': prompt,
                'voice_id': voice_id,
                'music_style': music_style,
                'duration_seconds': duration_seconds
            }
        )
        
        # Start background task
        def background_jingle_generation():
            try:
                logger.info(f"Task {task_id}: Starting generation process")
                task.status = 'processing'
                task.save(update_fields=['status'])
                
                # Step 1: Generate TTS
                logger.info(f"Task {task_id}: Generating TTS...")
                task.progress = 20
                task.current_step = 'generating_voice'
                task.save(update_fields=['progress', 'current_step'])
                
                tts_url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
                tts_payload = {
                    'text': text,
                    'model_id': 'eleven_multilingual_v2',
                    'voice_settings': voice_settings_payload
                }
                tts_headers = {
                    'xi-api-key': ELEVENLABS_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                tts_response = requests.post(tts_url, json=tts_payload, headers=tts_headers, timeout=30)
                
                if tts_response.status_code != 200:
                    raise Exception(f'TTS API error: {tts_response.status_code} - {tts_response.text}')
                
                tts_bytes = tts_response.content
                logger.info(f"Task {task_id}: TTS generated ({len(tts_bytes)} bytes)")
                
                # Calculate actual TTS duration to generate matching music
                from pydub import AudioSegment
                tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
                tts_duration_seconds = len(tts_audio) / 1000  # Convert ms to seconds
                logger.info(f"Task {task_id}: TTS duration: {tts_duration_seconds:.2f}s")
                
                # Generate music with TTS duration + 2 seconds for intro/outro
                music_duration = min(max(int(tts_duration_seconds) + 2, 5), 30)  # Between 5-30 seconds
                logger.info(f"Task {task_id}: Music target duration: {music_duration}s")
                
                # Step 2: Generate Music
                logger.info(f"Task {task_id}: Generating music...")
                task.progress = 50
                task.current_step = 'generating_music'
                task.save(update_fields=['progress', 'current_step'])
                
                # ElevenLabs Music Generation API
                music_url = 'https://api.elevenlabs.io/v1/sound-generation'
                music_payload = {
                    'text': music_prompt,
                    'duration_seconds': music_duration
                }
                music_headers = {
                    'xi-api-key': ELEVENLABS_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                music_response = requests.post(music_url, json=music_payload, headers=music_headers, timeout=60)
                
                if music_response.status_code != 200:
                    logger.warning(f"Music API error: {music_response.status_code}, using fallback")
                    # Fallback: use silent background or default music
                    # For now, we'll create a simple tone as placeholder
                    from pydub.generators import Sine
                    music_audio = Sine(440).to_audio_segment(duration=music_duration * 1000).apply_gain(-20)
                    music_io = io.BytesIO()
                    music_audio.export(music_io, format='mp3')
                    music_bytes = music_io.getvalue()
                else:
                    music_bytes = music_response.content
                
                logger.info(f"Task {task_id}: Music generated ({len(music_bytes)} bytes)")
                
                # Step 3: Mix audio
                logger.info(f"Task {task_id}: Mixing audio...")
                task.progress = 75
                task.current_step = 'mixing'
                task.save(update_fields=['progress', 'current_step'])
                
                mixed_audio = mix_tts_with_music(tts_bytes, music_bytes)
                
                # Step 4: Save file
                logger.info(f"Task {task_id}: Saving file...")
                task.progress = 90
                task.current_step = 'finalizing'
                task.save(update_fields=['progress', 'current_step'])
                
                jingles_dir = DATA_DIR / 'jingles'
                jingles_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = int(time.time())
                filename = f'jingle_{timestamp}_{task_id[:8]}.mp3'
                file_path = jingles_dir / filename
                
                with open(file_path, 'wb') as f:
                    f.write(mixed_audio)
                
                logger.info(f"Task {task_id}: Jingle saved to {file_path}")
                
                # Calculate actual duration from final mixed audio
                from pydub import AudioSegment
                final_audio = AudioSegment.from_mp3(io.BytesIO(mixed_audio))
                actual_duration = len(final_audio) / 1000  # ms to seconds
                
                # Update task status
                task.status = 'completed'
                task.progress = 100
                task.current_step = 'completed'
                task.result = {
                    'audio_url': f'/api/jingles/{filename}',
                    'filename': filename,
                    'duration_seconds': actual_duration,
                    'size_bytes': len(mixed_audio)
                }
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'progress', 'current_step', 'result', 'completed_at'])
                
                logger.info(f"Task {task_id}: COMPLETED successfully")
                
            except Exception as e:
                logger.error(f"Task {task_id}: ERROR - {e}", exc_info=True)
                task.status = 'failed'
                task.error = str(e)
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'error', 'completed_at'])
        
        # Start thread
        thread = threading.Thread(target=background_jingle_generation)
        thread.daemon = True
        thread.start()
        
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
        
        if not ELEVENLABS_API_KEY:
            return Response({'error': 'ElevenLabs API key not configured'}, status=500)
        
        logger.info(f"Generating music preview: '{music_prompt}', {duration}s")
        
        # Call ElevenLabs Sound Generation API
        url = 'https://api.elevenlabs.io/v1/sound-generation'
        payload = {
            'text': music_prompt,
            'duration_seconds': duration
        }
        headers = {
            'xi-api-key': ELEVENLABS_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Music API error: {response.status_code} - {response.text}")
            # Return a fallback simple tone
            from pydub.generators import Sine
            music_audio = Sine(440).to_audio_segment(duration=duration * 1000).apply_gain(-20)
            music_io = io.BytesIO()
            music_audio.export(music_io, format='mp3')
            music_io.seek(0)
            
            return HttpResponse(music_io.getvalue(), content_type='audio/mpeg')
        
        logger.info(f"Music preview generated: {len(response.content)} bytes")
        
        # Return audio directly
        return HttpResponse(response.content, content_type='audio/mpeg')
        
    except Exception as e:
        logger.error(f"Error generating music preview: {e}", exc_info=True)


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
        
        jingles_dir = DATA_DIR / 'jingles'
        logger.info(f'Looking for jingles in: {jingles_dir}')
        logger.info(f'Directory exists: {jingles_dir.exists()}')
        
        if not jingles_dir.exists():
            logger.warning('Jingles directory does not exist')
            return Response([])
        
        jingles = []
        for file_path in jingles_dir.glob('*.mp3'):
            # Get file metadata
            stat = file_path.stat()
            
            # Try to load metadata JSON if exists
            metadata_path = file_path.with_suffix('.json')
            metadata = {}
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Error loading metadata for {file_path.name}: {e}")
            
            jingles.append({
                'filename': file_path.name,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'size': stat.st_size,
                'metadata': metadata
            })
        
        # Sort by creation time (newest first)
        jingles.sort(key=lambda x: x['created'], reverse=True)
        
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
            if playlist_file.exists():
                with open(playlist_file, 'r') as f:
                    playlist = json.load(f)
            else:
                playlist = {
                    'jingles': [],
                    'enabled': False,
                    'interval': 3
                }
            
            return Response(playlist)
            
        except Exception as e:
            logger.error(f"Error loading playlist: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = request.data
            
            # Validate jingle files exist
            jingles_dir = DATA_DIR / 'jingles'
            validated_jingles = []
            for filename in data.get('jingles', []):
                file_path = jingles_dir / filename
                if file_path.exists():
                    validated_jingles.append(filename)
                else:
                    logger.warning(f"Jingle not found: {filename}")
            
            playlist = {
                'jingles': validated_jingles,
                'enabled': data.get('enabled', False),
                'interval': int(data.get('interval', 3))
            }
            
            # Save playlist
            with open(playlist_file, 'w') as f:
                json.dump(playlist, f, indent=2)
            
            logger.info(f"Playlist updated: {len(validated_jingles)} jingles, enabled={playlist['enabled']}")
            return Response(playlist)
            
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
            from .models import JingleSchedule
            
            # Get venue_name from query params
            venue_name = request.GET.get('venue_name')
            
            # Filter schedules
            if venue_name:
                # Get schedules for specific venue OR schedules without venue (global)
                all_schedules = JingleSchedule.objects.filter(
                    models.Q(venue_name=venue_name) | models.Q(venue_name__isnull=True) | models.Q(venue_name='')
                ).order_by('-priority', '-created_at')
                logger.info(f'Filtering schedules for venue: {venue_name}')
            else:
                # Get all schedules
                all_schedules = JingleSchedule.objects.all().order_by('-priority', '-created_at')
                logger.info('Returning all schedules (no venue filter)')
            
            schedules_list = []
            for schedule in all_schedules:
                schedules_list.append({
                    'id': schedule.id,
                    'jingle_name': schedule.jingle_name,
                    'jingle_filename': schedule.jingle_filename,
                    'venue_name': schedule.venue_name,
                    'start_date': schedule.start_date.strftime('%Y-%m-%d'),
                    'end_date': schedule.end_date.strftime('%Y-%m-%d') if schedule.end_date else None,
                    'time_start': schedule.time_start.strftime('%H:%M') if schedule.time_start else None,
                    'time_end': schedule.time_end.strftime('%H:%M') if schedule.time_end else None,
                    'days_of_week': {
                        'monday': schedule.monday,
                        'tuesday': schedule.tuesday,
                        'wednesday': schedule.wednesday,
                        'thursday': schedule.thursday,
                        'friday': schedule.friday,
                        'saturday': schedule.saturday,
                        'sunday': schedule.sunday
                    },
                    'repeat_pattern': schedule.repeat_pattern,
                    'enabled': schedule.enabled,
                    'priority': schedule.priority,
                    'is_active_now': schedule.is_active_now(),
                    'interval': schedule.get_interval(),
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat()
                })
            
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
        from .models import JingleSchedule
        from datetime import datetime
        
        data = request.data
        
        # Validate required fields
        jingle_name = data.get('jingle_name', '').strip()
        if not jingle_name:
            return Response({
                'error': 'Jingle name is required'
            }, status=400)
        
        jingle_filename = data.get('jingle_filename', '').strip()
        if not jingle_filename:
            return Response({
                'error': 'Jingle filename is required'
            }, status=400)
        
        # Verify jingle file exists (optional check - skip if in development)
        jingles_dir = DATA_DIR / 'jingles'
        jingle_path = jingles_dir / jingle_filename
        if not jingle_path.exists():
            logger.warning(f'Jingle file not found at {jingle_path}, but continuing anyway')
            # In production, uncomment this to enforce file existence:
            # return Response({
            #     'error': f'Jingle file not found: {jingle_filename}'
            # }, status=404)
        
        start_date = data.get('start_date')
        if not start_date:
            return Response({
                'error': 'Start date is required'
            }, status=400)
        
        # Validate date format
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'error': 'Invalid start_date format. Use YYYY-MM-DD'
            }, status=400)
        
        # Validate end_date if provided
        end_date = data.get('end_date')
        end_date_obj = None
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid end_date format. Use YYYY-MM-DD'
                }, status=400)
            
            # Validate end_date is after start_date
            if end_date_obj < start_date_obj:
                return Response({
                    'error': 'End date must be after start date'
                }, status=400)
        
        # Validate time_start and time_end if provided
        time_start = data.get('time_start')
        time_end = data.get('time_end')
        time_start_obj = None
        time_end_obj = None
        
        if time_start:
            try:
                time_start_obj = datetime.strptime(time_start, '%H:%M').time()
            except ValueError:
                return Response({
                    'error': 'Invalid time_start format. Use HH:MM'
                }, status=400)
        
        if time_end:
            try:
                time_end_obj = datetime.strptime(time_end, '%H:%M').time()
            except ValueError:
                return Response({
                    'error': 'Invalid time_end format. Use HH:MM'
                }, status=400)
        
        # Validate time_end is after time_start
        if time_start_obj and time_end_obj and time_end_obj <= time_start_obj:
            return Response({
                'error': 'End time must be after start time'
            }, status=400)
        
        # Validate days_of_week
        days_of_week = data.get('days_of_week', {})
        if not any(days_of_week.values()):
            return Response({
                'error': 'At least one day of the week must be selected'
            }, status=400)
        
        # Validate repeat_pattern
        repeat_pattern = data.get('repeat_pattern', 'regular')
        if repeat_pattern not in ['occasional', 'regular', 'often']:
            return Response({
                'error': 'Invalid repeat_pattern. Must be: occasional, regular, or often'
            }, status=400)
        
        # Validate priority
        priority = int(data.get('priority', 0))
        if priority < 0 or priority > 100:
            return Response({
                'error': 'Priority must be between 0 and 100'
            }, status=400)
        
        # Get optional venue_name
        venue_name = data.get('venue_name', '').strip() or None
        
        # Create JingleSchedule
        schedule = JingleSchedule.objects.create(
            jingle_name=jingle_name,
            jingle_filename=jingle_filename,
            venue_name=venue_name,
            start_date=start_date_obj,
            end_date=end_date_obj,
            time_start=time_start_obj,
            time_end=time_end_obj,
            monday=days_of_week.get('monday', False),
            tuesday=days_of_week.get('tuesday', False),
            wednesday=days_of_week.get('wednesday', False),
            thursday=days_of_week.get('thursday', False),
            friday=days_of_week.get('friday', False),
            saturday=days_of_week.get('saturday', False),
            sunday=days_of_week.get('sunday', False),
            repeat_pattern=repeat_pattern,
            enabled=data.get('enabled', True),
            priority=priority
        )
        
        logger.info(f"Created jingle schedule #{schedule.id}: {jingle_name}")
        
        return Response({
            'success': True,
            'schedule_id': schedule.id,
            'message': 'Schedule created successfully'
        }, status=201)
        
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
        from .models import JingleSchedule
        from django.db import models as django_models
        
        # Get venue_name from query params
        venue_name = request.GET.get('venue_name')
        
        # Filter schedules by venue
        if venue_name:
            # Get schedules for specific venue OR global schedules (no venue set)
            all_schedules = JingleSchedule.objects.filter(
                enabled=True
            ).filter(
                django_models.Q(venue_name=venue_name) | django_models.Q(venue_name__isnull=True) | django_models.Q(venue_name='')
            ).order_by('-priority', '-created_at')
            logger.info(f'Filtering active jingles for venue: {venue_name}')
        else:
            # Get all enabled schedules
            all_schedules = JingleSchedule.objects.filter(enabled=True).order_by('-priority', '-created_at')
            logger.info('Returning all active jingles (no venue filter)')
        
        # Filter to only active schedules using is_active_now()
        active_schedules = []
        for schedule in all_schedules:
            if schedule.is_active_now():
                active_schedules.append({
                    'id': schedule.id,
                    'jingle_name': schedule.jingle_name,
                    'jingle_filename': schedule.jingle_filename,
                    'interval': schedule.get_interval(),
                    'priority': schedule.priority
                })
        
        logger.info(f'✅ Found {len(active_schedules)} active jingle schedules out of {len(all_schedules)} total')
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
        from .models import JingleSchedule
        
        # Get schedule by ID
        try:
            schedule = JingleSchedule.objects.get(id=schedule_id)
        except JingleSchedule.DoesNotExist:
            return Response({
                'error': f'Schedule with id {schedule_id} not found'
            }, status=404)
        
        # Store name for logging before deletion
        schedule_name = schedule.jingle_name
        
        # Delete the schedule
        schedule.delete()
        
        logger.info(f"Deleted jingle schedule #{schedule_id}: {schedule_name}")
        
        return Response({
            'success': True,
            'message': 'Schedule deleted successfully'
        })
        
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
            data = request.data
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session
            session = BingoSession.objects.create(
                session_id=session_id,
                venue_name=data.get('venue_name', ''),
                host_name=data.get('host_name', ''),
                num_players=data.get('num_players', 25),
                voice_id=data.get('voice_id', 'JBFqnCBsd6RMkjVDRZzb'),
                decades=data.get('decades', ['1960s', '1970s', '1980s', '1990s']),
                logo_url=data.get('logo_url', ''),
                social_media=data.get('social_media', ''),
                include_qr=data.get('include_qr', False),
                prizes=data.get('prizes', {}),
                status='pending'
            )
            
            logger.info(f"Created bingo session: {session_id} for {session.venue_name}")
            
            return Response({
                'success': True,
                'session_id': session_id,
                'message': 'Session created successfully'
            }, status=201)
            
        except Exception as e:
            logger.error(f"Error creating bingo session: {e}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    else:  # GET
        try:
            venue_name = request.GET.get('venue')
            
            if venue_name:
                sessions = BingoSession.objects.filter(venue_name__icontains=venue_name)
            else:
                sessions = BingoSession.objects.all()[:50]  # Limit to 50 recent
            
            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    'session_id': session.session_id,
                    'venue_name': session.venue_name,
                    'host_name': session.host_name,
                    'num_players': session.num_players,
                    'status': session.status,
                    'songs_count': session.get_songs_count(),
                    'duration_minutes': session.get_duration_minutes(),
                    'created_at': session.created_at.isoformat(),
                    'started_at': session.started_at.isoformat() if session.started_at else None,
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                })
            
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
        return Response({
            'session_id': session.session_id,
            'venue_name': session.venue_name,
            'host_name': session.host_name,
            'num_players': session.num_players,
            'voice_id': session.voice_id,
            'decades': session.decades,
            'logo_url': session.logo_url,
            'social_media': session.social_media,
            'include_qr': session.include_qr,
            'prizes': session.prizes,
            'songs_played': session.songs_played,
            'current_song_index': session.current_song_index,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
    
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

