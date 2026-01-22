"""
Test para comparar los diferentes tipos de preguntas (Multiple Choice vs Written)
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

from api.pub_quiz_generator import PubQuizGenerator
import json


def print_separator(char="=", length=100):
    print(char * length)


def print_question(q, index):
    """Imprime una pregunta de forma bonita"""
    print(f"\n   {'─' * 90}")
    print(f"   Pregunta #{index}")
    print(f"   Tipo: {q.get('question_type', 'N/A').upper()}")
    print(f"   Dificultad: {q.get('difficulty', 'N/A')}")
    print(f"   {'─' * 90}")
    print(f"   ❓ {q['question']}")
    
    if q.get('question_type') == 'multiple_choice':
        print(f"\n   Opciones:")
        options = q.get('options', {})
        for key in sorted(options.keys()):
            marker = "✅" if key == q.get('correct_option') else "  "
            print(f"      {marker} {key}) {options[key]}")
        print(f"\n   Respuesta correcta: {q.get('correct_option')} - {q.get('answer')}")
    else:
        print(f"\n   ✍️  Respuesta: {q.get('answer')}")
        alts = q.get('alternative_answers', [])
        if alts:
            print(f"   Alternativas aceptadas: {', '.join(alts)}")
    
    if q.get('fun_fact'):
        print(f"\n   💡 {q.get('fun_fact')}")


def test_question_types():
    print("\n")
    print_separator("=")
    print("🧪 TEST: TIPOS DE PREGUNTAS (Multiple Choice vs Written)")
    print_separator("=")
    
    generator = PubQuizGenerator()
    genre = "Pop Music"
    count = 5
    
    # Test 1: 100% Multiple Choice
    print("\n\n" + "🎯 " * 30)
    print("TEST 1: 100% MULTIPLE CHOICE (Opciones A, B, C, D)")
    print("🎯 " * 30)
    print(f"\nConfiguración: {{'multiple_choice': 1.0, 'written': 0.0}}")
    print(f"Generando {count} preguntas de {genre}...\n")
    
    mc_questions = generator.generate_sample_questions(
        genre, 
        count=count,
        question_types={'multiple_choice': 1.0, 'written': 0.0}
    )
    
    print(f"✅ Generadas {len(mc_questions)} preguntas")
    
    for i, q in enumerate(mc_questions[:3], 1):  # Mostrar solo 3
        print_question(q, i)
    
    # Estadísticas
    mc_count = sum(1 for q in mc_questions if q.get('question_type') == 'multiple_choice')
    written_count = sum(1 for q in mc_questions if q.get('question_type') == 'written')
    print(f"\n   📊 Estadísticas:")
    print(f"      Multiple Choice: {mc_count}/{len(mc_questions)} ({mc_count/len(mc_questions)*100:.0f}%)")
    print(f"      Written: {written_count}/{len(mc_questions)} ({written_count/len(mc_questions)*100:.0f}%)")
    
    # Verificar que todas tienen opciones
    has_options = all(q.get('options') and len(q.get('options', {})) == 4 for q in mc_questions)
    print(f"      Todas tienen 4 opciones: {'✅ SÍ' if has_options else '❌ NO'}")
    
    
    # Test 2: 100% Written
    print("\n\n" + "✍️  " * 30)
    print("TEST 2: 100% WRITTEN (Para llenar/escribir)")
    print("✍️  " * 30)
    print(f"\nConfiguración: {{'multiple_choice': 0.0, 'written': 1.0}}")
    print(f"Generando {count} preguntas de {genre}...\n")
    
    written_questions = generator.generate_sample_questions(
        genre,
        count=count,
        question_types={'multiple_choice': 0.0, 'written': 1.0}
    )
    
    print(f"✅ Generadas {len(written_questions)} preguntas")
    
    for i, q in enumerate(written_questions[:3], 1):  # Mostrar solo 3
        print_question(q, i)
    
    # Estadísticas
    mc_count = sum(1 for q in written_questions if q.get('question_type') == 'multiple_choice')
    written_count = sum(1 for q in written_questions if q.get('question_type') == 'written')
    print(f"\n   📊 Estadísticas:")
    print(f"      Multiple Choice: {mc_count}/{len(written_questions)} ({mc_count/len(written_questions)*100:.0f}%)")
    print(f"      Written: {written_count}/{len(written_questions)} ({written_count/len(written_questions)*100:.0f}%)")
    
    # Verificar que ninguna tiene opciones
    no_options = all(not q.get('options') or len(q.get('options', {})) == 0 for q in written_questions)
    print(f"      Ninguna tiene opciones: {'✅ SÍ' if no_options else '❌ NO'}")
    
    
    # Test 3: Mix 70/30
    print("\n\n" + "🎲 " * 30)
    print("TEST 3: MIX 70% MULTIPLE CHOICE + 30% WRITTEN")
    print("🎲 " * 30)
    print(f"\nConfiguración: {{'multiple_choice': 0.7, 'written': 0.3}}")
    print(f"Generando {count} preguntas de {genre}...\n")
    
    mixed_questions = generator.generate_sample_questions(
        genre,
        count=count,
        question_types={'multiple_choice': 0.7, 'written': 0.3}
    )
    
    print(f"✅ Generadas {len(mixed_questions)} preguntas")
    
    # Separar por tipo
    mc_mixed = [q for q in mixed_questions if q.get('question_type') == 'multiple_choice']
    written_mixed = [q for q in mixed_questions if q.get('question_type') == 'written']
    
    print(f"\n   Mostrando 2 Multiple Choice:")
    for i, q in enumerate(mc_mixed[:2], 1):
        print_question(q, i)
    
    print(f"\n   Mostrando 2 Written:")
    for i, q in enumerate(written_mixed[:2], 1):
        print_question(q, i)
    
    # Estadísticas
    mc_count = len(mc_mixed)
    written_count = len(written_mixed)
    print(f"\n   📊 Estadísticas:")
    print(f"      Multiple Choice: {mc_count}/{len(mixed_questions)} ({mc_count/len(mixed_questions)*100:.0f}%)")
    print(f"      Written: {written_count}/{len(mixed_questions)} ({written_count/len(mixed_questions)*100:.0f}%)")
    
    
    # Test 4: Comparación lado a lado
    print("\n\n" + "🔍 " * 30)
    print("TEST 4: COMPARACIÓN LADO A LADO")
    print("🔍 " * 30)
    
    print(f"\n{'CAMPO':<25} | {'MULTIPLE CHOICE':<30} | {'WRITTEN':<30}")
    print("─" * 90)
    
    mc_sample = mc_questions[0]
    written_sample = written_questions[0]
    
    fields = ['question', 'question_type', 'answer', 'options', 'correct_option', 
              'alternative_answers', 'difficulty', 'fun_fact']
    
    for field in fields:
        mc_val = mc_sample.get(field, '❌ No existe')
        written_val = written_sample.get(field, '❌ No existe')
        
        # Truncar valores largos
        if isinstance(mc_val, str) and len(mc_val) > 25:
            mc_val = mc_val[:25] + "..."
        if isinstance(written_val, str) and len(written_val) > 25:
            written_val = written_val[:25] + "..."
        
        # Convertir a string
        mc_str = str(mc_val) if not isinstance(mc_val, dict) else f"{len(mc_val)} items"
        written_str = str(written_val) if not isinstance(written_val, dict) else f"{len(written_val)} items"
        
        print(f"{field:<25} | {mc_str:<30} | {written_str:<30}")
    
    
    # Resumen final
    print("\n\n")
    print_separator("=")
    print("📋 RESUMEN DE DIFERENCIAS")
    print_separator("=")
    
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTIPLE CHOICE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ Tiene campo 'options' con 4 opciones: A, B, C, D                        │
│ ✅ Tiene campo 'correct_option' con la letra correcta                      │
│ ✅ Usuario elige de botones/opciones                                       │
│ ✅ Validación automática (A == A)                                          │
│ ✅ Ideal para preguntas con respuestas definidas                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              WRITTEN                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ Campo 'options' vacío {}                                                 │
│ ✅ Campo 'correct_option' vacío ""                                          │
│ ✅ Usuario escribe la respuesta en un input de texto                       │
│ ✅ Tiene 'alternative_answers' para aceptar variaciones                    │
│ ✅ Validación flexible (Paris, paris, París)                               │
│ ✅ Ideal para nombres, lugares, fechas                                     │
└─────────────────────────────────────────────────────────────────────────────┘
    """)
    
    print("\n💡 CASOS DE USO:")
    print("   🎯 Multiple Choice → Preguntas de cultura general, trivias, opciones claras")
    print("   ✍️  Written → Nombres propios, capitales, fechas, respuestas abiertas")
    print("   🎲 Mix 70/30 → Balance ideal para pub quiz (mayoría opciones, algunos desafíos)")
    
    print("\n")
    print_separator("=")
    print("✅ TEST COMPLETADO")
    print_separator("=")
    print("\n")


if __name__ == '__main__':
    try:
        test_question_types()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
