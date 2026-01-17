"""
Karaoke System Views
Handles karaoke sessions, queue management, and song selection
"""

import logging
from datetime import datetime
from django.http import JsonResponse
from django.db import models as django_models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import KaraokeSession, KaraokeQueue

logger = logging.getLogger(__name__)


# ============================================================
# SESSION MANAGEMENT
# ============================================================

@api_view(['POST'])
def create_session(request):
    """
    POST /api/karaoke/session
    Create a new karaoke session for a venue
    """
    try:
        venue_name = request.data.get('venue_name')
        if not venue_name:
            return Response({'error': 'venue_name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there's already an active session
        existing = KaraokeSession.objects.filter(
            venue_name=venue_name,
            status__in=['waiting', 'active', 'paused']
        ).first()
        
        if existing:
            return Response({
                'id': existing.id,
                'venue_name': existing.venue_name,
                'status': existing.status,
                'created_at': existing.created_at,
                'queue_count': existing.get_queue_count(),
                'message': 'Using existing active session'
            })
        
        # Create new session
        avg_duration = request.data.get('avg_song_duration', 240)
        session = KaraokeSession.objects.create(
            venue_name=venue_name,
            avg_song_duration=avg_duration
        )
        
        logger.info(f"✅ Created karaoke session for {venue_name}: {session.id}")
        
        return Response({
            'id': session.id,
            'venue_name': session.venue_name,
            'status': session.status,
            'created_at': session.created_at,
            'queue_count': 0
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating karaoke session: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_session(request, venue_name):
    """GET /api/karaoke/session/<venue_name>"""
    try:
        session = KaraokeSession.objects.filter(
            venue_name=venue_name,
            status__in=['waiting', 'active', 'paused']
        ).first()
        
        if not session:
            return Response({'error': 'No active session found'}, status=status.HTTP_404_NOT_FOUND)
        
        current_singer = session.get_current_singer()
        current_data = None
        if current_singer:
            current_data = {
                'id': current_singer.id,
                'name': current_singer.name,
                'song_title': current_singer.song_title,
                'artist': current_singer.artist
            }
        
        queue = session.get_active_queue()
        queue_data = [{
            'id': e.id,
            'name': e.name,
            'song_title': e.song_title,
            'artist': e.artist,
            'position': e.position,
            'estimated_wait': e.estimated_wait_time()
        } for e in queue]
        
        return Response({
            'session': {
                'id': session.id,
                'venue_name': session.venue_name,
                'status': session.status,
                'queue_count': session.get_queue_count()
            },
            'current_singer': current_data,
            'queue': queue_data
        })
        
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_to_queue(request):
    """POST /api/karaoke/queue - Add singer to queue"""
    try:
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = KaraokeSession.objects.get(id=session_id)
        
        # Get next position
        max_position = session.queue_entries.filter(status='pending').aggregate(
            max_pos=django_models.Max('position')
        )['max_pos']
        next_position = (max_position or 0) + 1
        
        # Create entry
        entry = KaraokeQueue.objects.create(
            session=session,
            name=request.data.get('name'),
            song_id=request.data.get('song_id'),
            song_title=request.data.get('song_title'),
            artist=request.data.get('artist'),
            message=request.data.get('message', ''),
            duration=request.data.get('duration', 240),
            audio_url=request.data.get('audio_url', ''),
            lyrics_url=request.data.get('lyrics_url', ''),
            position=next_position
        )
        
        logger.info(f"✅ Added to queue: {entry.name} - {entry.song_title}")
        
        return Response({
            'id': entry.id,
            'name': entry.name,
            'song_title': entry.song_title,
            'position': entry.position,
            'estimated_wait': entry.estimated_wait_time()
        }, status=status.HTTP_201_CREATED)
        
    except KaraokeSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error adding to queue: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_queue(request, session_id):
    """GET /api/karaoke/queue/<session_id>"""
    try:
        session = KaraokeSession.objects.get(id=session_id)
        queue = session.get_active_queue()
        
        queue_data = [{
            'id': e.id,
            'name': e.name,
            'song_title': e.song_title,
            'artist': e.artist,
            'position': e.position,
            'estimated_wait': e.estimated_wait_time(),
            'audio_url': e.audio_url,
            'lyrics_url': e.lyrics_url
        } for e in queue]
        
        return Response({'session_id': session.id, 'queue': queue_data, 'count': len(queue_data)})
        
    except KaraokeSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting queue: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def cancel_entry(request, entry_id):
    """DELETE /api/karaoke/queue/<entry_id>"""
    try:
        entry = KaraokeQueue.objects.get(id=entry_id)
        
        if entry.status == 'singing':
            return Response({'error': 'Cannot cancel currently singing'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = entry.session
        entry.status = 'cancelled'
        entry.save()
        
        # Reorder remaining
        for idx, e in enumerate(session.get_active_queue(), start=1):
            e.position = idx
            e.save()
        
        logger.info(f"Cancelled: {entry.name} - {entry.song_title}")
        return Response({'message': 'Entry cancelled'})
        
    except KaraokeQueue.DoesNotExist:
        return Response({'error': 'Entry not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error cancelling entry: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def complete_entry(request, entry_id):
    """PATCH /api/karaoke/queue/<entry_id>/complete"""
    try:
        entry = KaraokeQueue.objects.get(id=entry_id)
        
        if entry.status != 'singing':
            entry.status = 'singing'
            entry.started_at = datetime.now()
            entry.save()
        
        entry.status = 'completed'
        entry.completed_at = datetime.now()
        entry.save()
        
        # Auto-advance to next
        session = entry.session
        next_entry = session.get_active_queue().first()
        next_singer = None
        
        if next_entry and session.auto_advance:
            next_entry.status = 'singing'
            next_entry.started_at = datetime.now()
            next_entry.save()
            next_singer = {
                'id': next_entry.id,
                'name': next_entry.name,
                'song_title': next_entry.song_title,
                'audio_url': next_entry.audio_url,
                'lyrics_url': next_entry.lyrics_url
            }
        
        logger.info(f"✅ Completed: {entry.name} - {entry.song_title}")
        
        return Response({
            'message': 'Entry completed',
            'completed_entry': {'id': entry.id, 'name': entry.name},
            'next_singer': next_singer
        })
        
    except KaraokeQueue.DoesNotExist:
        return Response({'error': 'Entry not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error completing entry: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
