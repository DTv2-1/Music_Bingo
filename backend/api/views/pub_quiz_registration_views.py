"""
Pub Quiz Registration Views — Team registration, QR codes, genre init

Endpoints:
- get_session_details: Session info + genres for registration page
- check_existing_team: Check if team already registered
- register_team: Register or update a team
- generate_qr_code: Generate QR code PNG for session
- initialize_quiz_genres: Seed the 50 quiz genres
"""

import logging
import qrcode
from io import BytesIO

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..pub_quiz_models import QuizTeam, QuizGenre, GenreVote
from ..pub_quiz_generator import initialize_genres_in_db
from ..utils.pub_quiz_helpers import get_session_by_code_or_id

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_session_details(request, session_id):
    """Session info + active genres for the registration page (accessed via QR)."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    genres = QuizGenre.objects.filter(is_active=True).order_by('order')

    return Response({
        'session': {
            'id': session.id,
            'venue_name': session.venue_name,
            'host_name': session.host_name,
            'status': session.status,
        },
        'genres': [{
            'id': g.id,
            'name': g.name,
            'icon': g.icon,
            'description': g.description,
        } for g in genres]
    })


@api_view(['GET'])
def check_existing_team(request, session_id):
    """Check if a team already exists in a session and return its data."""
    try:
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)

        team_name = request.GET.get('team_name', '')
        if not team_name:
            return Response({'exists': False})

        team = QuizTeam.objects.filter(session=session, team_name=team_name).first()

        if team:
            genre_votes = GenreVote.objects.filter(
                team=team
            ).order_by('priority').values_list('genre_id', flat=True)

            return Response({
                'exists': True,
                'team': {
                    'team_name': team.team_name,
                    'table_number': team.table_number,
                    'num_players': team.num_players,
                    'social_handle': team.social_handle,
                    'followed_social': team.followed_social,
                    'genre_votes': list(genre_votes),
                }
            })
        else:
            return Response({'exists': False})

    except Exception as e:
        return Response({'exists': False, 'error': str(e)})


@api_view(['POST'])
def register_team(request, session_id):
    """Register a new team or update an existing one."""
    try:
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)

        data = request.data
        team_name = data.get('team_name')

        existing_team = QuizTeam.objects.filter(session=session, team_name=team_name).first()

        if existing_team:
            team = existing_team
            team.table_number = data.get('table_number')
            team.num_players = data.get('num_players', 4)
            team.contact_email = data.get('contact_email', '')
            team.contact_phone = data.get('contact_phone', '')
            team.social_handle = data.get('social_handle', '')
            team.followed_social = data.get('followed_social', False)

            if team.followed_social and team.bonus_points == 0:
                team.bonus_points = 1

            team.save()
            GenreVote.objects.filter(team=team).delete()
            message = '¡Registro actualizado!'
        else:
            team = QuizTeam.objects.create(
                session=session,
                team_name=team_name,
                table_number=data.get('table_number'),
                num_players=data.get('num_players', 4),
                contact_email=data.get('contact_email', ''),
                contact_phone=data.get('contact_phone', ''),
                social_handle=data.get('social_handle', ''),
                followed_social=data.get('followed_social', False),
            )
            if team.followed_social:
                team.bonus_points = 1
                team.save()
            message = '¡Equipo registrado! Sigan @PerfectDJ para más diversión!'

        # Register genre votes (top 3-5)
        genre_votes = data.get('genre_votes', [])
        for i, genre_id in enumerate(genre_votes[:5], 1):
            try:
                genre = QuizGenre.objects.get(id=genre_id)
                GenreVote.objects.create(team=team, genre=genre, priority=i)
            except QuizGenre.DoesNotExist:
                pass

        logger.info(f"[REGISTER_TEAM] Team '{team.team_name}' registered (ID {team.id})")

        return Response({
            'success': True,
            'team_id': team.id,
            'team_name': team.team_name,
            'bonus_points': team.bonus_points,
            'message': message,
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"[REGISTER_TEAM] Error: {e}", exc_info=True)
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def generate_qr_code(request, session_id):
    """Generate a QR code PNG for team registration."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    registration_url = f"/pub-quiz/register/{session_id}"

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(registration_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_code_session_{session_id}.png"'
    return response


@api_view(['GET', 'POST'])
def initialize_quiz_genres(request):
    """Seed the 50 quiz genres in the database."""
    try:
        initialize_genres_in_db()
        count = QuizGenre.objects.count()
        return Response({
            'success': True,
            'message': f'{count} géneros inicializados correctamente'
        })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
