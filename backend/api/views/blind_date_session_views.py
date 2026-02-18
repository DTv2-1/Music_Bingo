"""
Blind Date Pub Game — Session & Registration Views

Endpoints:
- create_session: POST — create a new blind date game
- get_sessions: GET — list all sessions
- delete_session: DELETE — remove a session
- get_session_details: GET — public session info for player join page
- join_session: POST — player registers with nickname/description/questions
- get_player_data: GET — retrieve player data by session token
- seed_test_players: POST — generate 5 AI-created test players
"""

import os
import json
import logging
import random

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from ..blind_date_models import BlindDateSession, BlindDatePlayer

logger = logging.getLogger(__name__)


# ============================================================
# SESSION CRUD
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_sessions(request):
    """List all blind date sessions."""
    sessions = BlindDateSession.objects.all()[:50]
    data = [{
        'id': s.id,
        'session_code': s.session_code,
        'venue_name': s.venue_name,
        'host_name': s.host_name,
        'status': s.status,
        'player_count': s.player_count,
        'min_players': s.min_players,
        'can_start': s.can_start,
        'created_at': s.created_at.isoformat(),
    } for s in sessions]
    return Response({'sessions': data})


@api_view(['POST'])
@permission_classes([AllowAny])
def create_session(request):
    """Create a new blind date game session."""
    venue = request.data.get('venue_name', 'The Pub')
    host = request.data.get('host_name', 'Celia Slack')
    min_p = int(request.data.get('min_players', 5))
    answer_time = int(request.data.get('answer_time_seconds', 120))

    session = BlindDateSession.objects.create(
        venue_name=venue,
        host_name=host,
        min_players=min_p,
        answer_time_seconds=answer_time,
    )

    logger.info(f"[BlindDate] Session created: {session.session_code} @ {venue}")
    return Response({
        'id': session.id,
        'session_code': session.session_code,
        'venue_name': session.venue_name,
    }, status=201)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_session(request, session_id):
    """Delete a blind date session."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)
    session.delete()
    return Response({'status': 'deleted'})


# ============================================================
# PLAYER REGISTRATION
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_session_details(request, session_id):
    """Public session info for the join page."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    players = session.players.all()
    return Response({
        'session_code': session.session_code,
        'venue_name': session.venue_name,
        'host_name': session.host_name,
        'status': session.status,
        'player_count': session.player_count,
        'min_players': session.min_players,
        'can_start': session.can_start,
        'answer_time_seconds': session.answer_time_seconds,
        'players': [{'nickname': p.nickname, 'joined_at': p.joined_at.isoformat()} for p in players],
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def join_session(request, session_id):
    """Player joins a session with nickname, description, and up to 3 questions."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    if session.status not in ('lobby',):
        return Response({'error': 'Game already in progress'}, status=400)

    nickname = request.data.get('nickname', '').strip()
    description = request.data.get('description', '').strip()
    q1 = request.data.get('question_1', '').strip()[:200]
    q2 = request.data.get('question_2', '').strip()[:200]
    q3 = request.data.get('question_3', '').strip()[:200]

    if not nickname:
        return Response({'error': 'Nickname is required'}, status=400)
    if not description:
        return Response({'error': 'Description is required'}, status=400)
    if not q1:
        return Response({'error': 'At least one question is required'}, status=400)

    # Check duplicate nickname
    if session.players.filter(nickname__iexact=nickname).exists():
        return Response({'error': 'Nickname already taken'}, status=400)

    player = BlindDatePlayer.objects.create(
        session=session,
        nickname=nickname,
        description=description,
        question_1=q1,
        question_2=q2,
        question_3=q3,
    )

    logger.info(f"[BlindDate] Player joined: {nickname} → session {session.session_code}")

    return Response({
        'player_id': player.id,
        'nickname': player.nickname,
        'session_token': player.session_token,
        'session_code': session.session_code,
    }, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_player_data(request, session_id):
    """Get player info by session token (passed as query param)."""
    token = request.query_params.get('token', '')
    if not token:
        return Response({'error': 'Token required'}, status=400)

    try:
        player = BlindDatePlayer.objects.get(session_token=token)
    except BlindDatePlayer.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    # Include received answers if their round is done
    received = []
    if player.round_completed:
        for ans in player.received_answers.all():
            received.append({
                'question_index': ans.question_index,
                'answer_text': ans.answer_text,
                'humor_score': ans.humor_score,
                'ai_commentary': ans.ai_commentary,
                'answerer_nickname': ans.answerer.nickname,
            })

    return Response({
        'player_id': player.id,
        'nickname': player.nickname,
        'description': player.description,
        'questions': player.questions,
        'round_completed': player.round_completed,
        'received_answers': received,
    })


# ============================================================
# QR CODE
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def generate_qr_code(request, session_id):
    """Generate QR code PNG for a session join URL."""
    import qrcode
    from io import BytesIO
    from django.http import HttpResponse

    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    base_url = request.build_absolute_uri('/').rstrip('/')
    # Point to frontend join page
    join_url = f"{base_url}/blind-date/join/{session.session_code}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(join_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type='image/png')


# ============================================================
# SEED TEST PLAYERS (AI)
# ============================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def seed_test_players(request, session_id):
    """Generate 5 fictional contestants via OpenAI and register them."""
    session = _get_session(session_id)
    if not session:
        return Response({'error': 'Session not found'}, status=404)

    if session.status != 'lobby':
        return Response({'error': 'Can only add test players while in lobby'}, status=400)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return Response({'error': 'OPENAI_API_KEY not configured'}, status=500)

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        prompt = (
            "Generate 5 fictional, fun and diverse pub-goers for a Blind Date game. "
            "Each person should have a unique personality. "
            "Return a JSON object with a key \"players\" containing an array of 5 objects. "
            "Each object must have:\n"
            "- \"nickname\": a catchy, funny first name or alias (max 20 chars)\n"
            "- \"description\": a short, cheeky self-description for a dating game (1-2 sentences, max 150 chars)\n"
            "- \"question_1\": a fun, flirty or quirky dating question they want to ask\n"
            "- \"question_2\": another creative dating question\n"
            "- \"question_3\": a third original dating question\n\n"
            "Make the personalities varied: shy, outgoing, nerdy, adventurous, etc. "
            "Keep the tone playful and pub-appropriate. "
            "Return ONLY valid JSON, no extra text."
        )

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.9,
        )

        data = json.loads(resp.choices[0].message.content)
        players_data = data.get('players', [])

        if not players_data or len(players_data) < 5:
            return Response({'error': 'AI returned insufficient player data'}, status=500)

        created = []
        for p in players_data[:5]:
            nickname = p.get('nickname', 'TestPlayer')[:20]
            # Ensure unique nickname in session
            base = nickname
            counter = 1
            while BlindDatePlayer.objects.filter(session=session, nickname=nickname).exists():
                nickname = f"{base}{counter}"
                counter += 1

            player = BlindDatePlayer.objects.create(
                session=session,
                nickname=nickname,
                description=p.get('description', 'A mystery contestant')[:200],
                question_1=p.get('question_1', 'What is your idea of a perfect date?'),
                question_2=p.get('question_2', 'What makes you laugh?'),
                question_3=p.get('question_3', 'What is your hidden talent?'),
            )
            created.append({
                'id': player.id,
                'nickname': player.nickname,
                'description': player.description,
                'questions': [player.question_1, player.question_2, player.question_3],
            })

        logger.info(f"Seeded {len(created)} test players in session {session.session_code}")
        return Response({'players': created, 'count': len(created)})

    except Exception as e:
        logger.error(f"Failed to generate test players: {e}")
        return Response({'error': f'AI generation failed: {str(e)}'}, status=500)


# ============================================================
# HELPERS
# ============================================================

def _get_session(session_identifier):
    """Get session by code or numeric ID."""
    try:
        return BlindDateSession.objects.get(session_code=session_identifier)
    except BlindDateSession.DoesNotExist:
        try:
            return BlindDateSession.objects.get(id=int(session_identifier))
        except (BlindDateSession.DoesNotExist, ValueError):
            return None
