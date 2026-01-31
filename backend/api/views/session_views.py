"""
Bingo Session Management Views
"""

import logging
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..services.bingo_session_service import BingoSessionService
from ..validators import validate_session_status

logger = logging.getLogger(__name__)


@api_view(['POST', 'GET'])
def bingo_sessions(request):
    """
    Create or list bingo sessions
    POST: Create new session
    GET: List all sessions (with optional venue filter)
    """
    from ..models import BingoSession
    
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
    from ..models import BingoSession
    
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
