"""
Vistas y API para el sistema Pub Quiz
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json
import os
import qrcode
from io import BytesIO
import base64
import time
import logging

from .pub_quiz_models import (
    PubQuizSession, QuizTeam, QuizGenre, QuizQuestion,
    QuizRound, TeamAnswer, BuzzerDevice, GenreVote
)
from .pub_quiz_generator import PubQuizGenerator, initialize_genres_in_db

logger = logging.getLogger(__name__)


# ============================================================================
# VISTAS DE ADMINISTRACIÓN
# ============================================================================

@api_view(['GET'])
def get_sessions(request):
    """Obtiene las sesiones de Pub Quiz con filtros opcionales"""
    status_filter = request.GET.get('status', None)
    
    sessions = PubQuizSession.objects.all()
    
    # Filtrar por status si se proporciona
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    sessions = sessions.order_by('-date', '-id')[:20]
    
    data = []
    for s in sessions:
        team_count = s.teams.count()
        question_count = QuizQuestion.objects.filter(session=s).count()
        
        data.append({
            'id': s.id,
            'venue_name': s.venue_name,
            'host_name': s.host_name,
            'date': s.date.isoformat(),
            'status': s.status,
            'team_count': team_count,
            'total_rounds': s.total_rounds,
            'current_round': s.current_round,
            'current_question': s.current_question,
            'questions_per_round': s.questions_per_round,
            'question_count': question_count,
            'duration_minutes': s.duration_minutes,
        })
    
    return Response({'success': True, 'sessions': data})


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
        
        # Asegurarse de que los géneros estén inicializados
        if QuizGenre.objects.count() == 0:
            initialize_genres_in_db()
        
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


@api_view(['GET'])
def check_existing_team(request, session_id):
    """Verifica si un equipo ya existe en la sesión y devuelve sus datos"""
    try:
        session = get_object_or_404(PubQuizSession, id=session_id)
        team_name = request.GET.get('team_name', '')
        
        if not team_name:
            return Response({'exists': False})
        
        team = QuizTeam.objects.filter(session=session, team_name=team_name).first()
        
        if team:
            # Obtener votos de géneros
            genre_votes = GenreVote.objects.filter(team=team).order_by('priority').values_list('genre_id', flat=True)
            
            return Response({
                'exists': True,
                'team': {
                    'team_name': team.team_name,
                    'table_number': team.table_number,
                    'num_players': team.num_players,
                    'social_handle': team.social_handle,
                    'followed_social': team.followed_social,
                    'genre_votes': list(genre_votes)
                }
            })
        else:
            return Response({'exists': False})
            
    except Exception as e:
        return Response({'exists': False, 'error': str(e)})


@api_view(['POST'])
def register_team(request, session_id):
    """Registra un nuevo equipo en la sesión o actualiza uno existente"""
    try:
        session = get_object_or_404(PubQuizSession, id=session_id)
        data = request.data
        team_name = data.get('team_name')
        
        # Buscar si ya existe un equipo con este nombre en esta sesión
        existing_team = QuizTeam.objects.filter(session=session, team_name=team_name).first()
        
        if existing_team:
            # Actualizar equipo existente
            team = existing_team
            team.table_number = data.get('table_number')
            team.num_players = data.get('num_players', 4)
            team.contact_email = data.get('contact_email', '')
            team.contact_phone = data.get('contact_phone', '')
            team.social_handle = data.get('social_handle', '')
            team.followed_social = data.get('followed_social', False)
            
            # Actualizar bonus si ahora sigue redes sociales
            if team.followed_social and team.bonus_points == 0:
                team.bonus_points = 1
            
            team.save()
            
            # Eliminar votos anteriores y crear nuevos
            GenreVote.objects.filter(team=team).delete()
            message = '¡Registro actualizado!'
        else:
            # Crear nuevo equipo
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
            
            # Bonus por seguir redes sociales
            if team.followed_social:
                team.bonus_points = 1
                team.save()
            
            message = '¡Equipo registrado! Sigan @PerfectDJ para más diversión!'
        
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
            'message': message
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
    from django.core.cache import cache
    
    try:
        session = get_object_or_404(PubQuizSession, id=session_id)
        
        # Initialize progress
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 0, 'status': 'starting'}, 300)
        
        # Get question type preferences from request body (DRF parses automatically)
        include_mc = request.data.get('include_multiple_choice', True)
        include_written = request.data.get('include_written', True)
        
        # Calculate ratios
        question_types = {}
        if include_mc and include_written:
            question_types = {'multiple_choice': 0.7, 'written': 0.3}
        elif include_mc:
            question_types = {'multiple_choice': 1.0, 'written': 0.0}
        elif include_written:
            question_types = {'multiple_choice': 0.0, 'written': 1.0}
        else:
            question_types = {'multiple_choice': 0.7, 'written': 0.3}
        
        # Contar votos por género
        genre_votes = GenreVote.objects.filter(team__session=session).values('genre_id').annotate(
            vote_count=Count('genre_id')
        ).order_by('-vote_count')
        
        votes_dict = {v['genre_id']: v['vote_count'] for v in genre_votes}
        
        # Usar generador para seleccionar géneros
        generator = PubQuizGenerator()
        selected_genres = generator.select_genres_by_votes(votes_dict, session.total_rounds)
        
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 10, 'status': 'Selecting genres...'}, 300)
        
        # Crear estructura de rondas
        structure = generator.create_quiz_structure(
            selected_genres,
            questions_per_round=session.questions_per_round,
            include_halftime=True,
            include_buzzer_round=False
        )
        
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 20, 'status': 'Creating quiz structure...'}, 300)
        
        # Crear rondas en DB primero (sin preguntas)
        total_rounds = len(structure['rounds'])
        rounds_to_generate = []
        
        for idx, round_data in enumerate(structure['rounds']):
            genre = QuizGenre.objects.get(name=round_data['genre']['name'])
            
            quiz_round = QuizRound.objects.create(
                session=session,
                round_number=round_data['round_number'],
                genre=genre,
                round_name=round_data['round_name'],
                is_buzzer_round=round_data['is_buzzer_round'],
                is_halftime_before=round_data['is_halftime_before'],
            )
            
            rounds_to_generate.append({
                'round_number': round_data['round_number'],
                'genre_name': genre.name,
                'genre_obj': genre,
                'questions_per_round': round_data['questions_per_round']
            })
        
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 30, 'status': 'Generating all questions (this may take 1-2 minutes)...'}, 300)
        
        # Generar todas las preguntas en paralelo usando threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def generate_round_questions(round_info):
            """Generate questions for a single round"""
            return {
                'round_number': round_info['round_number'],
                'genre_obj': round_info['genre_obj'],
                'questions': generator.generate_sample_questions(
                    round_info['genre_name'],
                    round_info['questions_per_round'],
                    question_types=question_types
                )
            }
        
        # Generate questions in parallel (max 4 concurrent API calls)
        all_round_questions = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_round = {executor.submit(generate_round_questions, round_info): round_info for round_info in rounds_to_generate}
            
            for idx, future in enumerate(as_completed(future_to_round)):
                result = future.result()
                all_round_questions.append(result)
                
                # Update progress
                progress = 30 + int(((idx + 1) / total_rounds) * 60)
                cache.set(f'quiz_generation_progress_{session_id}', 
                         {'progress': progress, 'status': f'Generated {idx+1}/{total_rounds} rounds...'}, 300)
        
        # Sort by round number
        all_round_questions.sort(key=lambda x: x['round_number'])
        
        # Save all questions to database
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 92, 'status': 'Saving questions to database...'}, 300)
        
        for round_data in all_round_questions:
            for q_data in round_data['questions']:
                QuizQuestion.objects.create(
                    session=session,
                    genre=round_data['genre_obj'],
                    round_number=round_data['round_number'],
                    question_number=q_data['question_number'],
                    question_text=q_data['question'],
                    correct_answer=q_data['answer'],
                    alternative_answers=q_data.get('alternative_answers', []),
                    difficulty=q_data.get('difficulty', 'medium'),
                    question_type=q_data.get('question_type', 'written'),
                    options=q_data.get('options', {}),
                    correct_option=q_data.get('correct_option', ''),
                    fun_fact=q_data.get('fun_fact', ''),
                    hints=q_data.get('hints', ''),
                )
        
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 90, 'status': 'Finalizing quiz...'}, 300)
        
        # Actualizar estado de sesión
        session.status = 'ready'
        session.save()
        
        # Agregar géneros seleccionados a la sesión
        for genre_data in selected_genres:
            genre = QuizGenre.objects.get(name=genre_data['name'])
            session.selected_genres.add(genre)
        
        cache.set(f'quiz_generation_progress_{session_id}', {'progress': 100, 'status': 'Complete!'}, 300)
        
        return Response({
            'success': True,
            'message': 'Quiz generado exitosamente',
            'structure': structure,
            'selected_genres': [g['name'] for g in selected_genres]
        })
    
    except Exception as e:
        cache.delete(f'quiz_generation_progress_{session_id}')
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
    
    # Mensaje de bienvenida
    team_count = session.teams.count()
    welcome_message = (
        f"Welcome to {session.venue_name}'s Pub Quiz! "
        f"We have {team_count} teams competing today. "
        f"Get ready for {session.total_rounds} rounds of trivia fun! "
        f"Good luck everyone!"
    )
    
    return Response({
        'success': True, 
        'status': 'in_progress',
        'welcome_message': welcome_message
    })


@api_view(['POST'])
def reset_quiz(request, session_id):
    """Reinicia completamente el quiz a su estado inicial"""
    session = get_object_or_404(PubQuizSession, id=session_id)
    
    # Borrar todas las respuestas
    TeamAnswer.objects.filter(team__session=session).delete()
    
    # Borrar todas las preguntas
    QuizQuestion.objects.filter(session=session).delete()
    
    # Borrar todas las rondas (esto permite regenerar preguntas)
    QuizRound.objects.filter(session=session).delete()
    
    # Resetear puntajes de equipos
    for team in session.teams.all():
        team.total_score = 0
        team.save()
    
    # Resetear sesión al estado inicial
    session.status = 'registration'
    session.current_round = 0
    session.current_question = 0
    session.save()
    
    return Response({
        'success': True,
        'message': 'Quiz reset successfully',
        'status': 'registration'
    })


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


def quiz_stream(request, session_id):
    """
    Server-Sent Events endpoint for real-time quiz updates
    Replaces polling with efficient push-based updates
    """
    def event_generator():
        """Generator that yields SSE-formatted messages"""
        session = get_object_or_404(PubQuizSession, id=session_id)
        last_round = session.current_round
        last_question = session.current_question
        last_status = session.status
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        # Send initial state immediately after connection
        initial_state_sent = False
        
        while True:
            try:
                # Refresh session from database
                session.refresh_from_db()
                
                # Check if session ended
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Quiz completed'})}\n\n"
                    break
                
                # Detect changes
                status_changed = session.status != last_status
                question_changed = (session.current_round != last_round or 
                                  session.current_question != last_question)
                
                # Send update on first iteration or when changes detected
                if not initial_state_sent or status_changed or question_changed:
                    # Status changed or new question
                    if session.status in ['in_progress', 'halftime', 'revealing_answer']:
                        question = QuizQuestion.objects.filter(
                            session=session,
                            round_number=session.current_round,
                            question_number=session.current_question
                        ).first()
                        
                        if question:
                            # Get team answers for this question
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
                            
                            data = {
                                'type': 'question_update',
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
                                    'options': question.options if question.question_type == 'multiple_choice' else None,
                                    'is_last': (question.question_number == session.questions_per_round)
                                },
                                'session_status': session.status,
                                'answers': answers,
                                'team_count': session.teams.count(),
                                'answers_count': len(answers)
                            }
                            
                            yield f"data: {json.dumps(data)}\n\n"
                            
                            # Update tracking variables
                            last_round = session.current_round
                            last_question = session.current_question
                            last_status = session.status
                            initial_state_sent = True
                        else:
                            # No hay pregunta disponible - enviar estado de espera
                            yield f"data: {json.dumps({{'type': 'waiting', 'message': 'Waiting for questions to be generated', 'status': session.status}})}\n\n"
                            last_status = session.status
                            initial_state_sent = True
                    else:
                        # Status changed but quiz not active
                        yield f"data: {json.dumps({'type': 'status_change', 'status': session.status})}\n\n"
                        last_status = session.status
                        initial_state_sent = True
                
                # Send heartbeat every 15 seconds to keep connection alive
                yield f": heartbeat\n\n"
                
                # Wait before checking again (1 second)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"SSE error for session {session_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response


@csrf_exempt
def host_stream(request, session_id):
    """
    SSE endpoint for host panel - provides stats, leaderboard, and question updates
    """
    from django.core.cache import cache
    
    def event_generator():
        """Generator for host-specific updates"""
        session = get_object_or_404(PubQuizSession, id=session_id)
        last_update_time = timezone.now()
        last_status = session.status
        last_round = session.current_round
        last_question = session.current_question
        last_progress = None
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        while True:
            try:
                # Check for generation progress
                progress_data = cache.get(f'quiz_generation_progress_{session_id}')
                if progress_data and progress_data != last_progress:
                    yield f"data: {json.dumps({'type': 'generation_progress', 'progress': progress_data['progress'], 'status': progress_data['status']})}\n\n"
                    last_progress = progress_data
                
                # Refresh session
                session.refresh_from_db()
                
                # Check if session ended
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Session completed'})}\n\n"
                    break
                
                # Detect changes
                status_changed = session.status != last_status
                question_changed = (session.current_round != last_round or 
                                  session.current_question != last_question)
                
                # Send updates every 3 seconds or when changes detected
                current_time = timezone.now()
                time_diff = (current_time - last_update_time).total_seconds()
                
                if status_changed or question_changed or time_diff >= 3:
                    # Get stats
                    teams = session.teams.all()
                    total_teams = teams.count()
                    teams_answered = 0
                    questions_generated = QuizQuestion.objects.filter(session=session).exists()
                    
                    if session.status == 'in_progress':
                        current_q = QuizQuestion.objects.filter(
                            session=session,
                            round_number=session.current_round,
                            question_number=session.current_question
                        ).first()
                        if current_q:
                            teams_answered = TeamAnswer.objects.filter(question=current_q).count()
                    
                    # Get leaderboard
                    leaderboard = []
                    for team in teams.order_by('-total_score', 'team_name'):
                        leaderboard.append({
                            'team_name': team.team_name,
                            'total_score': team.total_score,
                            'table_number': team.table_number
                        })
                    
                    # Get current question details if quiz is active
                    question_data = None
                    if session.status in ['in_progress', 'halftime', 'revealing_answer']:
                        question = QuizQuestion.objects.filter(
                            session=session,
                            round_number=session.current_round,
                            question_number=session.current_question
                        ).first()
                        
                        if question:
                            question_data = {
                                'id': question.id,
                                'text': question.question_text,
                                'answer': question.correct_answer if session.status == 'revealing_answer' else None,
                                'fun_fact': question.fun_fact if session.status == 'revealing_answer' else None,
                                'round': question.round_number,
                                'number': question.question_number,
                                'type': question.question_type,
                                'points': question.points,
                                'options': question.options if question.question_type == 'multiple_choice' else None
                            }
                    
                    # Send combined update
                    data = {
                        'type': 'host_update',
                        'stats': {
                            'total_teams': total_teams,
                            'teams_answered': teams_answered,
                            'status': session.status,
                            'current_round': session.current_round,
                            'current_question': session.current_question,
                            'total_rounds': session.total_rounds,
                            'questions_per_round': session.questions_per_round,
                            'questions_generated': questions_generated
                        },
                        'leaderboard': leaderboard,
                        'question': question_data,
                        'timestamp': current_time.isoformat()
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    last_update_time = current_time
                    last_status = session.status
                    last_round = session.current_round
                    last_question = session.current_question
                
                # Heartbeat
                yield f": heartbeat\n\n"
                
                # Wait 1 second before next check
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Host SSE error for session {session_id}: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


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
    is_multiple_choice = request.data.get('is_multiple_choice', False)
    
    # For multiple choice, check if answer matches correct option
    is_correct = False
    if is_multiple_choice and question.question_type == 'multiple_choice':
        is_correct = (answer_text.upper() == question.correct_option.upper())
    
    # Verificar si ya respondió (para evitar duplicados)
    ans, created = TeamAnswer.objects.get_or_create(
        team=team,
        question=question,
        defaults={
            'answer_text': answer_text,
            'is_correct': is_correct
        }
    )
    
    if not created:
        ans.answer_text = answer_text
        ans.is_correct = is_correct
        ans.save()
        
    return Response({
        'success': True,
        'message': 'Answer submitted successfully',
        'is_correct': is_correct
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

# Removed: get_leaderboard - replaced by SSE host_stream
# Removed: get_session_stats - replaced by SSE host_stream


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


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_quiz_tts(request):
    """Generate TTS audio for quiz questions"""
    import os
    import requests
    
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
    
    if not ELEVENLABS_API_KEY:
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)
    
    try:
        text = request.data.get('text', '')
        voice_id = request.data.get('voice_id', ELEVENLABS_VOICE_ID)
        
        if not text:
            return Response({'error': 'No text provided'}, status=400)
        
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        
        response = requests.post(
            url,
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.35,
                    'similarity_boost': 0.85,
                    'style': 0.5,
                    'use_speaker_boost': True
                },
                'optimize_streaming_latency': 1,
                'output_format': 'mp3_44100_128'
            }
        )
        
        if not response.ok:
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
        
        return HttpResponse(response.content, content_type='audio/mpeg')
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


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


# ============================================================================
# TTS (Text-to-Speech)
# ============================================================================

@api_view(['POST'])
def generate_quiz_tts(request):
    """Genera audio TTS para preguntas del quiz usando ElevenLabs"""
    import requests
    
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
    
    # Voice IDs de ElevenLabs
    VOICE_MAP = {
        'daniel': 'onwK4e9ZLuTAKqWW03F9',      # Daniel (Male British)
        'charlotte': '21m00Tcm4TlvDq8ikWAM',   # Charlotte (Female British) 
        'callum': 'N2lVS1w4EtoT3dr4eOWO',      # Callum (Male British)
        'alice': 'Xb7hH8MSUJpSbSDYk0k2'        # Alice (Female British)
    }
    
    if not ELEVENLABS_API_KEY:
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)
    
    try:
        text = request.data.get('text', '')
        voice_id_name = request.data.get('voice_id', 'daniel')
        
        if not text:
            return Response({'error': 'No text provided'}, status=400)
        
        # Obtener voice ID real
        voice_id = VOICE_MAP.get(voice_id_name, VOICE_MAP['daniel'])
        
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        
        response = requests.post(
            url,
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.35,
                    'similarity_boost': 0.85,
                    'style': 0.5,
                    'use_speaker_boost': True
                },
                'optimize_streaming_latency': 1,
                'output_format': 'mp3_44100_128'
            },
            timeout=30
        )
        
        if not response.ok:
            logger.error(f'ElevenLabs API error: {response.status_code} - {response.text}')
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
        
        return HttpResponse(response.content, content_type='audio/mpeg')
        
    except Exception as e:
        logger.error(f'TTS generation error: {e}')
        return Response({'error': str(e)}, status=500)
