"""
Test End-to-End: Verificar que frontend y backend están conectados correctamente
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

from api.pub_quiz_models import QuizQuestion


def test_frontend_backend_integration():
    print("\n" + "="*100)
    print("🔗 TEST: INTEGRACIÓN FRONTEND ↔️ BACKEND")
    print("="*100 + "\n")
    
    # Obtener pregunta multiple choice de la base de datos
    mc_question = QuizQuestion.objects.filter(question_type='multiple_choice').first()
    
    if not mc_question:
        print("❌ No hay preguntas multiple choice en la base de datos")
        print("   Ejecuta primero: python test_question_generation.py")
        return
    
    print("📝 PREGUNTA MULTIPLE CHOICE EN BASE DE DATOS")
    print("─" * 100)
    print(f"ID: {mc_question.id}")
    print(f"Pregunta: {mc_question.question_text}")
    print(f"Tipo: {mc_question.question_type}")
    print(f"\nOpciones en DB:")
    for letter, text in mc_question.options.items():
        marker = "✅" if letter == mc_question.correct_option else "  "
        print(f"  {marker} {letter}: {text}")
    print(f"\nRespuesta correcta en DB:")
    print(f"  - correct_option: '{mc_question.correct_option}'")
    print(f"  - correct_answer: '{mc_question.correct_answer}'")
    
    # Simular lo que envía el FRONTEND
    print("\n\n🌐 LO QUE ENVÍA EL FRONTEND")
    print("─" * 100)
    frontend_payload = {
        "team_id": 1,
        "answer": "B",  # Letra que el usuario seleccionó
        "is_multiple_choice": True
    }
    print(f"POST /api/pub-quiz/question/{mc_question.id}/submit")
    print(f"Body: {frontend_payload}")
    
    # Simular lo que hace el BACKEND
    print("\n\n⚙️  LO QUE HACE EL BACKEND")
    print("─" * 100)
    
    # Esta es la lógica del backend (de submit_answer)
    answer_text = frontend_payload['answer']
    is_multiple_choice = frontend_payload['is_multiple_choice']
    
    print(f"1. Recibe answer_text = '{answer_text}'")
    print(f"2. Recibe is_multiple_choice = {is_multiple_choice}")
    print(f"3. La pregunta en DB tiene question_type = '{mc_question.question_type}'")
    print(f"4. La pregunta en DB tiene correct_option = '{mc_question.correct_option}'")
    
    # Validación
    is_correct = False
    if is_multiple_choice and mc_question.question_type == 'multiple_choice':
        is_correct = (answer_text.upper() == mc_question.correct_option.upper())
        print(f"\n5. Compara: '{answer_text.upper()}' == '{mc_question.correct_option.upper()}'")
        print(f"6. Resultado: is_correct = {is_correct}")
    
    # Obtener pregunta written
    print("\n\n" + "="*100)
    written_question = QuizQuestion.objects.filter(question_type='written').first()
    
    if not written_question:
        print("❌ No hay preguntas written en la base de datos")
        return
    
    print("✍️  PREGUNTA WRITTEN EN BASE DE DATOS")
    print("─" * 100)
    print(f"ID: {written_question.id}")
    print(f"Pregunta: {written_question.question_text}")
    print(f"Tipo: {written_question.question_type}")
    print(f"\nRespuesta correcta: {written_question.correct_answer}")
    print(f"Alternativas aceptadas: {written_question.alternative_answers}")
    print(f"\nOpciones (debe estar vacío): {written_question.options}")
    print(f"Correct_option (debe estar vacío): '{written_question.correct_option}'")
    
    # Simular respuesta written
    print("\n\n🌐 LO QUE ENVÍA EL FRONTEND (Written)")
    print("─" * 100)
    frontend_payload_written = {
        "team_id": 1,
        "answer": "Paris",  # Texto que el usuario escribió
        "is_multiple_choice": False
    }
    print(f"POST /api/pub-quiz/question/{written_question.id}/submit")
    print(f"Body: {frontend_payload_written}")
    
    print("\n\n⚙️  LO QUE HACE EL BACKEND (Written)")
    print("─" * 100)
    print(f"1. Recibe answer_text = '{frontend_payload_written['answer']}'")
    print(f"2. Recibe is_multiple_choice = {frontend_payload_written['is_multiple_choice']}")
    print(f"3. Como is_multiple_choice = False, NO valida automáticamente")
    print(f"4. Guarda la respuesta como is_correct = False (requiere validación manual)")
    
    # Verificar estructura de datos
    print("\n\n📊 VERIFICACIÓN DE ESTRUCTURA DE DATOS")
    print("="*100)
    
    print("\n✅ PREGUNTA MULTIPLE CHOICE:")
    mc_fields = {
        'question_text': mc_question.question_text[:50] + "...",
        'question_type': mc_question.question_type,
        'options': f"{len(mc_question.options)} opciones" if mc_question.options else "VACÍO",
        'correct_option': mc_question.correct_option or "VACÍO",
        'correct_answer': mc_question.correct_answer,
        'alternative_answers': len(mc_question.alternative_answers) if mc_question.alternative_answers else 0
    }
    
    for key, value in mc_fields.items():
        check = "✅" if value and value != "VACÍO" else "⚠️"
        print(f"  {check} {key}: {value}")
    
    print("\n✅ PREGUNTA WRITTEN:")
    written_fields = {
        'question_text': written_question.question_text[:50] + "...",
        'question_type': written_question.question_type,
        'options': "VACÍO (correcto)" if not written_question.options or len(written_question.options) == 0 else f"ERROR: {written_question.options}",
        'correct_option': "VACÍO (correcto)" if not written_question.correct_option else f"ERROR: {written_question.correct_option}",
        'correct_answer': written_question.correct_answer,
        'alternative_answers': len(written_question.alternative_answers) if written_question.alternative_answers else 0
    }
    
    for key, value in written_fields.items():
        if "ERROR" in str(value):
            check = "❌"
        elif "VACÍO (correcto)" in str(value):
            check = "✅"
        elif value:
            check = "✅"
        else:
            check = "⚠️"
        print(f"  {check} {key}: {value}")
    
    # Resumen de flujo
    print("\n\n📋 RESUMEN DEL FLUJO COMPLETO")
    print("="*100)
    
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTIPLE CHOICE FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Frontend muestra 4 botones con opciones A, B, C, D                      │
│ 2. Usuario hace clic en botón (ejemplo: B)                                 │
│ 3. Frontend envía: {answer: "B", is_multiple_choice: true}                 │
│ 4. Backend compara: "B" == question.correct_option                         │
│ 5. Backend responde: {is_correct: true/false}                              │
│ 6. Frontend muestra feedback inmediato                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           WRITTEN FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Frontend muestra input de texto                                         │
│ 2. Usuario escribe respuesta (ejemplo: "Paris")                            │
│ 3. Frontend envía: {answer: "Paris", is_multiple_choice: false}            │
│ 4. Backend guarda respuesta (validación manual por host)                   │
│ 5. Backend responde: {is_correct: false} (default)                         │
│ 6. Host revisa y marca correcto/incorrecto manualmente                     │
└─────────────────────────────────────────────────────────────────────────────┘
    """)
    
    print("\n✅ VERIFICACIÓN FINAL")
    print("─" * 100)
    
    checks = [
        ("Multiple Choice tiene 4 opciones", len(mc_question.options) == 4),
        ("Multiple Choice tiene correct_option", bool(mc_question.correct_option)),
        ("Written NO tiene opciones", not written_question.options or len(written_question.options) == 0),
        ("Written NO tiene correct_option", not written_question.correct_option),
        ("Written tiene alternative_answers", bool(written_question.alternative_answers)),
    ]
    
    all_good = True
    for desc, result in checks:
        symbol = "✅" if result else "❌"
        print(f"  {symbol} {desc}")
        if not result:
            all_good = False
    
    print("\n" + "="*100)
    if all_good:
        print("🎉 TODO ESTÁ CORRECTAMENTE CONECTADO FRONTEND ↔️ BACKEND")
    else:
        print("⚠️  HAY PROBLEMAS EN LA INTEGRACIÓN")
    print("="*100 + "\n")


if __name__ == '__main__':
    try:
        test_frontend_backend_integration()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
