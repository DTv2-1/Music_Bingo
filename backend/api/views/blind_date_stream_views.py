"""
Blind Date Pub Game — SSE Stream Views

Real-time Server-Sent Events for:
- Player stream: receives game state updates (new player, question, answers, game end)
- Host stream: receives join notifications, answer counts, status changes
"""

import json
import time
import logging

from django.http import StreamingHttpResponse
from django.utils import timezone

from ..blind_date_models import BlindDateSession, BlindDatePlayer, BlindDateAnswer

logger = logging.getLogger(__name__)


def player_stream(request, session_id):
    """SSE endpoint for players — real-time game updates."""

    def event_generator():
        session = _get_session(session_id)
        if not session:
            yield f'data: {json.dumps({"type": "error", "message": "Session not found"})}\n\n'
            return

        last_status = None
        last_player_count = 0
        last_position = None
        connection_start = timezone.now()

        yield f'data: {json.dumps({"type": "connected", "session_code": session.session_code})}\n\n'

        while True:
            try:
                elapsed = (timezone.now() - connection_start).total_seconds()
                if elapsed > 600:  # 10 min timeout
                    yield f'data: {json.dumps({"type": "timeout"})}\n\n'
                    break

                session.refresh_from_db()

                # Status change
                if session.status != last_status:
                    data = {
                        'type': 'status_change',
                        'status': session.status,
                    }

                    if session.status == 'in_progress':
                        players = list(session.players.order_by('queue_order'))
                        if players:
                            idx = min(session.current_player_idx, len(players) - 1)
                            cp = players[idx]
                            qs = cp.questions
                            data['current_player'] = {
                                'nickname': cp.nickname,
                                'description': cp.description,
                                'id': cp.id,
                            }
                            if session.current_question_idx < len(qs):
                                data['current_question'] = qs[session.current_question_idx]
                                data['current_question_idx'] = session.current_question_idx
                            data['answer_time'] = session.answer_time_seconds

                    if session.status == 'completed':
                        data['type'] = 'game_ended'

                    yield f'data: {json.dumps(data)}\n\n'
                    last_status = session.status

                # New player joined (lobby)
                if session.status == 'lobby':
                    count = session.player_count
                    if count != last_player_count:
                        latest = session.players.order_by('-joined_at').first()
                        yield f'data: {json.dumps({"type": "player_joined", "nickname": latest.nickname if latest else "", "player_count": count, "can_start": session.can_start})}\n\n'
                        last_player_count = count

                # Question/player position changed
                if session.status == 'in_progress':
                    pos = f"{session.current_player_idx}.{session.current_question_idx}"
                    if pos != last_position:
                        players = list(session.players.order_by('queue_order'))
                        if players:
                            idx = min(session.current_player_idx, len(players) - 1)
                            cp = players[idx]
                            qs = cp.questions
                            q_text = qs[session.current_question_idx] if session.current_question_idx < len(qs) else ''
                            yield f'data: {json.dumps({"type": "question_change", "current_player": {"nickname": cp.nickname, "description": cp.description, "id": cp.id}, "current_question": q_text, "current_question_idx": session.current_question_idx, "current_player_idx": session.current_player_idx, "answer_time": session.answer_time_seconds})}\n\n'
                        last_position = pos

                # Keepalive
                time.sleep(1.5)
                yield f': keepalive\n\n'

            except Exception as e:
                logger.error(f"[BlindDate SSE] Player stream error: {e}")
                yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
                break

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def host_stream(request, session_id):
    """SSE endpoint for host — answer counts, player joins, status."""

    def event_generator():
        session = _get_session(session_id)
        if not session:
            yield f'data: {json.dumps({"type": "error", "message": "Session not found"})}\n\n'
            return

        last_player_count = 0
        last_answer_count = 0
        last_position = None
        last_status = None
        connection_start = timezone.now()

        yield f'data: {json.dumps({"type": "connected"})}\n\n'

        while True:
            try:
                elapsed = (timezone.now() - connection_start).total_seconds()
                if elapsed > 600:
                    yield f'data: {json.dumps({"type": "timeout"})}\n\n'
                    break

                session.refresh_from_db()

                # Player count change
                count = session.player_count
                if count != last_player_count:
                    latest = session.players.order_by('-joined_at').first()
                    yield f'data: {json.dumps({"type": "player_joined", "nickname": latest.nickname if latest else "", "player_count": count, "can_start": session.can_start})}\n\n'
                    last_player_count = count

                # Status change
                if session.status != last_status:
                    yield f'data: {json.dumps({"type": "status_change", "status": session.status})}\n\n'
                    last_status = session.status

                # Answer count for current question
                if session.status == 'in_progress':
                    players = list(session.players.order_by('queue_order'))
                    if players:
                        idx = min(session.current_player_idx, len(players) - 1)
                        cp = players[idx]
                        ans_count = BlindDateAnswer.objects.filter(
                            question_player=cp,
                            question_index=session.current_question_idx,
                        ).count()
                        if ans_count != last_answer_count:
                            yield f'data: {json.dumps({"type": "answer_update", "answers_received": ans_count})}\n\n'
                            last_answer_count = ans_count

                    pos = f"{session.current_player_idx}.{session.current_question_idx}"
                    if pos != last_position:
                        last_position = pos
                        last_answer_count = 0  # Reset on new question

                time.sleep(1.5)
                yield f': keepalive\n\n'

            except Exception as e:
                logger.error(f"[BlindDate SSE] Host stream error: {e}")
                yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
                break

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def _get_session(session_identifier):
    try:
        return BlindDateSession.objects.get(session_code=session_identifier)
    except BlindDateSession.DoesNotExist:
        try:
            return BlindDateSession.objects.get(id=int(session_identifier))
        except (BlindDateSession.DoesNotExist, ValueError):
            return None
