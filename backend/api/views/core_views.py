"""
Core Utility Views

This module provides core utility endpoints for the Music Bingo application:
- health_check: System health monitoring endpoint
- get_pool: Retrieve music pool data
- get_task_status: Check status of async tasks (card generation, jingle generation)
- get_config: Get public configuration settings

These endpoints provide essential infrastructure services used across the application.
"""

import json
import logging

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import TaskStatus
from ..utils.config import DATA_DIR, VENUE_NAME

logger = logging.getLogger(__name__)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    logger.info("Health check endpoint called")
    return Response({'status': 'healthy', 'message': 'Music Bingo API (Django)'})


@api_view(['GET'])
def get_pool(request):
    """Get music pool data"""
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


@api_view(['GET'])
def get_session(request):
    """
    Get session data with exact songs used in printed cards
    
    Supports two modes:
    1. Query by session_id: /api/session?session_id=<uuid>
       Returns session from database (recommended for production)
       
    2. Legacy mode: /api/session (no params)
       Tries GCS → local file fallback (for backward compatibility)
    
    CRITICAL: This endpoint returns the exact songs from card generation,
    ensuring the game plays the EXACT songs that appear on the printed cards.
    
    Returns:
        JSON with session info and song list
        
    Status Codes:
        200: Session found and returned
        404: Session not found
        500: Server error
    """
    try:
        from api.models import BingoSession
        import requests
        
        # Check if session_id provided (new database-backed approach)
        session_id = request.GET.get('session_id')
        
        if session_id:
            logger.info(f"📡 Fetching session from database: {session_id}")
            try:
                session = BingoSession.objects.get(session_id=session_id)
                logger.info(f"✅ Found BingoSession in database")
                logger.info(f"   ID: {session.session_id}")
                logger.info(f"   Venue: {session.venue_name}")
                logger.info(f"   Players: {session.num_players}")
                logger.info(f"   song_pool length: {len(session.song_pool)}")
                logger.info(f"   PDF URL: {session.pdf_url or 'none'}")
                logger.info(f"   Created: {session.created_at}")
                
                data = {
                    'session_id': session.session_id,
                    'venue_name': session.venue_name,
                    'num_players': session.num_players,
                    'songs': session.song_pool,
                    'generated_at': session.created_at.isoformat(),
                    'game_number': session.game_number,
                    'pdf_url': session.pdf_url,
                    'source': 'database'
                }
                
                if len(session.song_pool) == 0:
                    logger.warning(f"⚠️  Session {session_id} has EMPTY song_pool!")
                    logger.warning(f"   Cards may not have been generated yet.")
                else:
                    logger.info(f"✅ Returning {len(data['songs'])} songs for venue: {data['venue_name']}")
                
                return Response(data)
            except BingoSession.DoesNotExist:
                logger.error(f"❌ Session not found in database: {session_id}")
                return Response({
                    'error': 'Session not found',
                    'hint': 'The session may have been deleted or the session_id is incorrect'
                }, status=404)
        
        # Legacy mode: Try GCS first (persistent)
        gcs_url = 'https://storage.googleapis.com/music-bingo-cards/cards/current_session.json'
        
        try:
            logger.info(f"Fetching session from GCS: {gcs_url}")
            response = requests.get(gcs_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                data['source'] = 'gcs'
                logger.info(f"Session loaded from GCS: {len(data.get('songs', []))} songs, venue: {data.get('venue_name')}")
                return Response(data)
            else:
                logger.warning(f"GCS returned status {response.status_code}")
        except Exception as gcs_error:
            logger.warning(f"Could not fetch from GCS: {gcs_error}")
        
        # Fallback to local file (if container hasn't restarted)
        session_path = DATA_DIR / 'cards' / 'current_session.json'
        logger.info(f"Trying local file: {session_path}")
        
        if not session_path.exists():
            logger.warning(f"Session file not found locally or in GCS")
            return Response({
                'error': 'No session file found. Generate cards first.',
                'hint': 'Use the "Generate Cards" button to create a new game session'
            }, status=404)
        
        with open(session_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['source'] = 'local'
        logger.info(f"Session loaded locally: {len(data.get('songs', []))} songs, venue: {data.get('venue_name')}")
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error loading session: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_task_status(request, task_id):
    """Get async task status"""
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


@api_view(['GET'])
def get_config(request):
    """Get public configuration"""
    return Response({'venue_name': VENUE_NAME})
