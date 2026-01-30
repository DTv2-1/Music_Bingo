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

logger = logging.getLogger(__name__)

# Global dict to track last question position per session for SSE sync
_player_question_positions = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_session_by_code_or_id(session_identifier):
    """
    Get session by session_code (string) or id (int).
    This allows backward compatibility with numeric IDs.
    """
    logger.info(f"🔎 [GET_SESSION] Looking for session: '{session_identifier}'")
    logger.info(f"🔎 [GET_SESSION] Total sessions in DB: {PubQuizSession.objects.count()}")
    
    try:
        # Try as session_code first
        logger.info(f"🔎 [GET_SESSION] Trying by session_code...")
        session = PubQuizSession.objects.get(session_code=session_identifier)
        logger.info(f"✅ [GET_SESSION] Found by session_code: {session.id}")
        return session
    except PubQuizSession.DoesNotExist:
        logger.warning(f"⚠️ [GET_SESSION] Not found by session_code, trying numeric ID...")
        try:
            # Fallback to numeric ID
            session = PubQuizSession.objects.get(id=int(session_identifier))
            logger.info(f"✅ [GET_SESSION] Found by numeric ID: {session.id}")
            return session
        except (PubQuizSession.DoesNotExist, ValueError) as e:
            logger.error(f"❌ [GET_SESSION] Session not found anywhere: {e}")
            # List all session codes for debugging
            all_codes = list(PubQuizSession.objects.values_list('session_code', flat=True))
            logger.error(f"❌ [GET_SESSION] Available session codes: {all_codes}")
            return None
    except ValueError as e:
        logger.error(f"❌ [GET_SESSION] ValueError: {e}")
        return None
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎬 [CREATE_SESSION] Received request to create session")
        logger.info(f"📋 [CREATE_SESSION] Request data: {request.data}")
        
        data = request.data
        
        venue_name = data.get('venue_name', 'The Pub')
        host_name = data.get('host_name', 'Perfect DJ')
        total_rounds = data.get('total_rounds', 6)
        questions_per_round = data.get('questions_per_round', 10)
        duration_minutes = data.get('duration_minutes', 120)
        
        logger.info(f"📝 [CREATE_SESSION] Creating session: venue={venue_name}, host={host_name}, rounds={total_rounds}, q/round={questions_per_round}")
        
        session = PubQuizSession.objects.create(
            venue_name=venue_name,
            host_name=host_name,
            total_rounds=total_rounds,
            questions_per_round=questions_per_round,
            duration_minutes=duration_minutes,
            status='registration',
        )
        
        logger.info(f"💾 [CREATE_SESSION] Session object created: ID={session.id}, Code={session.session_code}, PK={session.pk}")
        
        # Django uses autocommit mode by default - session is already saved
        # Just verify it exists
        from django.db import connection
        logger.info(f"🔍 [CREATE_SESSION] DB in transaction: {connection.in_atomic_block}")
        
        verification = PubQuizSession.objects.filter(session_code=session.session_code).exists()
        logger.info(f"✅ [CREATE_SESSION] Session verified in DB: {verification}, Code: {session.session_code}")
        
        # Asegurarse de que los géneros estén inicializados
        if QuizGenre.objects.count() == 0:
            logger.info(f"🔧 [CREATE_SESSION] Initializing genres...")
            initialize_genres_in_db()
        
        response_data = {
            'success': True,
            'session_id': session.session_code,  # Use session_code instead of id
            'session': {
                'id': session.id,
                'session_code': session.session_code,
                'venue_name': session.venue_name,
                'status': session.status,
                'total_rounds': session.total_rounds,
                'questions_per_round': session.questions_per_round,
            }
        }
        
        logger.info(f"📤 [CREATE_SESSION] Returning response: {response_data}")
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"❌ [CREATE_SESSION] Exception: {str(e)}")
        logger.exception(e)
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# REGISTRO DE EQUIPOS Y QR
# ============================================================================

@api_view(['GET'])
def get_session_details(request, session_id):
    """Página de registro para equipos (acceso vía QR)"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
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
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)
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
    logger.info(f"🚀 [REGISTER_TEAM] Starting registration for session {session_id}")
    logger.info(f"📦 [REGISTER_TEAM] Request data: {request.data}")
    logger.info(f"🔑 [REGISTER_TEAM] Content-Type: {request.content_type}")
    
    try:
        logger.info(f"🔍 [REGISTER_TEAM] Looking up session {session_id}")
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)
        logger.info(f"✅ [REGISTER_TEAM] Session found: {session.venue_name}, status: {session.status}")
        
        data = request.data
        team_name = data.get('team_name')
        logger.info(f"👥 [REGISTER_TEAM] Team name: {team_name}")
        
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
        logger.info(f"🎭 [REGISTER_TEAM] Genre votes: {genre_votes}")
        
        for i, genre_id in enumerate(genre_votes[:5], 1):
            try:
                genre = QuizGenre.objects.get(id=genre_id)
                GenreVote.objects.create(
                    team=team,
                    genre=genre,
                    priority=i
                )
                logger.info(f"✅ [REGISTER_TEAM] Voted for genre {genre.name} (priority {i})")
            except QuizGenre.DoesNotExist:
                logger.warning(f"⚠️ [REGISTER_TEAM] Genre {genre_id} not found")
                pass
        
        logger.info(f"🎉 [REGISTER_TEAM] Registration successful! Team ID: {team.id}")
        return Response({
            'success': True,
            'team_id': team.id,
            'team_name': team.team_name,
            'bonus_points': team.bonus_points,
            'message': message
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"❌ [REGISTER_TEAM] Error: {str(e)}", exc_info=True)
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def generate_qr_code(request, session_id):
    """Genera código QR para registro del equipo"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🎯 [GENERATE_QUESTIONS] Starting generation for session {session_id}")
    
    try:
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)
        logger.info(f"✅ [GENERATE_QUESTIONS] Session found: {session.session_code}, rounds: {session.total_rounds}, questions/round: {session.questions_per_round}")
        
        # Initialize progress
        session.generation_progress = {'progress': 0, 'status': 'starting'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 0% - starting (session: {session_id})")
        
        # Get question type preferences from request body (DRF parses automatically)
        include_mc = request.data.get('include_multiple_choice', True)
        include_written = request.data.get('include_written', True)
        easy_count = request.data.get('easy_count', 3)
        medium_count = request.data.get('medium_count', 4)
        hard_count = request.data.get('hard_count', 3)
        
        logger.info(f"📋 [GENERATE_QUESTIONS] Question types - Multiple Choice: {include_mc}, Written: {include_written}")
        logger.info(f"📊 [GENERATE_QUESTIONS] Difficulty distribution - Easy: {easy_count}, Medium: {medium_count}, Hard: {hard_count}")
        
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
        
        # Difficulty distribution
        difficulty_mix = {
            'easy': easy_count,
            'medium': medium_count,
            'hard': hard_count
        }
        
        # Contar votos por género
        genre_votes = GenreVote.objects.filter(team__session=session).values('genre_id').annotate(
            vote_count=Count('genre_id')
        ).order_by('-vote_count')
        
        votes_dict = {v['genre_id']: v['vote_count'] for v in genre_votes}
        logger.info(f"🗳️ [GENERATE_QUESTIONS] Genre votes collected: {len(votes_dict)} genres voted")
        
        # Usar generador para seleccionar géneros
        generator = PubQuizGenerator()
        selected_genres = generator.select_genres_by_votes(votes_dict, session.total_rounds)
        logger.info(f"✅ [GENERATE_QUESTIONS] Selected {len(selected_genres)} genres: {[g['name'] for g in selected_genres]}")
        
        session.generation_progress = {'progress': 10, 'status': 'Selecting genres...'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 10% - Selecting genres... (session: {session_id})")
        
        # Crear estructura de rondas
        structure = generator.create_quiz_structure(
            selected_genres,
            questions_per_round=session.questions_per_round,
            include_halftime=True,
            include_buzzer_round=False
        )
        
        session.generation_progress = {'progress': 20, 'status': 'Creating quiz structure...'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 20% - Creating quiz structure... (session: {session_id})")
        
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
        
        session.generation_progress = {'progress': 30, 'status': 'Generating all questions (this may take 1-2 minutes)...'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 30% - Generating all questions (this may take 1-2 minutes)... (session: {session_id})")
        logger.info(f"🤖 [GENERATE_QUESTIONS] Starting parallel question generation for {len(rounds_to_generate)} rounds")
        
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
                    question_types=question_types,
                    difficulty_mix=difficulty_mix
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
                status_msg = f'Generated {idx+1}/{total_rounds} rounds...'
                session.generation_progress = {'progress': progress, 'status': status_msg}
                session.save(update_fields=['generation_progress'])
                logger.info(f"📊 [PROGRESS] {progress}% - {status_msg} (session: {session_id})")
        
        # Sort by round number
        all_round_questions.sort(key=lambda x: x['round_number'])
        
        # Save all questions to database
        session.generation_progress = {'progress': 92, 'status': 'Saving questions to database...'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 92% - Saving questions to database... (session: {session_id})")
        logger.info(f"💾 [GENERATE_QUESTIONS] Saving questions to database...")
        
        total_questions_saved = 0
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
                total_questions_saved += 1
        
        logger.info(f"✅ [GENERATE_QUESTIONS] Saved {total_questions_saved} questions to database")
        session.generation_progress = {'progress': 95, 'status': 'Finalizing quiz...'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 95% - Finalizing quiz... (session: {session_id})")
        
        # Actualizar estado de sesión
        session.status = 'ready'
        session.save()
        logger.info(f"✅ [GENERATE_QUESTIONS] Session status updated to 'ready'")
        
        # Agregar géneros seleccionados a la sesión
        for genre_data in selected_genres:
            genre = QuizGenre.objects.get(name=genre_data['name'])
            session.selected_genres.add(genre)
        
        session.generation_progress = {'progress': 100, 'status': 'Complete!'}
        session.save(update_fields=['generation_progress'])
        logger.info(f"📊 [PROGRESS] 100% - Complete! (session: {session_id})")
        logger.info(f"🎉 [GENERATE_QUESTIONS] Quiz generation completed successfully!")
        
        return Response({
            'success': True,
            'message': 'Quiz generado exitosamente',
            'structure': structure,
            'selected_genres': [g['name'] for g in selected_genres]
        })
    
    except Exception as e:
        logger.error(f"❌ [GENERATE_QUESTIONS] Error: {str(e)}", exc_info=True)
        if session:
            session.generation_progress = None
            session.save(update_fields=['generation_progress'])
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# CONTROL DEL QUIZ EN VIVO
# ============================================================================

@api_view(['GET'])
def quiz_host_data(request, session_id):
    """Obtiene datos para la vista del host"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📊 [HOST_DATA] ========== REQUEST START ==========")
    logger.info(f"📊 [HOST_DATA] Request for session_id: '{session_id}' (type: {type(session_id).__name__})")
    logger.info(f"📊 [HOST_DATA] Total sessions in DB at request time: {PubQuizSession.objects.count()}")
    
    session = get_session_by_code_or_id(session_id)
    if not session:
        logger.error(f"❌ [HOST_DATA] Session '{session_id}' not found!")
        return Response({"error": "Session not found"}, status=404)
    teams = session.teams.all().order_by('-total_score')
    rounds = session.rounds.all()
    
    # Get all questions for this session
    questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')
    
    logger.info(f"✅ [HOST_DATA] Found {teams.count()} teams, {rounds.count()} rounds, {questions.count()} questions")
    logger.info(f"⏱️ [HOST_DATA] question_started_at: {session.question_started_at}")
    
    # Get current question details
    current_question_obj = None
    if session.current_round and session.current_question:
        current_question_obj = questions.filter(
            round_number=session.current_round,
            question_number=session.current_question
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
            'bonus_points': t.bonus_points
        } for t in teams],
        'rounds': [{
            'round_number': r.round_number,
            'round_name': r.round_name,
            'is_completed': r.is_completed
        } for r in rounds],
        'questions': [{
            'id': q.id,
            'round_number': q.round_number,
            'question_number': q.question_number,
            'question_text': q.question_text,
            'question_type': q.question_type
        } for q in questions]
    })


@api_view(['POST'])
def start_quiz(request, session_id):
    """Inicia el quiz y envía todas las preguntas a los jugadores"""
    logger.info(f"🎬 [START_QUIZ] ========== START QUIZ CALLED ==========")
    logger.info(f"🎬 [START_QUIZ] Session ID: {session_id}")
    
    session = get_session_by_code_or_id(session_id)
    if not session:
        logger.error(f"❌ [START_QUIZ] Session not found: {session_id}")
        return Response({"error": "Session not found"}, status=404)
    
    logger.info(f"🎬 [START_QUIZ] Current status: {session.status}")
    logger.info(f"🎬 [START_QUIZ] Changing status to 'in_progress'...")
    
    session.status = 'in_progress'
    session.current_round = 1
    session.current_question = 1
    session.save()
    
    logger.info(f"✅ [START_QUIZ] Status saved! New status: {session.status}")
    
    # Force database commit
    from django.db import transaction
    transaction.commit()
    logger.info(f"💾 [START_QUIZ] Database commit forced")
    
    # Marcar primera ronda como iniciada
    first_round = session.rounds.filter(round_number=1).first()
    if first_round:
        first_round.started_at = timezone.now()
        first_round.save()
    
    # Obtener TODAS las preguntas del quiz
    all_questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')
    
    questions_data = []
    for q in all_questions:
        questions_data.append({
            'id': q.id,
            'text': q.question_text,
            'round': q.round_number,
            'number': q.question_number,
            'genre': q.genre.name if q.genre else 'General',
            'difficulty': q.difficulty,
            'points': q.get_points_value(),
            'type': q.question_type,
            'options': q.options if q.question_type == 'multiple_choice' else None,
            'correct_option': q.correct_option if q.question_type == 'multiple_choice' else None
        })
    
    # Configuración de timing
    timing_config = {
        'seconds_per_question': 15,  # 15 segundos por pregunta
        'halftime_duration': 90,  # 90 segundos de halftime
        'halftime_after_round': 1  # Halftime después del round 1
    }
    
    # Mensaje de bienvenida
    team_count = session.teams.count()
    welcome_message = (
        f"Welcome to {session.venue_name}'s Pub Quiz! "
        f"We have {team_count} teams competing today. "
        f"Get ready for {session.total_rounds} rounds of trivia fun! "
        f"Good luck everyone!"
    )
    
    logger.info(f"🎬 [START_QUIZ] Quiz started for session {session_id}, sending {len(questions_data)} questions to players")
    
    return Response({
        'success': True, 
        'status': 'in_progress',
        'welcome_message': welcome_message,
        'all_questions': questions_data,
        'timing': timing_config,
        'total_rounds': session.total_rounds,
        'questions_per_round': session.questions_per_round
    })


@api_view(['GET'])
def get_all_questions(request, session_id):
    """Get all questions for local navigation (no SSE needed for host)"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')
    
    questions_data = []
    for q in questions:
        questions_data.append({
            'id': q.id,
            'text': q.question_text,
            'answer': q.correct_answer,
            'fun_fact': q.fun_fact,
            'round': q.round_number,
            'number': q.question_number,
            'genre': q.genre.name if q.genre else 'General Knowledge',
            'difficulty': q.difficulty,
            'points': q.get_points_value(),
            'type': q.question_type,
            'options': q.options if q.question_type == 'multiple_choice' else None
        })
    
    return Response({
        'success': True,
        'questions': questions_data,
        'total': len(questions_data)
    })


@api_view(['POST'])
def sync_question_to_players(request, session_id):
    """Sync current question to player screens via SSE"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    data = request.data
    round_num = data.get('round')
    question_num = data.get('question_number')
    
    # Update session state
    session.current_round = round_num
    session.current_question = question_num
    session.save()
    
    logger.info(f"📡 [SYNC] Host updated to Round {round_num}, Q{question_num}")
    
    return Response({
        'success': True,
        'message': 'Question synced to players'
    })


@api_view(['POST'])
def start_countdown(request, session_id):
    """Marca el inicio del countdown después de que TTS termine"""
    import logging
    logger = logging.getLogger(__name__)
    
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    logger.info(f"⏱️ [START_COUNTDOWN] Setting question_started_at for session {session_id}")
    session.question_started_at = timezone.now()
    logger.info(f"⏱️ [START_COUNTDOWN] Before save: {session.question_started_at}")
    session.save(update_fields=['question_started_at'])
    logger.info(f"⏱️ [START_COUNTDOWN] After save: {session.question_started_at}")
    
    # Verificar que se guardó
    session.refresh_from_db()
    logger.info(f"⏱️ [START_COUNTDOWN] After refresh_from_db: {session.question_started_at}")
    
    return Response({
        'success': True,
        'question_started_at': session.question_started_at.isoformat() if session.question_started_at else None
    })


@api_view(['POST'])
def reset_quiz(request, session_id):
    """Reinicia completamente el quiz a su estado inicial"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
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
    
    return Response({'success': True, 'message': 'Quiz reset successfully'})


@api_view(['DELETE'])
def delete_session(request, session_id):
    """Elimina completamente una sesión y todos sus datos relacionados"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ [DELETE_SESSION] Request to delete session {session_id}")
    
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    venue_name = session.venue_name
    
    # Django cascadeará automáticamente y borrará:
    # - Teams (por ForeignKey con on_delete=CASCADE)
    # - GenreVotes (relacionados a teams)
    # - QuizQuestions (por ForeignKey)
    # - QuizRounds (por ForeignKey)
    # - TeamAnswers (relacionados a teams)
    
    session.delete()
    
    logger.info(f"✅ [DELETE_SESSION] Session '{venue_name}' (ID: {session_id}) deleted successfully")
    
    return Response({
        'success': True, 
        'message': f'Session "{venue_name}" deleted successfully'
    })


@api_view(['POST'])
def next_question(request, session_id):
    """Avanza a la siguiente pregunta"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    logger.info(f"🔄 [NEXT] Current state - Round: {session.current_round}, Question: {session.current_question}, Status: {session.status}")
    
    # 🔧 FIX: Si estamos en halftime, el primer "Next" debe pasar a in_progress
    if session.status == 'halftime':
        logger.info(f"▶️ [HALFTIME] Currently in halftime status")
        logger.info(f"▶️ [HALFTIME] Round: {session.current_round}, Question: {session.current_question}")
        logger.info(f"▶️ [HALFTIME] User clicked Next - resuming to 'in_progress'")
        session.status = 'in_progress'
        session.save()
        logger.info(f"✅ [HALFTIME] Status changed to 'in_progress', quiz continues")
        logger.info(f"📡 [HALFTIME] Sending SSE notification to update frontend")
        return Response({
            'success': True,
            'current_round': session.current_round,
            'current_question': session.current_question,
            'status': session.status
        })
    
    total_questions_in_round = session.questions_per_round
    
    logger.info(f"🔍 [NEXT] total_questions_in_round: {total_questions_in_round}, current_question: {session.current_question}")
    
    if session.current_question < total_questions_in_round:
        session.current_question += 1
        # Keep question_started_at as None - frontend will set it after TTS via start-countdown
        # DO NOT reset to timezone.now() here as it would start countdown before TTS finishes
        session.question_started_at = None
        # Ensure status is in_progress when showing a new question
        session.status = 'in_progress'
        logger.info(f"➡️ [NEXT] Moving to question {session.current_question} (still in round {session.current_round}), question_started_at reset to None (will be set after TTS)")
    else:
        # Siguiente ronda
        logger.info(f"🎯 [NEXT] ❗ LAST QUESTION OF ROUND - current_question ({session.current_question}) >= total ({total_questions_in_round})")
        logger.info(f"🎯 [NEXT] Will advance from Round {session.current_round} to Round {session.current_round + 1}")
        
        current_round = session.rounds.filter(round_number=session.current_round).first()
        if current_round:
            current_round.is_completed = True
            current_round.completed_at = timezone.now()
            current_round.save()
            logger.info(f"✅ [NEXT] Round {session.current_round} marked as completed")
        
        if session.current_round < session.total_rounds:
            old_round = session.current_round
            session.current_round += 1
            session.current_question = 1
            session.question_started_at = None  # Will be set by frontend after TTS
            logger.info(f"🔄 [NEXT] Changed from Round {old_round} to Round {session.current_round}, Question reset to 1")
            
            # Verificar si es halftime
            next_round = session.rounds.filter(round_number=session.current_round).first()
            if next_round and next_round.is_halftime_before:
                logger.info(f"🍻 [HALFTIME] ❗❗❗ Detected is_halftime_before=True for round {session.current_round}")
                logger.info(f"🍻 [HALFTIME] Previous round completed: {session.current_round - 1}")
                logger.info(f"🍻 [HALFTIME] Next round will be: {session.current_round}")
                logger.info(f"🍻 [HALFTIME] Setting status to 'halftime' for break")
                session.status = 'halftime'
                logger.info(f"✅ [HALFTIME] Status saved, SSE will notify frontend")
            else:
                logger.info(f"⚠️ [NEXT] No halftime detected for round {session.current_round} (is_halftime_before={next_round.is_halftime_before if next_round else 'N/A'})")
            
            if next_round:
                next_round.started_at = timezone.now()
                next_round.save()
                logger.info(f"▶️ [NEXT] Starting Round {session.current_round}")
        else:
            session.status = 'completed'
            logger.info(f"🏉 [NEXT] Quiz completed!")
    
    logger.info(f"💾 [NEXT] About to save session - Final state: Round {session.current_round}, Question {session.current_question}, Status: {session.status}")
    session.save()
    logger.info(f"✅ [NEXT] Session saved successfully")
    
    # 📡 SYNC: Get current question details to send to players
    current_question_obj = QuizQuestion.objects.filter(
        session=session,
        round_number=session.current_round,
        question_number=session.current_question
    ).first()
    
    logger.info(f"📡 [SYNC] Broadcasting question_update to all connected players")
    logger.info(f"📡 [SYNC] Round: {session.current_round}, Question: {session.current_question}")
    
    return Response({
        'success': True,
        'current_round': session.current_round,
        'current_question': session.current_question,
        'status': session.status,
        'broadcast_to_players': True  # Flag to trigger SSE broadcast
    })


@api_view(['POST'])
def toggle_auto_advance(request, session_id):
    """Toggle auto-advance on/off"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    session.auto_advance_enabled = not session.auto_advance_enabled
    if session.auto_advance_enabled and session.status == 'in_progress':
        # Starting auto-advance - mark current question start time
        session.question_started_at = timezone.now()
    session.save()
    
    return Response({
        'success': True,
        'auto_advance_enabled': session.auto_advance_enabled
    })


@api_view(['POST'])
def pause_auto_advance(request, session_id):
    """Pause/resume auto-advance timer"""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)
    
    session.auto_advance_paused = not session.auto_advance_paused
    session.save()
    
    return Response({
        'success': True,
        'auto_advance_paused': session.auto_advance_paused
    })


@api_view(['POST'])
def set_auto_advance_time(request, session_id):
    """Set auto-advance timer duration"""
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
        'auto_advance_seconds': session.auto_advance_seconds
    })


def quiz_stream(request, session_id):
    """
    Server-Sent Events endpoint for real-time quiz updates
    NEW: Sends ALL questions at once when quiz starts
    """
    def event_generator():
        """Generator that yields SSE-formatted messages"""
        session = get_session_by_code_or_id(session_id)
        if not session:
            yield f"data: {{\"type\": \"error\", \"message\": \"Session not found\"}}\n\n"
            return
        
        connection_start = timezone.now()
        MAX_CONNECTION_TIME = 300  # 5 minutes max for SSE connection
        
        last_status = None  # Initialize as None to detect first poll
        quiz_started_sent = False  # Track if we've sent the quiz_started message
        
        # Keepalive tracking - send data keepalive every 30s to prevent timeout
        last_keepalive = timezone.now()
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        logger.info(f"📡 [SSE] Player connected to session {session_id}")
        
        while True:
            try:
                # 🔧 FIX: Force close SSE after MAX_CONNECTION_TIME to prevent zombie connections
                connection_duration = (timezone.now() - connection_start).total_seconds()
                if connection_duration > MAX_CONNECTION_TIME:
                    logger.info(f"⏰ [SSE] Player connection timeout for {session_id} after {connection_duration:.0f}s, closing")
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout, please refresh'})}\n\n"
                    break
                
                # Refresh session from database
                session.refresh_from_db()
                
                # Check if session ended
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Quiz completed'})}\n\n"
                    logger.info(f"🏁 [SSE] Quiz completed for session {session_id}")
                    break
                
                # Detect status change
                status_changed = session.status != last_status
                logger.info(f"🔍 [SSE] Status check: current={session.status}, last={last_status}, changed={status_changed}, quiz_started_sent={quiz_started_sent}")
                
                # NEW: Send questions when quiz is in_progress (either just started OR player connected late)
                should_send_questions = (
                    session.status == 'in_progress' and 
                    not quiz_started_sent and 
                    (status_changed or last_status is None)  # Changed to in_progress OR first poll
                )
                
                if should_send_questions:
                    logger.info(f"🎬 [SSE] ✅ CONDITIONS MET! Quiz started! Sending all questions to players...")
                    logger.info(f"🎬 [SSE] - status_changed: {status_changed}")
                    logger.info(f"🎬 [SSE] - session.status: {session.status}")
                    logger.info(f"🎬 [SSE] - quiz_started_sent: {quiz_started_sent}")
                    
                    # Get ALL questions
                    all_questions = QuizQuestion.objects.filter(session=session).order_by('round_number', 'question_number')
                    
                    questions_data = []
                    for q in all_questions:
                        questions_data.append({
                            'id': q.id,
                            'text': q.question_text,
                            'round': q.round_number,
                            'number': q.question_number,
                            'genre': q.genre.name if q.genre else 'General',
                            'difficulty': q.difficulty,
                            'points': q.get_points_value(),
                            'type': q.question_type,
                            'options': q.options if q.question_type == 'multiple_choice' else None
                        })
                    
                    # Timing configuration
                    timing_config = {
                        'seconds_per_question': 15,
                        'halftime_duration': 90,
                        'halftime_after_round': 1
                    }
                    
                    data = {
                        'type': 'quiz_started',
                        'all_questions': questions_data,
                        'timing': timing_config,
                        'total_rounds': session.total_rounds,
                        'questions_per_round': session.questions_per_round,
                        'current_round': session.current_round,
                        'current_question': session.current_question
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    logger.info(f"✅ [SSE] Sent {len(questions_data)} questions to players")
                    
                    quiz_started_sent = True
                    last_status = session.status
                
                # 📡 SYNC: Send question_update when host advances question
                if session.status == 'in_progress' and quiz_started_sent:
                    # Check if question changed by comparing with stored position
                    current_position = f"{session.current_round}.{session.current_question}"
                    last_position = _player_question_positions.get(session_id, None)
                    
                    logger.info(f"🔍 [SYNC] Position check - current: {current_position}, last: {last_position}, status: {session.status}")
                    
                    if last_position != current_position and last_position is not None:
                        logger.info(f"📡 [SYNC] ⚡ Question changed from {last_position} to {current_position}")
                        logger.info(f"📡 [SYNC] Preparing question_update event for players...")
                        
                        # Get timing config
                        timing_config = {
                            'seconds_per_question': 15,
                            'halftime_duration': 90,
                            'halftime_after_round': 1,
                            'total_rounds': session.total_rounds
                        }
                        
                        question_update_data = {
                            'type': 'question_update',
                            'round': session.current_round,
                            'question': session.current_question,
                            'timing': timing_config
                        }
                        
                        yield f"data: {json.dumps(question_update_data)}\n\n"
                        logger.info(f"✅ [SYNC] Sent question_update to players: Round {session.current_round}, Question {session.current_question}")
                    elif last_position is None:
                        logger.info(f"🔍 [SYNC] First poll - initializing position to {current_position}")
                    else:
                        logger.info(f"🔍 [SYNC] No change detected")
                    
                    # Update stored position
                    _player_question_positions[session_id] = current_position
                
                # Handle other status changes
                elif status_changed:
                    if session.status == 'ready' or session.status == 'registration':
                        yield f"data: {json.dumps({'type': 'waiting', 'message': 'Waiting for quiz to start', 'status': session.status})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status_change', 'status': session.status})}\n\n"
                    
                    last_status = session.status
                
                # Check if data keepalive is needed (every 30 seconds)
                current_time = timezone.now()
                time_since_keepalive = (current_time - last_keepalive).total_seconds()
                if time_since_keepalive >= 30:
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': current_time.isoformat()})}\n\n"
                    last_keepalive = current_time
                
                # Send comment-based heartbeat (lightweight, doesn't trigger client events)
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
        session = get_session_by_code_or_id(session_id)
        if not session:
            yield f"data: {{\"type\": \"error\", \"message\": \"Session not found\"}}\n\n"
            return
        
        connection_start = timezone.now()
        MAX_CONNECTION_TIME = 300  # 5 minutes max for SSE connection
        
        last_update_time = timezone.now()
        last_status = session.status
        last_round = session.current_round
        last_question = session.current_question
        last_progress = None
        last_keepalive = timezone.now()  # Track last keepalive message
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        while True:
            try:
                # 🔧 FIX: Force close SSE after MAX_CONNECTION_TIME to prevent zombie connections
                connection_duration = (timezone.now() - connection_start).total_seconds()
                if connection_duration > MAX_CONNECTION_TIME:
                    logger.info(f"⏰ [SSE] Connection timeout for {session_id} after {connection_duration:.0f}s, closing")
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout, please refresh'})}\n\n"
                    break
                
                # Refresh session to get latest progress
                session.refresh_from_db()
                
                # Check for generation progress
                progress_data = session.generation_progress
                if progress_data:
                    logger.info(f"🔍 [SSE] Found progress data for {session_id}: {progress_data}")
                    if progress_data != last_progress:
                        logger.info(f"📤 [SSE] Sending progress update: {progress_data}")
                        yield f"data: {json.dumps({'type': 'generation_progress', 'progress': progress_data['progress'], 'status': progress_data['status']})}\n\n"
                        last_progress = progress_data
                        
                        # 🔧 FIX: Force close SSE when generation reaches 100%
                        if progress_data.get('progress', 0) >= 100:
                            logger.info(f"✅ [SSE] Generation 100% reached, closing SSE for {session_id}")
                            yield f"data: {json.dumps({'type': 'generation_complete', 'message': 'Generation complete, closing connection'})}\n\n"
                            break
                else:
                    if last_progress is not None:
                        logger.info(f"🔍 [SSE] No progress data for {session_id}")
                
                # Check if session ended
                if session.status == 'completed':
                    yield f"data: {json.dumps({'type': 'ended', 'message': 'Session completed'})}\n\n"
                    break
                
                # Detect changes
                status_changed = session.status != last_status
                question_changed = (session.current_round != last_round or 
                                  session.current_question != last_question)
                
                # Only send updates when something actually changed OR every 10 seconds for heartbeat
                current_time = timezone.now()
                time_diff = (current_time - last_update_time).total_seconds()
                
                # Send update if: status changed, question changed, or 10 seconds passed (heartbeat)
                should_send_update = status_changed or question_changed or time_diff >= 10
                
                if should_send_update:
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
                                'points': question.get_points_value(),
                                'difficulty': question.difficulty,
                                'genre': question.genre.name if question.genre else 'General',
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
                            'questions_generated': questions_generated,
                            'auto_advance_enabled': session.auto_advance_enabled,
                            'auto_advance_seconds': session.auto_advance_seconds,
                            'auto_advance_paused': session.auto_advance_paused,
                            'question_started_at': session.question_started_at.isoformat() if session.question_started_at else None
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
                
                # SSE keepalive strategy (best practices):
                # 1. Comment lines (:) every 15s - prevents timeouts, no client traffic
                # 2. Data messages every 30s - for monitoring/debugging
                time_since_keepalive = (current_time - last_keepalive).total_seconds()
                if time_since_keepalive >= 30:
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': current_time.isoformat()})}\n\n"
                    last_keepalive = current_time
                    logger.debug(f"💓 [SSE] Data keepalive sent for session {session_id}")
                
                # Lightweight comment keepalive (every iteration = ~1s)
                # This prevents proxy/Cloud Run timeouts without generating client events
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


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_all_answers(request, session_id):
    """
    NEW: Receive all answers from a team at the end of the quiz
    """
    try:
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({'error': 'Session not found'}, status=404)
        
        team_id = request.data.get('team_id')
        answers = request.data.get('answers', [])
        
        if not team_id:
            return Response({'error': 'team_id required'}, status=400)
        
        team = get_object_or_404(QuizTeam, id=team_id)
        
        logger.info(f"📥 [SUBMIT_ALL] Receiving {len(answers)} answers from team {team.team_name}")
        
        saved_count = 0
        for ans_data in answers:
            question_id = ans_data.get('question_id')
            answer_text = ans_data.get('answer', '')
            is_multiple_choice = ans_data.get('is_multiple_choice', False)
            
            try:
                question = QuizQuestion.objects.get(id=question_id, session=session)
                
                # Check if correct
                is_correct = False
                if is_multiple_choice and question.question_type == 'multiple_choice':
                    is_correct = (answer_text.upper() == question.correct_option.upper())
                else:
                    # For written answers, compare against correct answer and alternatives
                    answer_lower = answer_text.lower().strip()
                    correct_lower = question.correct_answer.lower().strip()
                    is_correct = (answer_lower == correct_lower)
                    
                    # Check alternatives
                    if not is_correct and question.alternative_answers:
                        for alt in question.alternative_answers:
                            if answer_lower == alt.lower().strip():
                                is_correct = True
                                break
                
                # Save or update answer
                team_answer, created = TeamAnswer.objects.update_or_create(
                    team=team,
                    question=question,
                    defaults={
                        'answer_text': answer_text,
                        'is_correct': is_correct,
                        'submitted_at': timezone.now()
                    }
                )
                saved_count += 1
                
            except QuizQuestion.DoesNotExist:
                logger.warning(f"⚠️ [SUBMIT_ALL] Question {question_id} not found")
                continue
        
        logger.info(f"✅ [SUBMIT_ALL] Saved {saved_count}/{len(answers)} answers for team {team.team_name}")
        
        return Response({
            'success': True,
            'message': f'Submitted {saved_count} answers',
            'saved_count': saved_count
        })
        
    except Exception as e:
        logger.error(f"❌ [SUBMIT_ALL] Error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


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
@permission_classes([AllowAny])
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
        logger.error("❌ [TTS] ElevenLabs API key not configured")
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)
    
    try:
        text = request.data.get('text', '')
        voice_id_name = request.data.get('voice_id', 'daniel')
        
        logger.info(f"🎤 [TTS] ===== NEW REQUEST =====")
        logger.info(f"🎤 [TTS] Text length: {len(text)} chars")
        logger.info(f"🎤 [TTS] Text preview: {text[:100]}...")
        logger.info(f"🎤 [TTS] Voice requested: {voice_id_name}")
        
        if not text:
            logger.error("❌ [TTS] No text provided")
            return Response({'error': 'No text provided'}, status=400)
        
        # Obtener voice ID real
        voice_id = VOICE_MAP.get(voice_id_name, VOICE_MAP['daniel'])
        logger.info(f"🎙️ [TTS] Using voice ID: {voice_id}")
        
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        logger.info(f"📡 [TTS] Calling ElevenLabs API at {url}")
        
        # Use streaming for faster response
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
            timeout=45,  # Keep for cold starts
            stream=True  # Enable streaming
        )
        
        logger.info(f"📡 [TTS] ElevenLabs response status: {response.status_code}")
        
        if not response.ok:
            logger.error(f'❌ [TTS] ElevenLabs API error: {response.status_code} - {response.text}')
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
        
        logger.info(f"✅ [TTS] Starting audio stream...")
        
        # Stream audio chunks instead of waiting for complete response
        def audio_stream():
            chunk_count = 0
            total_bytes = 0
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    chunk_count += 1
                    total_bytes += len(chunk)
                    yield chunk
            logger.info(f"✅ [TTS] Stream complete: {chunk_count} chunks, {total_bytes} bytes")
        
        return StreamingHttpResponse(audio_stream(), content_type='audio/mpeg')
        
    except Exception as e:
        logger.error(f'❌ [TTS] Exception: {type(e).__name__}: {str(e)}')
        import traceback
        logger.error(f'❌ [TTS] Traceback: {traceback.format_exc()}')
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_answer_sheets(request):
    """
    Generate printable answer sheets for a pub quiz session
    
    POST /api/pub-quiz/generate-answer-sheets/
    Body: {
        "session_code": "Y5SWRH0M",
        "num_sheets": 30  (optional, default 30)
    }
    
    Returns PDF file
    """
    from generate_pub_quiz_cards import generate_blank_templates
    from datetime import datetime
    
    try:
        session_code = request.data.get('session_code')
        num_sheets = request.data.get('num_sheets', 30)
        
        logger.info(f"📄 [ANSWER_SHEETS] Received request for session {session_code}, {num_sheets} sheets")
        
        if not session_code:
            logger.error(f"❌ [ANSWER_SHEETS] Missing session_code in request")
            return Response({'error': 'session_code required'}, status=400)
        
        # Get session
        session = get_session_by_code_or_id(session_code)
        if not session:
            logger.error(f"❌ [ANSWER_SHEETS] Session {session_code} not found")
            return Response({'error': 'Session not found'}, status=404)
        
        logger.info(f"✅ [ANSWER_SHEETS] Session found: {session.venue_name}, {session.total_rounds} rounds")
        
        # Get session details
        venue_name = session.venue_name or "Perfect DJ Pub Quiz"
        session_date = session.created_at.strftime("%d/%m/%Y") if session.created_at else ""
        
        # Get all questions organized by round
        questions_by_round = []
        rounds = QuizRound.objects.filter(session=session).order_by('round_number')
        
        for round_obj in rounds:
            questions = QuizQuestion.objects.filter(
                session=session, 
                round_number=round_obj.round_number
            ).order_by('question_number')
            
            round_questions = []
            for q in questions:
                question_data = {
                    'number': q.question_number,
                    'text': q.question_text,
                    'type': q.question_type,
                    'genre': round_obj.genre.name if round_obj.genre else 'General'
                }
                
                # Add options for multiple choice
                if q.question_type == 'multiple_choice' and q.options:
                    question_data['options'] = q.options
                
                round_questions.append(question_data)
            
            if round_questions:
                questions_by_round.append({
                    'round_number': round_obj.round_number,
                    'genre': round_obj.genre.name if round_obj.genre else 'General',
                    'questions': round_questions
                })
        
        # If no questions generated yet, return error
        if not questions_by_round:
            logger.error(f"❌ [ANSWER_SHEETS] No questions found for session {session_code}")
            return Response({'error': 'Please generate quiz questions first before printing answer sheets'}, status=400)
        
        logger.info(f"📊 [ANSWER_SHEETS] Found {len(questions_by_round)} rounds with questions")
        
        # Generate PDF with actual questions
        logger.info(f"🖨️ [ANSWER_SHEETS] Generating {num_sheets} answer sheets with questions for session {session_code}")
        pdf_buffer = generate_blank_templates(
            venue_name=venue_name,
            session_date=session_date,
            questions_by_round=questions_by_round,
            num_sheets=num_sheets,
            output_path=None
        )
        
        # Get PDF size for logging
        pdf_buffer.seek(0, 2)  # Seek to end
        pdf_size = pdf_buffer.tell()  # Get position (file size)
        pdf_buffer.seek(0)  # Reset to beginning
        
        logger.info(f"✅ [ANSWER_SHEETS] PDF generated successfully, size: {pdf_size / 1024:.2f} KB")
        
        # Create response
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pub_quiz_answer_sheets_{session_code}.pdf"'
        
        logger.info(f"📥 [ANSWER_SHEETS] Sending PDF download for session {session_code}")
        return response
        
    except Exception as e:
        logger.error(f"❌ [ANSWER_SHEETS] Error generating answer sheets: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
