"""
Pub Quiz TTS & PDF Views — Text-to-Speech and printable answer sheets

Endpoints:
- generate_quiz_tts: Generate TTS audio via ElevenLabs API
- generate_answer_sheets: Generate printable answer sheet PDFs
"""

import os
import logging

from django.http import HttpResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..pub_quiz_models import QuizQuestion, QuizRound
from ..utils.pub_quiz_helpers import get_session_by_code_or_id

logger = logging.getLogger(__name__)

# ElevenLabs Voice IDs
VOICE_MAP = {
    'daniel': 'onwK4e9ZLuTAKqWW03F9',       # Daniel (Male British)
    'charlotte': '21m00Tcm4TlvDq8ikWAM',     # Charlotte (Female British)
    'callum': 'N2lVS1w4EtoT3dr4eOWO',        # Callum (Male British)
    'alice': 'Xb7hH8MSUJpSbSDYk0k2',         # Alice (Female British)
}


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_quiz_tts(request):
    """Generate TTS audio for quiz questions using ElevenLabs streaming API."""
    import requests

    api_key = os.getenv('ELEVENLABS_API_KEY', '')
    if not api_key:
        return Response({'error': 'ElevenLabs API key not configured'}, status=500)

    try:
        text = request.data.get('text', '')
        voice_id_name = request.data.get('voice_id', 'daniel')

        if not text:
            return Response({'error': 'No text provided'}, status=400)

        voice_id = VOICE_MAP.get(voice_id_name, VOICE_MAP['daniel'])
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

        logger.info(f"[TTS] Requesting voice={voice_id_name}, text_len={len(text)}")

        response = requests.post(
            url,
            headers={
                'xi-api-key': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.35,
                    'similarity_boost': 0.85,
                    'style': 0.5,
                    'use_speaker_boost': True,
                },
                'optimize_streaming_latency': 1,
                'output_format': 'mp3_44100_128',
            },
            timeout=45,
            stream=True,
        )

        if not response.ok:
            logger.error(f"[TTS] ElevenLabs error: {response.status_code}")
            return Response({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text,
            }, status=response.status_code)

        def audio_stream():
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        return StreamingHttpResponse(audio_stream(), content_type='audio/mpeg')

    except Exception as e:
        logger.error(f"[TTS] Exception: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_answer_sheets(request):
    """
    Generate printable answer sheet PDFs for a pub quiz session.

    POST /api/pub-quiz/generate-answer-sheets/
    Body: { "session_code": "Y5SWRH0M", "num_sheets": 30 }
    Returns PDF file.
    """
    from generate_pub_quiz_cards import generate_blank_templates

    try:
        session_code = request.data.get('session_code')
        num_sheets = request.data.get('num_sheets', 30)

        if not session_code:
            return Response({'error': 'session_code required'}, status=400)

        session = get_session_by_code_or_id(session_code)
        if not session:
            return Response({'error': 'Session not found'}, status=404)

        venue_name = session.venue_name or "Perfect DJ Pub Quiz"
        session_date = session.created_at.strftime("%d/%m/%Y") if session.created_at else ""

        # Build questions by round
        questions_by_round = []
        rounds = QuizRound.objects.filter(session=session).order_by('round_number')

        for round_obj in rounds:
            questions = QuizQuestion.objects.filter(
                session=session,
                round_number=round_obj.round_number,
            ).order_by('question_number')

            round_questions = []
            for q in questions:
                question_data = {
                    'number': q.question_number,
                    'text': q.question_text,
                    'type': q.question_type,
                    'genre': round_obj.genre.name if round_obj.genre else 'General',
                }
                if q.question_type == 'multiple_choice' and q.options:
                    question_data['options'] = q.options
                round_questions.append(question_data)

            if round_questions:
                questions_by_round.append({
                    'round_number': round_obj.round_number,
                    'genre': round_obj.genre.name if round_obj.genre else 'General',
                    'questions': round_questions,
                })

        if not questions_by_round:
            return Response({'error': 'Please generate quiz questions first before printing answer sheets'}, status=400)

        logger.info(f"[ANSWER_SHEETS] Generating {num_sheets} sheets for session {session_code}")

        pdf_buffer = generate_blank_templates(
            venue_name=venue_name,
            session_date=session_date,
            questions_by_round=questions_by_round,
            num_sheets=num_sheets,
            output_path=None,
        )

        pdf_buffer.seek(0)
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pub_quiz_answer_sheets_{session_code}.pdf"'
        return response

    except Exception as e:
        logger.error(f"[ANSWER_SHEETS] Error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
