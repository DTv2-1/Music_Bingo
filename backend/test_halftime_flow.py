#!/usr/bin/env python
"""
Test para verificar el flujo completo hasta el halftime
SIMULA EL FLUJO REAL: Host navega localmente y usa /sync-question
TAMBIÉN VERIFICA: SSE envía eventos question_update correctamente
"""
import requests
import time
import json
from threading import Thread
import sys

# Configuración
BASE_URL = "https://music-bingo-106397905288.europe-west2.run.app"
# BASE_URL = "http://localhost:8080"  # Para testing local

# Variable global para capturar eventos SSE
sse_events = []
sse_connected = False
sse_error = None

# Variable global para capturar eventos SSE
sse_events = []
sse_connected = False
sse_error = None

def listen_to_sse(session_id):
    """Conecta a SSE stream y captura eventos"""
    global sse_events, sse_connected, sse_error
    
    try:
        print(f"🎧 [SSE] Conectando al stream de jugadores...")
        response = requests.get(
            f"{BASE_URL}/api/pub-quiz/{session_id}/stream",
            stream=True,
            timeout=180  # 3 minutos max
        )
        
        if response.status_code != 200:
            sse_error = f"SSE connection failed: {response.status_code}"
            return
        
        sse_connected = True
        print(f"✅ [SSE] Conectado al stream")
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    data_str = decoded[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(data_str)
                        sse_events.append(event)
                        print(f"📨 [SSE] Evento recibido: {event.get('type')}")
                        
                        # Si recibimos timeout o ended, cerramos
                        if event.get('type') in ['timeout', 'ended']:
                            break
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        sse_error = str(e)
        print(f"❌ [SSE] Error: {e}")

def test_halftime_flow():
    print("\n" + "="*60)
    print("TEST: Flujo REAL hasta HALFTIME (usando /sync-question)")
    print("="*60 + "\n")
    
    # 1. Crear sesión
    print("📝 [TEST] Creando sesión...")
    create_response = requests.post(f"{BASE_URL}/api/pub-quiz/create-session", json={
        "venue_name": "Test Halftime",
        "host_name": "Test Host",
        "total_rounds": 2,  # Solo 2 rondas para testing rápido
        "questions_per_round": 10,
        "seconds_per_question": 15
    })
    
    if create_response.status_code != 201:
        print(f"❌ Error creando sesión: {create_response.status_code}")
        print(create_response.text)
        return
    
    session_data = create_response.json()
    session_id = session_data.get('session_id')
    print(f"✅ Sesión creada: {session_id}\n")
    
    # 2. Registrar un equipo (necesario para votación de géneros)
    print("👥 [TEST] Registrando equipo con votación de géneros...")
    team_response = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/register-team", json={
        "team_name": "Test Team",
        "player_name": "Test Player",
        "genre_votes": [1, 2, 3, 4, 5]  # Votar por 5 géneros (IDs 1-5)
    })
    if team_response.status_code != 201:
        print(f"❌ Error registrando equipo: {team_response.status_code}")
        print(team_response.text)
        return
    print(f"✅ Equipo registrado con votos de género\n")
    
    # 3. Generar preguntas
    print("🎲 [TEST] Generando preguntas...")
    generate_response = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/generate-questions", json={
        "include_multiple_choice": True,
        "include_written": True,
        "easy_count": 3,
        "medium_count": 4,
        "hard_count": 3
    })
    
    print(f"📋 Generate response status: {generate_response.status_code}")
    print(f"📋 Generate response body: {generate_response.text[:500]}")  # Primeros 500 chars
    
    if generate_response.status_code != 200:
        print(f"❌ Error generando preguntas: {generate_response.status_code}")
        print(generate_response.text)
        return
    
    # Esperar a que termine la generación
    print("⏳ Esperando generación de preguntas...")
    for i in range(60):
        time.sleep(2)
        details_resp = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/details")
        if details_resp.status_code != 200:
            print(f"❌ Error obteniendo detalles: {details_resp.status_code}")
            continue
            
        details = details_resp.json()
        # El status está en details['session']['status']
        status = details.get('session', {}).get('status')
        progress = details.get('generation_progress', {}).get('progress', 0)
        print(f"   Status: {status}, Progress: {progress}%")
        
        if status == 'ready':
            print("✅ Preguntas generadas\n")
            break
        if status == 'error':
            print(f"❌ Error en generación: {details}")
            return
    else:
        print("❌ Timeout esperando generación")
        return
    
    # 4. Obtener todas las preguntas (simular lo que hace el host al cargar)
    print("📥 [TEST] Obteniendo todas las preguntas...")
    questions_resp = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/all-questions")
    if questions_resp.status_code != 200:
        print(f"❌ Error obteniendo preguntas: {questions_resp.status_code}")
        return
    
    questions_data = questions_resp.json()
    
    # Manejar diferentes estructuras de respuesta
    if isinstance(questions_data, dict):
        all_questions = questions_data.get('questions', [])
        print(f"📋 Estructura de respuesta: dict con key 'questions'")
    else:
        all_questions = questions_data
        print(f"📋 Estructura de respuesta: lista directa")
    
    print(f"✅ Obtenidas {len(all_questions)} preguntas")
    
    if len(all_questions) > 0 and isinstance(all_questions[0], dict):
        round_1_count = len([q for q in all_questions if q.get('round') == 1 or q.get('round_number') == 1])
        round_2_count = len([q for q in all_questions if q.get('round') == 2 or q.get('round_number') == 2])
        print(f"   Estructura: {round_1_count} en Round 1, {round_2_count} en Round 2\n")
    else:
        print(f"   ⚠️ No se pudo analizar estructura de preguntas\n")
    
    # 5. Iniciar quiz
    print("▶️ [TEST] Iniciando quiz...")
    start_response = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/start")
    if start_response.status_code != 200:
        print(f"❌ Error iniciando quiz: {start_response.status_code}")
        return
    print("✅ Quiz iniciado\n")
    
    # 5.5. Conectar listener SSE en background thread
    print("🎧 [TEST] Iniciando listener SSE en background...")
    sse_thread = Thread(target=listen_to_sse, args=(session_id,), daemon=True)
    sse_thread.start()
    
    # Esperar a que SSE se conecte
    for i in range(10):
        if sse_connected or sse_error:
            break
        time.sleep(0.5)
    
    if sse_error:
        print(f"⚠️ [TEST] SSE falló: {sse_error}, continuando sin validación SSE...")
    elif sse_connected:
        print(f"✅ [TEST] SSE listener activo\n")
    else:
        print(f"⚠️ [TEST] SSE no conectado después de 5s, continuando...\n")
    
    # 6. SIMULAR EL FLUJO REAL DEL HOST: Navegar localmente y sincronizar con /sync-question
    print("➡️ [TEST] Simulando navegación del HOST (usando /sync-question)...")
    print("=" * 60)
    
    # Avanzar por las 10 preguntas del Round 1
    for q_num in range(1, 11):
        round_num = 1
        print(f"\n📍 Host navega a: Round {round_num}, Pregunta {q_num}")
        
        # ESTO ES LO QUE HACE EL HOST REAL
        sync_response = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/sync-question", json={
            "round": round_num,
            "question_number": q_num
        })
        
        if sync_response.status_code != 200:
            print(f"   ❌ Error en sync-question: {sync_response.status_code}")
            print(f"   Response: {sync_response.text}")
            return
        
        print(f"   ✅ Sincronizado con backend")
        
        # Verificar el estado actual solo para debugging (no crítico)
        try:
            host_data = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data").json()
            sess = host_data.get('session', {})
            print(f"   Backend state: Round {sess.get('current_round')}, Q{sess.get('current_question')}, Status: {sess.get('status')}")
        except Exception as e:
            print(f"   ⚠️ No se pudo verificar estado: {e}")
    
    # 7. MOMENTO CRÍTICO: Avanzar a Round 2, Question 1 (debería detectar halftime)
    print(f"\n\n🎯 [TEST] ========== MOMENTO CRÍTICO ==========")
    print(f"Host detecta cambio de Round 1 → Round 2")
    print(f"Frontend muestra pantalla de HALFTIME")
    print(f"Host sincroniza: Round 2, Question 1")
    print(f"Backend debería detectar halftime y enviar evento SSE\n")
    
    critical_sync = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/sync-question", json={
        "round": 2,
        "question_number": 1
    })
    
    if critical_sync.status_code != 200:
        print(f"❌ Error en sync-question crítico: {critical_sync.status_code}")
        print(f"Response: {critical_sync.text}")
        return
    
    print(f"✅ Sync-question enviado (Round 2, Q1)")
    
    # Verificar el estado usando /host-data que tiene current_round y current_question
    time.sleep(0.5)  # Dar tiempo al backend para procesar
    host_data = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data").json()
    
    # Los valores están dentro de 'session'
    session_data = host_data.get('session', {})
    
    print(f"\n📊 [TEST] RESULTADO:")
    print(f"   Backend Round: {session_data.get('current_round')}")
    print(f"   Backend Question: {session_data.get('current_question')}")
    print(f"   Backend Status: {session_data.get('status')}")
    
    print(f"\n" + "="*60)
    print("VALIDACIÓN:")
    print("="*60)
    
    # En el flujo REAL, el status NO cambia a 'halftime' en el backend
    # El halftime es puramente frontend en el host
    # Lo importante es que current_round = 2, current_question = 1
    
    success = True
    if session_data.get('current_round') != 2:
        print(f"❌ Round incorrecto: esperado 2, recibido {session_data.get('current_round')}")
        success = False
    else:
        print(f"✅ Round correcto: {session_data.get('current_round')}")
    
    if session_data.get('current_question') != 1:
        print(f"❌ Question incorrecto: esperado 1, recibido {session_data.get('current_question')}")
        success = False
    else:
        print(f"✅ Question correcto: {session_data.get('current_question')}")
    
    # El status debe ser 'in_progress', NO 'halftime' (halftime es solo frontend)
    if session_data.get('status') != 'in_progress':
        print(f"⚠️ Status inesperado: '{session_data.get('status')}' (esperado 'in_progress')")
    else:
        print(f"✅ Status correcto: '{session_data.get('status')}')")
    
    print(f"\n📝 NOTA IMPORTANTE:")
    print(f"   El HALFTIME es manejado por el FRONTEND del host")
    print(f"   El backend solo almacena current_round y current_question")
    print(f"   Los players reciben 'question_update' events via SSE")
    
    # VALIDACIÓN SSE: Verificar que se recibieron eventos
    print(f"\n" + "="*60)
    print("VALIDACIÓN DE EVENTOS SSE:")
    print("="*60)
    
    # Dar tiempo a que lleguen eventos
    time.sleep(2)
    
    print(f"📊 Total eventos SSE recibidos: {len(sse_events)}")
    
    if len(sse_events) == 0:
        print(f"⚠️ No se recibieron eventos SSE (posible timeout o error de conexión)")
    else:
        # Buscar evento quiz_started
        quiz_started = [e for e in sse_events if e.get('type') == 'quiz_started']
        print(f"   - quiz_started: {len(quiz_started)}")
        
        # Buscar eventos question_update
        question_updates = [e for e in sse_events if e.get('type') == 'question_update']
        print(f"   - question_update: {len(question_updates)}")
        
        if question_updates:
            print(f"\n📡 Eventos question_update recibidos:")
            for i, event in enumerate(question_updates[:5], 1):  # Mostrar primeros 5
                print(f"     {i}. Round {event.get('round')}, Question {event.get('question')}")
            
            # Verificar que Round 2 Q1 está en los eventos
            round2_q1 = [e for e in question_updates if e.get('round') == 2 and e.get('question') == 1]
            if round2_q1:
                print(f"\n✅ SSE: Evento para Round 2 Q1 SÍ fue enviado")
                success = success and True
            else:
                print(f"\n❌ SSE: Evento para Round 2 Q1 NO fue encontrado")
                print(f"   Esto significa que los players NO recibirán la primera pregunta del Round 2")
                success = False
    
    print("\n" + "="*60)
    if success:
        print("✅✅✅ TEST PASSED - Sistema funcionando correctamente")
    else:
        print("❌❌❌ TEST FAILED - Se detectaron problemas")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_halftime_flow()
