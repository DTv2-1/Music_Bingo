"""
Pub Quiz Session Views — CRUD operations for quiz sessions

Endpoints:
- get_sessions: List sessions with optional status filter
- create_quiz_session: Create a new quiz session
- delete_session: Delete a session by code/ID
- bulk_delete_sessions: Delete multiple sessions at once
- reset_quiz: Reset a session to registration state
"""

import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..utils.pub_quiz_helpers import get_session_by_code_or_id, serialize_session_summary
from ..services.pub_quiz_service import PubQuizService

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_sessions(request):
    """List pub quiz sessions with optional status filter."""
    from ..pub_quiz_models import PubQuizSession

    status_filter = request.GET.get('status', None)
    sessions = PubQuizSession.objects.all()

    if status_filter:
        sessions = sessions.filter(status=status_filter)

    sessions = sessions.order_by('-date', '-id')[:20]
    data = [serialize_session_summary(s) for s in sessions]

    return Response({'success': True, 'sessions': data})


@api_view(['POST'])
def create_quiz_session(request):
    """Create a new pub quiz session."""
    try:
        session = PubQuizService.create_session(request.data)

        return Response({
            'success': True,
            'session_id': session.session_code,
            'session': {
                'id': session.id,
                'session_code': session.session_code,
                'venue_name': session.venue_name,
                'status': session.status,
                'total_rounds': session.total_rounds,
                'questions_per_round': session.questions_per_round,
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"[CREATE_SESSION] Error: {e}", exc_info=True)
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_session(request, session_id):
    """Delete a session and all related data (cascade)."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    venue_name = PubQuizService.delete_session(session)

    return Response({
        'success': True,
        'message': f'Session "{venue_name}" deleted successfully'
    })


@api_view(['DELETE'])
def bulk_delete_sessions(request):
    """Delete multiple sessions at once."""
    session_ids = request.data.get('session_ids', [])

    if not session_ids:
        return Response({"error": "No session IDs provided"}, status=400)
    if not isinstance(session_ids, list):
        return Response({"error": "session_ids must be an array"}, status=400)

    deleted_count = 0
    errors = []

    for sid in session_ids:
        try:
            session = get_session_by_code_or_id(sid)
            if session:
                PubQuizService.delete_session(session)
                deleted_count += 1
            else:
                errors.append(f"Session {sid} not found")
        except Exception as e:
            errors.append(f"Error deleting session {sid}: {str(e)}")

    return Response({
        'success': True,
        'deleted_count': deleted_count,
        'total_requested': len(session_ids),
        'errors': errors if errors else None
    })


@api_view(['POST'])
def reset_quiz(request, session_id):
    """Reset a quiz session to its initial state."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    PubQuizService.reset_session(session)

    return Response({'success': True, 'message': 'Quiz reset successfully'})
