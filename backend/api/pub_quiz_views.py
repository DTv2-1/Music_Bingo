"""
Vistas y API para el sistema Pub Quiz
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import qrcode
from io import BytesIO
import base64

from .pub_quiz_models import (
    PubQuizSession, QuizTeam, QuizGenre, QuizQuestion,
    QuizRound, TeamAnswer, BuzzerDevice, GenreVote
)
from .pub_quiz_generator import PubQuizGenerator, initialize_genres_in_db


# ============================================================================
# VISTAS DE ADMINISTRACIÓN
# ============================================================================

@api_view(['GET'])
def get_sessions(request):
    """Obtiene las sesiones de Pub Quiz más recientes"""
    sessions = PubQuizSession.objects.all().order_by('-date')[:10]
    data = [{
        'id': s.id,
        'venue_name': s.venue_name,
        'date': s.date,
        'status': s.status,
        'team_count': s.teams.count()
    } for s in sessions]
    return Response(data)


@api_view(['POST'])
def create_quiz_session(request):
    """Crea una nueva sesión de Pub Quiz"""
    try:
        data = request.data
        
        session = PubQuizSession.objects.create(
            venue_name=data.get('venue_name', 'The Pub'),
            host_name=data.get('host_name', 'Perfect DJ'),
            total_rounds=data.get('total_rounds', 6),
            questions_per_round=data.get('questions_per_round', 10),
            duration_minutes=data.get('duration_minutes', 120),
            status='registration',
        )
        
        return Response({
            'success': True,
            'session_id': session.id,
            'session': {
                'id': session.id,
                'venue_name': session.venue_name,
                'status': session.status,
                'total_rounds': session.total_rounds,
                'questions_per_round': session.questions_per_round,
            }
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# REGISTRO DE EQUIPOS Y QR
# ============================================================================

@api_view(['GET'])
def get_session_details(request, session_id):
    """Página de registro para equipos (acceso vía QR)"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    genres = QuizGenre.objects.filter(is_active=True).order_by('order')
    
    return Response({
        'session': {
            'id': session.id,
            'venue_name': session.venue_name,
            'host_name': session.host_name,
            'status': session.status
        },
        'genres': [{
            'id': g.id,
            'name': g.name,
            'icon': g.icon,
            'description': g.description
        } for g in genres]
    })


@api_view(['POST'])
def register_team(request, session_id):
    """Registra un nuevo equipo en la sesión"""
    try:
        session = get_object_or_404(PubQuizSession, id=session_id)
        data = request.data
        
        # Crear equipo
        team = QuizTeam.objects.create(
            session=session,
            team_name=data.get('team_name'),
            table_number=data.get('table_number'),
            num_players=data.get('num_players', 4),
            contact_email=data.get('contact_email', ''),
            contact_phone=data.get('contact_phone', ''),
            social_handle=data.get('social_handle', ''),
            followed_social=data.get('followed_social', False),
        )
        
        # Bonus por seguir redes sociales
        if team.followed_social:
            team.bonus_points = 1
            team.save()
        
        # Registrar votos de géneros (top 3-5)
        genre_votes = data.get('genre_votes', [])
        for i, genre_id in enumerate(genre_votes[:5], 1):
            try:
                genre = QuizGenre.objects.get(id=genre_id)
                GenreVote.objects.create(
                    team=team,
                    genre=genre,
                    priority=i
                )
            except QuizGenre.DoesNotExist:
                pass
        
        return Response({
            'success': True,
            'team_id': team.id,
            'team_name': team.team_name,
            'bonus_points': team.bonus_points,
            'message': '¡Equipo registrado! Sigan @PerfectDJ para más diversión!'
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def generate_qr_code(request, session_id):
    """Genera código QR para registro del equipo"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    # Registration URL should point to the frontend
    registration_url = f"/pub-quiz/register/{session_id}"
    
    # Generar QR
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(registration_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64 o retornar imagen
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_code_session_{session_id}.png"'
    
    return response


# ============================================================================
# GESTIÓN DE PREGUNTAS Y RONDAS
# ============================================================================

@api_view(['POST'])
def generate_quiz_questions(request, session_id):
    """Genera preguntas para el quiz basado en votación de géneros"""
    try:
        session = get_object_or_404(PubQuizSession, id=session_id)
        
        # Contar votos por género
        genre_votes = GenreVote.objects.filter(team__session=session).values('genre_id').annotate(
            vote_count=Count('genre_id')
        ).order_by('-vote_count')
        
        votes_dict = {v['genre_id']: v['vote_count'] for v in genre_votes}
        
        # Usar generador para seleccionar géneros
        generator = PubQuizGenerator()
        selected_genres = generator.select_genres_by_votes(votes_dict, session.total_rounds)
        
        # Crear estructura de rondas
        structure = generator.create_quiz_structure(
            selected_genres,
            questions_per_round=session.questions_per_round,
            include_halftime=True,
            include_buzzer_round=False
        )
        
        # Crear rondas en DB
        for round_data in structure['rounds']:
            genre = QuizGenre.objects.get(name=round_data['genre']['name'])
            
            quiz_round = QuizRound.objects.create(
                session=session,
                round_number=round_data['round_number'],
                genre=genre,
                round_name=round_data['round_name'],
                is_buzzer_round=round_data['is_buzzer_round'],
                is_halftime_before=round_data['is_halftime_before'],
            )
            
            # Aquí iría la integración con IA para generar preguntas reales
            # Por ahora, usar samples
            sample_questions = generator.generate_sample_questions(
                genre.name, 
                round_data['questions_per_round']
            )
            
            for q_data in sample_questions:
                QuizQuestion.objects.create(
                    session=session,
                    genre=genre,
                    round_number=round_data['round_number'],
                    question_number=q_data['question_number'],
                    question_text=q_data['question'],
                    correct_answer=q_data['answer'],
                    alternative_answers=q_data.get('alternative_answers', []),
                    difficulty=q_data.get('difficulty', 'medium'),
                    fun_fact=q_data.get('fun_fact', ''),
                    hints=q_data.get('hints', ''),
                )
        
        # Actualizar estado de sesión
        session.status = 'ready'
        session.save()
        
        # Agregar géneros seleccionados a la sesión
        for genre_data in selected_genres:
            genre = QuizGenre.objects.get(name=genre_data['name'])
            session.selected_genres.add(genre)
        
        return Response({
            'success': True,
            'message': 'Quiz generado exitosamente',
            'structure': structure,
            'selected_genres': [g['name'] for g in selected_genres]
        })
    
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# CONTROL DEL QUIZ EN VIVO
# ============================================================================

@api_view(['GET'])
def quiz_host_data(request, session_id):
    """Obtiene datos para la vista del host"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    teams = session.teams.all().order_by('-total_score')
    rounds = session.rounds.all()
    
    return Response({
        'session': {
            'id': session.id,
            'venue_name': session.venue_name,
            'status': session.status,
            'current_round': session.current_round,
            'current_question': session.current_question,
        },
        'teams': [{
            'id': t.id,
            'team_name': t.team_name,
            'total_score': t.total_score,
            'bonus_points': t.bonus_points
        } for t in teams],
        'rounds': [{
            'round_number': r.round_number,
            'round_name': r.round_name,
            'is_completed': r.is_completed
        } for r in rounds],
    })


@api_view(['POST'])
def start_quiz(request, session_id):
    """Inicia el quiz"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    session.status = 'in_progress'
    session.current_round = 1
    session.current_question = 1
    session.save()
    
    # Marcar primera ronda como iniciada
    first_round = session.rounds.filter(round_number=1).first()
    if first_round:
        first_round.started_at = timezone.now()
        first_round.save()
    
    return Response({'success': True, 'status': 'in_progress'})


@api_view(['POST'])
def next_question(request, session_id):
    """Avanza a la siguiente pregunta"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    
    total_questions_in_round = session.questions_per_round
    
    if session.current_question < total_questions_in_round:
        session.current_question += 1
    else:
        # Siguiente ronda
        current_round = session.rounds.filter(round_number=session.current_round).first()
        if current_round:
            current_round.is_completed = True
            current_round.completed_at = timezone.now()
            current_round.save()
        
        if session.current_round < session.total_rounds:
            session.current_round += 1
            session.current_question = 1
            
            # Verificar si es halftime
            next_round = session.rounds.filter(round_number=session.current_round).first()
            if next_round and next_round.is_halftime_before:
                session.status = 'halftime'
            
            if next_round:
                next_round.started_at = timezone.now()
                next_round.save()
        else:
            session.status = 'completed'
    
    session.save()
    
    return Response({
        'success': True,
        'current_round': session.current_round,
        'current_question': session.current_question,
        'status': session.status
    })


@api_view(['GET'])
def get_current_question(request, session_id):
    """Obtiene la pregunta actual"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    
    question = QuizQuestion.objects.filter(
        session=session,
        round_number=session.current_round,
        question_number=session.current_question
    ).first()
    
    if not question:
        return Response({'success': False, 'error': 'No question found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Obtener respuestas/buzzes para esta pregunta
    answers = []
    team_answers = TeamAnswer.objects.filter(question=question).select_related('team').order_by('buzz_order', 'submitted_at')
    
    for ans in team_answers:
        answers.append({
            'team_id': ans.team.id,
            'team_name': ans.team.team_name,
            'is_correct': ans.is_correct,
            'buzz_order': ans.buzz_order,
            'buzz_time': ans.buzz_timestamp.isoformat() if ans.buzz_timestamp else None,
            'points': ans.points_awarded
        })

    return Response({
        'success': True,
        'question': {
            'id': question.id,
            'text': question.question_text,
            'answer': question.correct_answer if session.status == 'revealing_answer' else None,
            'fun_fact': question.fun_fact if session.status == 'revealing_answer' else None,
            'round': question.round_number,
            'number': question.question_number,
            'points': question.points,
            'type': question.question_type,
            'hints': question.hints,
            'is_last': (question.question_number == session.questions_per_round) # Assuming total_questions means questions_per_round for the current round
        },
        'session_status': session.status,
        'answers': answers, # Lista de equipos que han respondido/buzzado
        'team_count': session.teams.count(),
        'answers_count': team_answers.count()
    })


@api_view(['GET'])
def get_question_answer(request, question_id):
    """Obtiene la respuesta de una pregunta"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    
    return Response({
        'success': True,
        'answer': question.correct_answer,
        'fun_fact': question.fun_fact
    })


from django.db import transaction
from django.utils import timezone

@api_view(['POST'])
def submit_answer(request, question_id):
    """Registra la respuesta de un equipo"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    team_id = request.data.get('team_id')
    team = get_object_or_404(QuizTeam, id=team_id)
    answer_text = request.data.get('answer', '')
    
    # Verificar si ya respondió (para evitar duplicados)
    ans, created = TeamAnswer.objects.get_or_create(
        team=team,
        question=question,
        defaults={'answer_text': answer_text}
    )
    
    if not created:
        ans.answer_text = answer_text
        ans.save()
        
    return Response({
        'success': True,
        'message': 'Answer submitted successfully'
    })


@api_view(['POST'])
def record_buzz(request, question_id):
    """Registra un 'buzz' (primero en presionar)"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    team_id = request.data.get('team_id')
    team = get_object_or_404(QuizTeam, id=team_id)
    
    with transaction.atomic():
        # Ver si ya buzzó
        ans, created = TeamAnswer.objects.get_or_create(
            team=team,
            question=question
        )
        
        if ans.buzz_timestamp is None:
            # Calcular orden
            order = TeamAnswer.objects.filter(question=question).exclude(buzz_timestamp=None).count() + 1
            ans.buzz_timestamp = timezone.now()
            ans.buzz_order = order
            ans.save()
            
            return Response({
                'success': True,
                'order': order,
                'message': f'Buzzed! You are #{order}'
            })
        else:
            return Response({
                'success': True,
                'order': ans.buzz_order,
                'message': 'Already buzzed'
            })


# ============================================================================
# LEADERBOARD Y ESTADÍSTICAS
# ============================================================================

@api_view(['GET'])
def get_leaderboard(request, session_id):
    """Obtiene el ranking actual de equipos"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    teams = session.teams.all().order_by('-total_score', '-bonus_points', 'team_name')
    
    leaderboard = []
    for i, team in enumerate(teams, 1):
        leaderboard.append({
            'position': i,
            'team_name': team.team_name,
            'table_number': team.table_number,
            'total_score': team.total_score,
            'bonus_points': team.bonus_points,
            'final_score': team.final_score,
            'social_handle': team.social_handle,
        })
    
    return Response({
        'success': True,
        'leaderboard': leaderboard,
        'total_teams': len(leaderboard)
    })


@api_view(['GET'])
def get_session_stats(request, session_id):
    """Estadísticas de la sesión"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    
    # Resumen de votos por género
    votes = GenreVote.objects.filter(team__session=session).values('genre__name').annotate(count=Count('id')).order_by('-count')
    genre_votes_summary = {item['genre__name']: item['count'] for item in votes}

    stats = {
        'total_teams': session.teams.count(),
        'total_players': sum(team.num_players for team in session.teams.all()),
        'social_followers': session.teams.filter(followed_social=True).count(),
        'current_round': session.current_round,
        'total_rounds': session.total_rounds,
        'progress_percent': (session.current_round / session.total_rounds * 100) if session.total_rounds > 0 else 0,
        'status': session.status,
        'selected_genres': [g.name for g in session.selected_genres.all()],
        'genre_votes_summary': genre_votes_summary,
    }
    
    return Response({'success': True, 'stats': stats})


# ============================================================================
# INICIALIZACIÓN
# ============================================================================

@api_view(['POST'])
def award_points(request, team_id):
    """Otorga o resta puntos a un equipo"""
    try:
        team = get_object_or_404(QuizTeam, id=team_id)
        points = request.data.get('points', 1)
        
        team.total_score += points
        team.save()
        
        return Response({
            'success': True,
            'new_score': team.total_score,
            'message': f'Points updated for {team.team_name}'
        })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def initialize_quiz_genres(request):
    """Endpoint para inicializar los 50 géneros"""
    try:
        initialize_genres_in_db()
        count = QuizGenre.objects.count()
        return Response({
            'success': True,
            'message': f'{count} géneros inicializados correctamente'
        })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
