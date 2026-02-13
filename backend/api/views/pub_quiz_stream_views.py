"""
Pub Quiz Stream Views — Server-Sent Events for real-time sync

Endpoints:
- quiz_stream: SSE for players (receives all questions, question updates, halftime)
- host_stream: SSE for host panel (stats, leaderboard, answers, progress)
"""

import json
import time
import logging

from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from ..pub_quiz_models import QuizQuestion
from ..utils.pub_quiz_helpers import (
    get_session_by_code_or_id,
    serialize_question_for_player,
    get_timing_config,
)
from ..services.pub_quiz_service import PubQuizService

logger = logging.getLogger(__name__)

# Global dict to track last question position per session for SSE sync
_player_question_positions = {}


def quiz_stream(request, session_id):
    """
    SSE endpoint for real-time quiz updates to players.
    Sends ALL questions when quiz starts, then streams position/status changes.
    """
    def event_generator():
        session = get_session_by_code_or_id(session_id)
        if not session:
            yield f'data: {{"type": "error", "message": "Session not found"}}\n\n'
            return

        connection_start = timezone.now()
        MAX_CONNECTION_TIME = 300  # 5 minutes

        last_status = None
        quiz_started_sent = False
        last_keepalive = timezone.now()

        # Initial connection
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        logger.debug(f"[SSE] Player connected to session {session_id}")

        while True:
            try:
                # Timeout guard
                if (timezone.now() - connection_start).total_seconds() > MAX_CONNECTION_TIME:
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout, please refresh'})}\n\n"
                    break

                session.refresh_from_db()

                # Quiz completed
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Quiz completed'})}\n\n"
                    break

                status_changed = session.status != last_status

                # Send all questions when quiz starts (or player connects late)
                should_send_questions = (
                    session.status == 'in_progress'
                    and not quiz_started_sent
                    and (status_changed or last_status is None)
                )

                if should_send_questions:
                    all_questions = QuizQuestion.objects.filter(
                        session=session
                    ).order_by('round_number', 'question_number')

                    questions_data = [serialize_question_for_player(q) for q in all_questions]

                    data = {
                        'type': 'quiz_started',
                        'all_questions': questions_data,
                        'timing': get_timing_config(session),
                        'total_rounds': session.total_rounds,
                        'questions_per_round': session.questions_per_round,
                        'current_round': session.current_round,
                        'current_question': session.current_question,
                    }

                    yield f"data: {json.dumps(data)}\n\n"
                    quiz_started_sent = True
                    last_status = session.status

                # Question sync: detect position changes
                if session.status == 'in_progress' and quiz_started_sent:
                    current_position = f"{session.current_round}.{session.current_question}"
                    last_position = _player_question_positions.get(session_id)

                    if last_position is not None and last_position != current_position:
                        question_update_data = {
                            'type': 'question_update',
                            'round': session.current_round,
                            'question': session.current_question,
                            'timing': get_timing_config(session),
                        }
                        yield f"data: {json.dumps(question_update_data)}\n\n"

                    _player_question_positions[session_id] = current_position

                # Other status changes
                elif status_changed:
                    if session.status in ('ready', 'registration'):
                        yield f"data: {json.dumps({'type': 'waiting', 'message': 'Waiting for quiz to start', 'status': session.status})}\n\n"
                    elif session.status == 'halftime':
                        halftime_data = {
                            'type': 'halftime',
                            'message': 'Halftime break - please wait',
                            'duration': 90,
                            'completed_round': session.current_round - 1,
                            'next_round': session.current_round,
                        }
                        yield f"data: {json.dumps(halftime_data)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status_change', 'status': session.status})}\n\n"

                    last_status = session.status

                # Data keepalive every 30s
                current_time = timezone.now()
                if (current_time - last_keepalive).total_seconds() >= 30:
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': current_time.isoformat()})}\n\n"
                    last_keepalive = current_time

                # Lightweight heartbeat comment
                yield ": heartbeat\n\n"
                time.sleep(1)

            except Exception as e:
                logger.error(f"[SSE] Player stream error for session {session_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
def host_stream(request, session_id):
    """
    SSE endpoint for the host panel.
    Streams stats, leaderboard, question data, answer counts, generation progress.
    """
    def event_generator():
        session = get_session_by_code_or_id(session_id)
        if not session:
            yield f'data: {{"type": "error", "message": "Session not found"}}\n\n'
            return

        connection_start = timezone.now()
        MAX_CONNECTION_TIME = 300

        last_status = session.status
        last_round = session.current_round
        last_question = session.current_question
        last_progress = None
        last_keepalive = timezone.now()
        last_update_time = timezone.now()
        last_answer_count = -1

        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

        while True:
            try:
                # Timeout guard
                if (timezone.now() - connection_start).total_seconds() > MAX_CONNECTION_TIME:
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout, please refresh'})}\n\n"
                    break

                session.refresh_from_db()

                # Generation progress
                progress_data = session.generation_progress
                if progress_data and progress_data != last_progress:
                    yield f"data: {json.dumps({'type': 'generation_progress', 'progress': progress_data['progress'], 'status': progress_data['status']})}\n\n"
                    last_progress = progress_data

                    if progress_data.get('progress', 0) >= 100:
                        yield f"data: {json.dumps({'type': 'generation_complete', 'message': 'Generation complete, closing connection'})}\n\n"
                        break

                # Session completed
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Session completed'})}\n\n"
                    break

                # Detect changes
                status_changed = session.status != last_status
                question_changed = (
                    session.current_round != last_round
                    or session.current_question != last_question
                )

                if question_changed:
                    last_answer_count = -1

                # Check answer count
                current_answer_count = -1
                current_q = None
                if session.current_round and session.current_question:
                    from ..pub_quiz_models import TeamAnswer
                    current_q = QuizQuestion.objects.filter(
                        session=session,
                        round_number=session.current_round,
                        question_number=session.current_question,
                    ).first()
                    if current_q:
                        current_answer_count = TeamAnswer.objects.filter(question=current_q).count()

                answers_changed = current_answer_count != last_answer_count

                current_time = timezone.now()
                time_diff = (current_time - last_update_time).total_seconds()
                should_send = status_changed or question_changed or answers_changed or time_diff >= 10

                if should_send:
                    host_data = PubQuizService.get_host_update_data(session)
                    host_data['timestamp'] = current_time.isoformat()
                    yield f"data: {json.dumps(host_data)}\n\n"

                    last_update_time = current_time
                    last_status = session.status
                    last_round = session.current_round
                    last_question = session.current_question
                    last_answer_count = current_answer_count

                # Data keepalive every 30s
                if (current_time - last_keepalive).total_seconds() >= 30:
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': current_time.isoformat()})}\n\n"
                    last_keepalive = current_time

                yield ": heartbeat\n\n"
                time.sleep(1)

            except Exception as e:
                logger.error(f"[SSE] Host stream error for session {session_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
