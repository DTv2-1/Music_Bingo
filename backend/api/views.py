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

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
FRONTEND_DIR = BASE_DIR.parent / 'frontend'

# In-memory task storage (works with 1 gunicorn worker)
tasks_storage = {}

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy', 'message': 'Music Bingo API (Django)'})

@api_view(['GET'])
def get_pool(request):
    try:
        pool_path = DATA_DIR / 'pool.json'
        with open(pool_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)
    except FileNotFoundError:
        return Response({'error': 'Pool file not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def generate_cards_async(request):
    """Generate cards asynchronously (Django)"""
    try:
        data = request.data
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        
        task_id = str(uuid.uuid4())
        
        tasks_storage[task_id] = {
            'status': 'pending',
            'result': None,
            'error': None,
            'started_at': time.time()
        }
        
        def background_task():
            try:
                tasks_storage[task_id]['status'] = 'processing'
                
                script_path = BASE_DIR / 'generate_cards.py'
                cmd = ['python3', str(script_path), '--venue_name', venue_name, '--num_players', str(num_players)]
                
                result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, timeout=180)
                
                if result.returncode != 0:
                    tasks_storage[task_id]['status'] = 'failed'
                    tasks_storage[task_id]['error'] = result.stderr
                    return
                
                tasks_storage[task_id]['status'] = 'completed'
                tasks_storage[task_id]['result'] = {
                    'success': True,
                    'download_url': '/data/cards/music_bingo_cards.pdf'
                }
            except Exception as e:
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
        announcements_path = DATA_DIR / 'announcements.json'
        with open(announcements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['venue_name'] = VENUE_NAME
        return Response(data)
    except FileNotFoundError:
        return Response({'error': 'Announcements not found'}, status=404)
    except Exception as e:
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
        if 'logo' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        
        file = request.FILES['logo']
        
        if not file.name:
            return Response({'error': 'No file selected'}, status=400)
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'}
        file_ext = file.name.rsplit('.', 1)[1].lower() if '.' in file.name else ''
        
        if file_ext not in allowed_extensions:
            return Response({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}, status=400)
        
        logos_dir = DATA_DIR / 'logos'
        logos_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        safe_filename = f'pub_logo_{timestamp}.{file_ext}'
        file_path = logos_dir / safe_filename
        
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        logo_url = f'/data/logos/{safe_filename}'
        
        return Response({
            'success': True,
            'url': logo_url,
            'filename': safe_filename
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_config(request):
    """Get public configuration"""
    return Response({'venue_name': VENUE_NAME})
