"""
Test manual para verificar la generación de preguntas del Pub Quiz
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

from api.pub_quiz_models import PubQuizSession, QuizTeam, QuizGenre, GenreVote, QuizQuestion, QuizRound
from api.pub_quiz_generator import PubQuizGenerator, initialize_genres_in_db
from django.utils import timezone
import json


def test_question_generation():
    print("\n" + "="*80)
    print("🧪 TEST: GENERACIÓN DE PREGUNTAS PUB QUIZ")
    print("="*80 + "\n")
    
    # 1. Inicializar géneros si no existen
    print("📚 Paso 1: Inicializando géneros en la base de datos...")
    initialize_genres_in_db()
    genres = QuizGenre.objects.all()
    print(f"   ✅ Total géneros disponibles: {genres.count()}")
    for genre in genres[:5]:
        print(f"      - {genre.name}")
    if genres.count() > 5:
        print(f"      ... y {genres.count() - 5} más")
    
    # 2. Crear sesión de prueba
    print("\n🎯 Paso 2: Creando sesión de prueba...")
    test_session = PubQuizSession.objects.create(
        venue_name="Test Venue - Question Generation",
        date=timezone.now().date(),
        status='registration',
        total_rounds=5,
        questions_per_round=10
    )
    print(f"   ✅ Sesión creada: ID={test_session.id}")
    print(f"      - Rondas: {test_session.total_rounds}")
    print(f"      - Preguntas por ronda: {test_session.questions_per_round}")
    print(f"      - Total preguntas esperadas: {test_session.total_rounds * test_session.questions_per_round}")
    
    # 3. Crear equipos y votos de género
    print("\n👥 Paso 3: Creando equipos y votos de género...")
    teams_votes = [
        ("Team A", ["Rock & Classic Rock", "Pop Music", "80s Nostalgia"]),
        ("Team B", ["Rock & Classic Rock", "Hip Hop & Rap", "90s Nostalgia"]),
        ("Team C", ["Rock & Classic Rock", "Electronic & Dance Music", "Pop Music"]),
        ("Team D", ["Country & Folk", "Rock & Classic Rock", "Jazz & Blues"]),
    ]
    
    for team_name, genre_names in teams_votes:
        team = QuizTeam.objects.create(
            session=test_session,
            team_name=team_name,
            table_number=teams_votes.index((team_name, genre_names)) + 1
        )
        print(f"   👤 {team_name} (Table {team.table_number})")
        
        for genre_name in genre_names:
            genre = QuizGenre.objects.filter(name=genre_name).first()
            if genre:
                GenreVote.objects.create(team=team, genre=genre)
                print(f"      ✅ Voto: {genre_name}")
            else:
                print(f"      ⚠️  Género no encontrado: {genre_name}")
    
    # 4. Contar votos por género
    print("\n📊 Paso 4: Contando votos por género...")
    from django.db.models import Count
    genre_votes = GenreVote.objects.filter(
        team__session=test_session
    ).values('genre__name').annotate(
        vote_count=Count('genre_id')
    ).order_by('-vote_count')
    
    print("   Resultados de votación:")
    for vote in genre_votes:
        print(f"      {vote['genre__name']}: {vote['vote_count']} votos")
    
    # 5. Generar estructura del quiz
    print("\n🔧 Paso 5: Generando estructura del quiz...")
    generator = PubQuizGenerator()
    
    # Convertir votos a formato esperado por el generador
    votes_dict = {}
    for vote in GenreVote.objects.filter(team__session=test_session).values('genre_id').annotate(
        vote_count=Count('genre_id')
    ):
        votes_dict[vote['genre_id']] = vote['vote_count']
    
    print(f"   Votos procesados: {votes_dict}")
    
    # Seleccionar géneros
    selected_genres = generator.select_genres_by_votes(votes_dict, test_session.total_rounds)
    print(f"\n   ✅ Géneros seleccionados para {test_session.total_rounds} rondas:")
    for i, genre_dict in enumerate(selected_genres, 1):
        print(f"      Ronda {i}: {genre_dict['name']} (ID: {genre_dict['id']})")
    
    # Crear estructura
    structure = generator.create_quiz_structure(
        selected_genres,
        questions_per_round=test_session.questions_per_round,
        include_halftime=True,
        include_buzzer_round=False
    )
    
    print(f"\n   📋 Estructura creada:")
    print(f"      - Total rondas: {len(structure['rounds'])}")
    print(f"      - Halftime después de ronda: {structure.get('halftime_after_round', 'N/A')}")
    
    # 6. Generar preguntas y guardar en DB
    print("\n🎲 Paso 6: Generando preguntas y guardando en base de datos...")
    
    question_types_config = {'multiple_choice': 0.7, 'written': 0.3}
    total_questions_created = 0
    
    for round_data in structure['rounds']:
        genre = QuizGenre.objects.get(name=round_data['genre']['name'])
        
        # Crear ronda
        quiz_round = QuizRound.objects.create(
            session=test_session,
            round_number=round_data['round_number'],
            genre=genre
        )
        
        print(f"\n   📍 Ronda {quiz_round.round_number}: {genre.name}")
        
        # Generar preguntas para esta ronda
        questions = generator.generate_sample_questions(
            genre.name,
            count=test_session.questions_per_round,
            question_types=question_types_config
        )
        
        # Guardar preguntas
        for idx, q_data in enumerate(questions, 1):
            question = QuizQuestion.objects.create(
                session=test_session,
                round_number=quiz_round.round_number,
                question_number=idx,
                genre=genre,
                question_text=q_data['question'],
                correct_answer=q_data['answer'],
                question_type=q_data.get('question_type', 'written'),
                difficulty=q_data.get('difficulty', 'medium'),
                points=q_data.get('points', 10),
                fun_fact=q_data.get('fun_fact', '')
            )
            total_questions_created += 1
            print(f"      Q{idx}: [{q_data.get('question_type', 'written')}] {q_data['question'][:60]}...")
    
    print(f"\n   ✅ Total preguntas creadas: {total_questions_created}")
    
    # 7. Verificar preguntas en DB
    print("\n✅ Paso 7: Verificando preguntas guardadas...")
    saved_questions = QuizQuestion.objects.filter(session=test_session)
    print(f"   Total preguntas en DB: {saved_questions.count()}")
    
    # Estadísticas por tipo
    from django.db.models import Count
    by_type = saved_questions.values('question_type').annotate(count=Count('id'))
    print(f"\n   📊 Distribución por tipo:")
    for stat in by_type:
        percentage = (stat['count'] / saved_questions.count()) * 100
        print(f"      {stat['question_type']}: {stat['count']} ({percentage:.1f}%)")
    
    # Estadísticas por dificultad
    by_difficulty = saved_questions.values('difficulty').annotate(count=Count('id'))
    print(f"\n   📊 Distribución por dificultad:")
    for stat in by_difficulty:
        print(f"      {stat['difficulty']}: {stat['count']}")
    
    # 8. Mostrar ejemplos de preguntas
    print("\n📝 Paso 8: Ejemplos de preguntas generadas...")
    sample_questions = saved_questions[:3]
    for q in sample_questions:
        print(f"\n   {'='*70}")
        print(f"   Ronda {q.round_number} - Pregunta {q.question_number}")
        print(f"   Género: {q.genre.name}")
        print(f"   Tipo: {q.question_type} | Dificultad: {q.difficulty} | Puntos: {q.points}")
        print(f"   {'='*70}")
        print(f"   ❓ {q.question_text}")
        print(f"   ✅ {q.correct_answer}")
        if q.fun_fact:
            print(f"   💡 {q.fun_fact}")
    
    # 9. Probar request simulado (como desde frontend)
    print("\n🌐 Paso 9: Simulando request desde frontend...")
    print("   Payload enviado:")
    payload = {
        'include_multiple_choice': True,
        'include_written': True
    }
    print(f"   {json.dumps(payload, indent=6)}")
    
    # Calcular ratios como lo hace la vista
    question_types = {}
    if payload['include_multiple_choice'] and payload['include_written']:
        question_types = {'multiple_choice': 0.7, 'written': 0.3}
    elif payload['include_multiple_choice']:
        question_types = {'multiple_choice': 1.0, 'written': 0.0}
    elif payload['include_written']:
        question_types = {'multiple_choice': 0.0, 'written': 1.0}
    
    print(f"   Ratios calculados: {question_types}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETADO EXITOSAMENTE")
    print("="*80)
    print(f"\n📌 Resumen:")
    print(f"   - Sesión ID: {test_session.id}")
    print(f"   - Equipos: {QuizTeam.objects.filter(session=test_session).count()}")
    print(f"   - Votos: {GenreVote.objects.filter(team__session=test_session).count()}")
    print(f"   - Rondas: {QuizRound.objects.filter(session=test_session).count()}")
    print(f"   - Preguntas: {saved_questions.count()}")
    print(f"\n💡 Para probar el endpoint real:")
    print(f"   curl -X POST http://localhost:8001/api/pub-quiz/{test_session.id}/generate-questions \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d '{{\"include_multiple_choice\": true, \"include_written\": true}}'")
    print()


if __name__ == '__main__':
    try:
        test_question_generation()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
