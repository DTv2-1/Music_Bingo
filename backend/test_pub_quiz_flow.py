#!/usr/bin/env python3
"""
Test completo del flujo de Pub Quiz desde el backend
Simula: crear sesión → generar preguntas → start → next (con countdown)
"""
import requests
import time
import json
from datetime import datetime

BASE_URL = "https://music-bingo-106397905288.europe-west2.run.app"
# BASE_URL = "http://localhost:8001"  # Para testing local

def log(emoji, msg):
    """Helper para logging con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {emoji} {msg}")

def test_pub_quiz_flow():
    """Test del flujo completo de pub quiz"""
    
    log("🚀", "=== INICIANDO TEST DE PUB QUIZ ===")
    
    # NOTA: Usar una sesión existente con preguntas ya generadas
    # Para crear una sesión nueva, usa el frontend primero
    session_id = input("🔑 Ingresa un SESSION_ID existente con preguntas generadas (o presiona ENTER para usar última sesión): ").strip()
    
    if not session_id:
        # Intentar obtener la última sesión
        log("🔍", "Buscando última sesión...")
        sessions_resp = requests.get(f"{BASE_URL}/api/pub-quiz/sessions")
        if sessions_resp.status_code == 200:
            data = sessions_resp.json()
            sessions = data.get('sessions', [])
            if sessions:
                # El formato puede ser 'session_code' o 'session_id'
                session_id = sessions[0].get('session_code') or sessions[0].get('session_id') or sessions[0].get('id')
                log("✅", f"Usando última sesión: {session_id}")
            else:
                log("❌", "No hay sesiones disponibles. Crea una desde el frontend primero.")
                return
        else:
            log("❌", f"No se pudo obtener sesiones: {sessions_resp.status_code}")
            return
    
    # 3. Obtener estado actual
    log("📊", "Paso 1: Obteniendo estado de la sesión...")
    host_data_resp = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data")
    host_data = host_data_resp.json()
    log("📈", f"Estado: {host_data.get('session', {}).get('status', 'N/A')}")
    log("📈", f"Pregunta actual: {host_data.get('current_question', {}).get('number', 'N/A')}/{host_data.get('session', {}).get('questions_per_round', 'N/A')}")
    
    if host_data.get('session', {}).get('status') == 'registration':
        log("⚠️", "La sesión está en registro. Asegúrate de que tenga preguntas generadas.")
        return
    
    # 4. Iniciar el quiz (puede ya estar iniciado)
    log("▶️", "Paso 2: Iniciando el quiz...")
    start_resp = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/start")
    if start_resp.status_code == 200:
        start_data = start_resp.json()
        current_q = start_data.get('current_question', {})
        if current_q:
            log("✅", f"Quiz iniciado! Pregunta actual: {current_q.get('text', 'N/A')[:50]}...")
            log("⏰", f"question_started_at: {current_q.get('question_started_at', 'NULL')}")
        else:
            log("⚠️", "Quiz iniciado pero no hay current_question")
    else:
        log("⚠️", f"Error o quiz ya iniciado: {start_resp.status_code}")
    
    # 5. Iniciar countdown
    log("⏱️", "Paso 3: Iniciando countdown...")
    time.sleep(1)  # Pequeña pausa para simular que el TTS terminó
    
    countdown_resp = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/start-countdown")
    if countdown_resp.status_code != 200:
        log("❌", f"Error iniciando countdown: {countdown_resp.status_code}")
        return
    
    countdown_data = countdown_resp.json()
    log("✅", f"Countdown iniciado! question_started_at: {countdown_data.get('question_started_at', 'NULL')}")
    
    # VERIFICAR INMEDIATAMENTE que se guardó en DB
    log("🔍", "Paso 3.5: Verificando que se guardó en DB...")
    immediate_check = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data")
    immediate_data = immediate_check.json()
    immediate_q = immediate_data.get('current_question', {})
    log("   ", f"Verificación inmediata: {immediate_q.get('question_started_at', 'NULL')}")
    
    if not immediate_q.get('question_started_at'):
        log("❌", "¡El timestamp NO se guardó en DB! El bug está en /start-countdown")
        return
    else:
        log("✅", "Timestamp SÍ está en DB, continuando test...")
    
    # 6. Esperar un poco y verificar estado
    log("⏳", "Paso 4: Esperando 3 segundos...")
    time.sleep(3)
    
    host_data_resp = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data")
    host_data = host_data_resp.json()
    current_q = host_data.get('current_question', {})
    session_info = host_data.get('session', {})
    log("📊", f"Estado después de 3s:")
    log("   ", f"- Pregunta: {current_q.get('number', 'N/A')}/{session_info.get('questions_per_round', 'N/A')}")
    log("   ", f"- question_started_at: {current_q.get('question_started_at', 'NULL')}")
    
    if not current_q.get('question_started_at'):
        log("⚠️", "BUG DETECTADO: question_started_at se PERDIÓ después de 3 segundos!")
    else:
        log("✅", "question_started_at se mantiene correctamente")
    
    # 7. Avanzar a siguiente pregunta
    log("⏭️", "Paso 5: Avanzando a siguiente pregunta...")
    next_resp = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/next")
    if next_resp.status_code != 200:
        log("❌", f"Error avanzando: {next_resp.status_code} - {next_resp.text}")
        return
    
    next_data = next_resp.json()
    next_question = next_data.get('current_question', {})
    question_text = next_question.get('text', 'N/A') if isinstance(next_question, dict) else 'N/A'
    log("✅", f"Avanzado! Nueva pregunta: {str(question_text)[:50]}...")
    log("⏰", f"question_started_at después de next: {next_question.get('question_started_at', 'NULL') if isinstance(next_question, dict) else 'NULL'}")
    
    # 8. Iniciar countdown de nueva pregunta
    log("⏱️", "Paso 6: Iniciando countdown de pregunta 2...")
    time.sleep(1)  # Simular TTS
    
    countdown2_resp = requests.post(f"{BASE_URL}/api/pub-quiz/{session_id}/start-countdown")
    if countdown2_resp.status_code != 200:
        log("❌", f"Error iniciando countdown 2: {countdown2_resp.status_code}")
        return
    
    countdown2_data = countdown2_resp.json()
    log("✅", f"Countdown 2 iniciado! question_started_at: {countdown2_data.get('question_started_at', 'NULL')}")
    
    # 9. Verificar estado final
    log("📊", "Paso 7: Estado final...")
    host_data_resp = requests.get(f"{BASE_URL}/api/pub-quiz/{session_id}/host-data")
    host_data = host_data_resp.json()
    current_q = host_data.get('current_question', {})
    session_info = host_data.get('session', {})
    log("   ", f"- Pregunta actual: {current_q.get('number', 'N/A')}/{session_info.get('questions_per_round', 'N/A')}")
    log("   ", f"- Ronda: {session_info.get('current_round', 'N/A')}/{session_info.get('total_rounds', 'N/A')}")
    log("   ", f"- question_started_at: {current_q.get('question_started_at', 'NULL')}")
    
    log("✅", "=== TEST COMPLETADO EXITOSAMENTE ===")
    log("🔗", f"Session ID para inspección manual: {session_id}")
    log("🌐", f"Host URL: {BASE_URL}/pub-quiz-host.html?session={session_id}")

if __name__ == "__main__":
    try:
        test_pub_quiz_flow()
    except Exception as e:
        log("💥", f"ERROR: {e}")
        import traceback
        traceback.print_exc()
