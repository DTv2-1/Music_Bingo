"""
Blind Date Pub Game — Game Control Views

Endpoints:
- start_game: POST — shuffle players, begin rounds
- host_data: GET — full game state for host dashboard
- next_step: POST — advance to next question or next player
- submit_answer: POST — player submits an answer to current question
- evaluate_answers: POST — AI ranks answers by humor, picks funniest
- end_game: POST — mark game as completed
- like_player: POST — player likes another player (for optional meetup)
- get_matches: GET — check mutual likes
"""

import os
import json
import logging
import random

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from ..blind_date_models import (
    BlindDateSession, BlindDatePlayer, BlindDateAnswer, BlindDateLike
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_game(request, session_id):
    """
    Start the game: shuffle player order, set status to in_progress.
    Only works from 'lobby' status with enough players.
    """
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    if session.status != 'lobby':
        return Response({'error': 'Game already started'}, status=400)

    if not session.can_start:
        return Response({
            'error': f'Need at least {session.min_players} players ({session.player_count} joined)'
        }, status=400)

    # Shuffle player order
    players = list(session.players.all())
    random.shuffle(players)
    for idx, player in enumerate(players):
        player.queue_order = idx
        player.save(update_fields=['queue_order'])

    session.status = 'in_progress'
    session.current_player_idx = 0
    session.current_question_idx = 0
    session.started_at = timezone.now()
    session.save()

    logger.info(f"[BlindDate] Game started: {session.session_code} with {len(players)} players")

    return Response({
        'status': 'in_progress',
        'player_order': [p.nickname for p in players],
        'total_players': len(players),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def host_data(request, session_id):
    """Full game state for the host dashboard."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    players = list(session.players.order_by('queue_order'))

    current_player = None
    current_question_text = None
    if session.status == 'in_progress' and players:
        idx = min(session.current_player_idx, len(players) - 1)
        cp = players[idx]
        current_player = {
            'id': cp.id,
            'nickname': cp.nickname,
            'description': cp.description,
            'questions': cp.questions,
            'current_question_idx': session.current_question_idx,
        }
        qs = cp.questions
        if session.current_question_idx < len(qs):
            current_question_text = qs[session.current_question_idx]

    # Count answers for current question
    answers_count = 0
    if current_player:
        answers_count = BlindDateAnswer.objects.filter(
            question_player_id=current_player['id'],
            question_index=session.current_question_idx,
        ).count()

    return Response({
        'session_code': session.session_code,
        'venue_name': session.venue_name,
        'host_name': session.host_name,
        'status': session.status,
        'player_count': session.player_count,
        'min_players': session.min_players,
        'can_start': session.can_start,
        'answer_time_seconds': session.answer_time_seconds,
        'current_player_idx': session.current_player_idx,
        'current_question_idx': session.current_question_idx,
        'current_player': current_player,
        'current_question_text': current_question_text,
        'answers_received': answers_count,
        'players': [{
            'id': p.id,
            'nickname': p.nickname,
            'description': p.description,
            'round_completed': p.round_completed,
            'queue_order': p.queue_order,
        } for p in players],
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def next_step(request, session_id):
    """
    Advance the game:
    - If more questions for current player → next question
    - If no more questions → mark player round done, move to next player
    - If no more players → game completed
    """
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    if session.status != 'in_progress':
        return Response({'error': 'Game not in progress'}, status=400)

    players = list(session.players.order_by('queue_order'))
    if not players:
        return Response({'error': 'No players'}, status=400)

    idx = session.current_player_idx
    current_player = players[min(idx, len(players) - 1)]
    questions = current_player.questions
    q_idx = session.current_question_idx

    if q_idx + 1 < len(questions):
        # More questions for this player
        session.current_question_idx = q_idx + 1
        session.save(update_fields=['current_question_idx'])
        action = 'next_question'
    else:
        # Player's round done
        current_player.round_completed = True
        current_player.save(update_fields=['round_completed'])

        if idx + 1 < len(players):
            # Next player
            session.current_player_idx = idx + 1
            session.current_question_idx = 0
            session.save(update_fields=['current_player_idx', 'current_question_idx'])
            action = 'next_player'
        else:
            # Game over
            session.status = 'completed'
            session.save(update_fields=['status'])
            action = 'game_completed'

    # Build response
    new_player = None
    new_question = None
    if action in ('next_question', 'next_player') and session.status == 'in_progress':
        np = players[min(session.current_player_idx, len(players) - 1)]
        qs = np.questions
        new_player = {'id': np.id, 'nickname': np.nickname, 'description': np.description}
        if session.current_question_idx < len(qs):
            new_question = qs[session.current_question_idx]

    return Response({
        'action': action,
        'current_player_idx': session.current_player_idx,
        'current_question_idx': session.current_question_idx,
        'current_player': new_player,
        'current_question': new_question,
        'status': session.status,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_answer(request, session_id):
    """Player submits an answer to the current question."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    token = request.data.get('token', '')
    answer_text = request.data.get('answer', '').strip()[:500]

    if not token or not answer_text:
        return Response({'error': 'Token and answer required'}, status=400)

    try:
        answerer = BlindDatePlayer.objects.get(session_token=token, session=session)
    except BlindDatePlayer.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    # Get current question player
    players = list(session.players.order_by('queue_order'))
    if not players:
        return Response({'error': 'No players'}, status=400)

    idx = min(session.current_player_idx, len(players) - 1)
    question_player = players[idx]

    # Can't answer your own question
    if answerer.id == question_player.id:
        return Response({'error': 'Cannot answer your own question'}, status=400)

    # Create or update answer
    answer, created = BlindDateAnswer.objects.update_or_create(
        question_player=question_player,
        question_index=session.current_question_idx,
        answerer=answerer,
        defaults={'answer_text': answer_text},
    )

    return Response({
        'status': 'submitted' if created else 'updated',
        'answer_id': answer.id,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def evaluate_answers(request, session_id):
    """
    AI evaluates answers for the current question.
    Ranks by humor, picks top N, adds sarcastic commentary.
    """
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    player_id = request.data.get('player_id')
    question_idx = request.data.get('question_index', session.current_question_idx)

    try:
        question_player = BlindDatePlayer.objects.get(id=player_id, session=session)
    except BlindDatePlayer.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    questions = question_player.questions
    if question_idx >= len(questions):
        return Response({'error': 'Invalid question index'}, status=400)

    question_text = questions[question_idx]
    answers = BlindDateAnswer.objects.filter(
        question_player=question_player,
        question_index=question_idx,
    )

    if not answers.exists():
        return Response({'error': 'No answers to evaluate'}, status=400)

    # Try AI evaluation
    answers_data = [{'id': a.id, 'text': a.answer_text, 'from': a.answerer.nickname} for a in answers]

    try:
        ranked = _ai_rank_answers(question_text, answers_data)
        # Update answers with AI scores
        for item in ranked:
            BlindDateAnswer.objects.filter(id=item['id']).update(
                humor_score=item.get('humor_score', 5),
                ai_commentary=item.get('commentary', ''),
            )
    except Exception as e:
        logger.error(f"[BlindDate] AI evaluation failed: {e}")
        # Fallback: random scores
        for a in answers:
            a.humor_score = random.randint(3, 9)
            a.save(update_fields=['humor_score'])
        ranked = [{'id': a.id, 'text': a.answer_text, 'from': a.answerer.nickname,
                    'humor_score': a.humor_score, 'commentary': ''} for a in answers]

    # Sort by score descending
    ranked.sort(key=lambda x: x.get('humor_score', 0), reverse=True)

    top_n = ranked[:session.max_funny_shown]

    return Response({
        'question': question_text,
        'total_answers': len(ranked),
        'top_answers': top_n,
        'all_answers': ranked,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def like_player(request, session_id):
    """Player likes another player (opt-in for meetup)."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    token = request.data.get('token', '')
    to_player_id = request.data.get('to_player_id')

    try:
        from_player = BlindDatePlayer.objects.get(session_token=token, session=session)
        to_player = BlindDatePlayer.objects.get(id=to_player_id, session=session)
    except BlindDatePlayer.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    if from_player.id == to_player.id:
        return Response({'error': 'Cannot like yourself'}, status=400)

    BlindDateLike.objects.get_or_create(
        session=session, from_player=from_player, to_player=to_player
    )

    is_mutual = BlindDateLike.is_mutual(from_player, to_player)

    return Response({
        'liked': True,
        'is_mutual': is_mutual,
        'match_nickname': to_player.nickname if is_mutual else None,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_matches(request, session_id):
    """Get mutual matches for a player."""
    token = request.query_params.get('token', '')

    try:
        player = BlindDatePlayer.objects.get(session_token=token)
    except BlindDatePlayer.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    # Find mutual likes
    given = set(BlindDateLike.objects.filter(from_player=player).values_list('to_player_id', flat=True))
    received = set(BlindDateLike.objects.filter(to_player=player).values_list('from_player_id', flat=True))
    mutual_ids = given & received

    matches = BlindDatePlayer.objects.filter(id__in=mutual_ids)

    return Response({
        'matches': [{'id': m.id, 'nickname': m.nickname} for m in matches],
        'total_likes_given': len(given),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def end_game(request, session_id):
    """Force-end the game."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    session.status = 'completed'
    session.save(update_fields=['status'])

    return Response({'status': 'completed'})


# ============================================================
# AI HELPERS
# ============================================================

def _ai_rank_answers(question_text, answers_data):
    """Use OpenAI to rank answers by humor."""
    import openai

    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        raise Exception("OpenAI API key not configured")

    client = openai.OpenAI(api_key=api_key)

    answers_str = "\n".join([f"- [{a['from']}]: \"{a['text']}\"" for a in answers_data])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": (
                "You are Celia Slack, a sarcastic Liverpool DJ hosting a pub dating game. "
                "You evaluate answers for humor. Be witty and cheeky."
            )
        }, {
            "role": "user",
            "content": (
                f"Rate these answers to the question: \"{question_text}\"\n\n"
                f"{answers_str}\n\n"
                f"For each answer, provide:\n"
                f"1. humor_score (1-10)\n"
                f"2. A short sarcastic commentary (1-2 sentences)\n\n"
                f"Respond in JSON array format:\n"
                f'[{{"from": "nickname", "humor_score": 8, "commentary": "..."}}]'
            )
        }],
        temperature=0.9,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    # Map AI results back to answer IDs
    ranked = []
    if isinstance(result, dict):
        result = result.get('answers', result.get('results', []))

    for ai_item in result:
        for orig in answers_data:
            if orig['from'].lower() == ai_item.get('from', '').lower():
                ranked.append({
                    'id': orig['id'],
                    'text': orig['text'],
                    'from': orig['from'],
                    'humor_score': ai_item.get('humor_score', 5),
                    'commentary': ai_item.get('commentary', ''),
                })
                break

    # Add any answers not matched by AI
    ranked_ids = {r['id'] for r in ranked}
    for orig in answers_data:
        if orig['id'] not in ranked_ids:
            ranked.append({
                'id': orig['id'],
                'text': orig['text'],
                'from': orig['from'],
                'humor_score': 5,
                'commentary': '',
            })

    return ranked


def _get_session(session_identifier):
    """Get session by code or numeric ID."""
    try:
        return BlindDateSession.objects.get(session_code=session_identifier)
    except BlindDateSession.DoesNotExist:
        try:
            return BlindDateSession.objects.get(id=int(session_identifier))
        except (BlindDateSession.DoesNotExist, ValueError):
            return None
