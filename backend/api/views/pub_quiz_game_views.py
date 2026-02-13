"""
Pub Quiz Game Views — Live quiz control: host data, start, next, countdown, auto-advance

Endpoints:
- quiz_host_data: Full data dump for host panel
- start_quiz: Start the quiz and send all questions
- get_all_questions: Get all questions for local navigation
- sync_question_to_players: Sync current question via SSE
- start_countdown: Mark countdown start after TTS finishes
- next_question: Advance to next question/round/halftime
- toggle_auto_advance: Toggle auto-advance on/off
- pause_auto_advance: Pause/resume auto-advance timer
- set_auto_advance_time: Set auto-advance duration
- generate_quiz_questions: Generate questions via AI
"""

import logging

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..pub_quiz_models import QuizQuestion
from ..utils.pub_quiz_helpers import (
    get_session_by_code_or_id,
    serialize_question_for_player,
    serialize_question_for_host,
    get_timing_config,
)
from ..services.pub_quiz_service import PubQuizService

logger = logging.getLogger(__name__)


@api_view(['GET'])
def quiz_host_data(request, session_id):
    """Full data dump for the host panel."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    teams = session.teams.all().order_by('-total_score')
    rounds = session.rounds.all()
    questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')

    # Current question details
    current_question_obj = None
    if session.current_round and session.current_question:
        current_question_obj = questions.filter(
            round_number=session.current_round,
            question_number=session.current_question,
        ).first()

    return Response({
        'session': {
            'id': session.id,
            'venue_name': session.venue_name,
            'status': session.status,
            'current_round': session.current_round,
            'current_question': session.current_question,
            'total_rounds': session.total_rounds,
            'questions_per_round': session.questions_per_round,
        },
        'current_question': {
            'number': session.current_question,
            'text': current_question_obj.question_text if current_question_obj else None,
            'question_started_at': session.question_started_at.isoformat() if session.question_started_at else None,
        } if current_question_obj else None,
        'teams': [{
            'id': t.id,
            'team_name': t.team_name,
            'total_score': t.total_score,
            'bonus_points': t.bonus_points,
        } for t in teams],
        'rounds': [{
            'round_number': r.round_number,
            'round_name': r.round_name,
            'is_completed': r.is_completed,
        } for r in rounds],
        'questions': [{
            'id': q.id,
            'round_number': q.round_number,
            'question_number': q.question_number,
            'question_text': q.question_text,
            'question_type': q.question_type,
        } for q in questions],
    })


@api_view(['POST'])
def start_quiz(request, session_id):
    """Start the quiz: set status and return all questions for players."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    result = PubQuizService.start_quiz(session)

    return Response({
        'success': True,
        'status': 'in_progress',
        **result,
    })


@api_view(['GET'])
def get_all_questions(request, session_id):
    """Get all questions for local host navigation (no SSE needed)."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')
    questions_data = [serialize_question_for_host(q) for q in questions]

    return Response({
        'success': True,
        'questions': questions_data,
        'total': len(questions_data),
    })


@api_view(['POST'])
def sync_question_to_players(request, session_id):
    """Sync current question to player screens via SSE."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    data = request.data
    session.current_round = data.get('round')
    session.current_question = data.get('question_number')
    session.save()

    logger.debug(f"[SYNC] Host updated to Round {session.current_round}, Q{session.current_question}")

    return Response({'success': True, 'message': 'Question synced to players'})


@api_view(['POST'])
def start_countdown(request, session_id):
    """Mark countdown start after TTS finishes reading the question."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    session.question_started_at = timezone.now()
    session.save(update_fields=['question_started_at'])

    return Response({
        'success': True,
        'question_started_at': session.question_started_at.isoformat() if session.question_started_at else None,
    })


@api_view(['POST'])
def next_question(request, session_id):
    """Advance to the next question, round, halftime, or completion."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    result = PubQuizService.advance_to_next_question(session)
    result['success'] = True
    result['broadcast_to_players'] = True

    return Response(result)


@api_view(['POST'])
def toggle_auto_advance(request, session_id):
    """Toggle auto-advance on/off."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    session.auto_advance_enabled = not session.auto_advance_enabled
    if session.auto_advance_enabled and session.status == 'in_progress':
        session.question_started_at = timezone.now()
    session.save()

    return Response({
        'success': True,
        'auto_advance_enabled': session.auto_advance_enabled,
    })


@api_view(['POST'])
def pause_auto_advance(request, session_id):
    """Pause/resume auto-advance timer."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    session.auto_advance_paused = not session.auto_advance_paused
    session.save()

    return Response({
        'success': True,
        'auto_advance_paused': session.auto_advance_paused,
    })


@api_view(['POST'])
def set_auto_advance_time(request, session_id):
    """Set auto-advance timer duration (5–120 seconds)."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    seconds = request.data.get('seconds', 15)
    if seconds < 5 or seconds > 120:
        return Response({"error": "Seconds must be between 5 and 120"}, status=400)

    session.auto_advance_seconds = seconds
    session.save()

    return Response({
        'success': True,
        'auto_advance_seconds': session.auto_advance_seconds,
    })


@api_view(['POST'])
def generate_quiz_questions(request, session_id):
    """Generate quiz questions via AI based on genre votes."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    try:
        result = PubQuizService.generate_questions(session, request.data)

        return Response({
            'success': True,
            'message': 'Quiz generado exitosamente',
            'structure': result['structure'],
            'selected_genres': result['selected_genres'],
        })

    except Exception as e:
        logger.error(f"[GENERATE_QUESTIONS] Error: {e}", exc_info=True)
        # Clear progress on failure
        session.generation_progress = None
        session.save(update_fields=['generation_progress'])
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
