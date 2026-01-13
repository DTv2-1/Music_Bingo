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
from pathlib import Path
from datetime import datetime

from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

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

# In-memory task storage (works with 1 gunicorn worker)
tasks_storage = {}

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
        
        logger.info(f"Starting async card generation: {num_players} cards for '{venue_name}'")
        logger.info(f"  pub_logo: {pub_logo}, social_media: {social_media}, include_qr: {include_qr}")
        
        task_id = str(uuid.uuid4())
        
        tasks_storage[task_id] = {
            'status': 'pending',
            'result': None,
            'error': None,
            'progress': 0,
            'started_at': time.time()
        }
        
        def background_task():
            try:
                logger.info(f"Task {task_id}: Processing started")
                tasks_storage[task_id]['status'] = 'processing'
                
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
                                tasks_storage[task_id]['progress'] = progress_val
                                logger.info(f"Task {task_id}: Progress updated to {progress_val}%")
                            except Exception as e:
                                logger.warning(f"Task {task_id}: Failed to parse progress: {e}")
                        # Also parse emoji format for backwards compatibility
                        elif '📊 Progress:' in line:
                            try:
                                progress_str = line.split('Progress:')[1].split('%')[0].strip()
                                tasks_storage[task_id]['progress'] = int(float(progress_str))
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
                    tasks_storage[task_id]['status'] = 'failed'
                    tasks_storage[task_id]['error'] = result.stderr
                    return
                
                logger.info(f"Task {task_id}: Completed successfully")
                tasks_storage[task_id]['status'] = 'completed'
                tasks_storage[task_id]['result'] = {
                    'success': True,
                    'download_url': '/data/cards/music_bingo_cards.pdf'
                }
            except Exception as e:
                logger.error(f"Task {task_id}: Exception: {str(e)}")
                tasks_storage[task_id]['status'] = 'failed'
                tasks_storage[task_id]['error'] = str(e)
        
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        
        return Response({'task_id': task_id, 'status': 'pending'}, status=202)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_task_status(request, task_id):
    if task_id not in tasks_storage:
        return Response({'error': 'Task not found'}, status=404)
    
    task = tasks_storage[task_id]
    response = {
        'task_id': task_id,
        'status': task['status'],
        'progress': task.get('progress', 0),
        'elapsed_time': round(time.time() - task['started_at'], 2)
    }
    
    if task['status'] == 'completed':
        response['result'] = task['result']
    elif task['status'] == 'failed':
        response['error'] = task['error']
    
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
