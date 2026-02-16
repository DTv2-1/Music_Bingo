"""
Pub Quiz Answer Views — Answer submission, buzzer, scoring, team stats

Endpoints:
- get_question_answer: Get the correct answer for a question
- submit_answer: Submit a single answer
- record_buzz: Record a buzzer press
- submit_all_answers: Batch-submit all answers at end of quiz
- award_points: Manually award/deduct points
- get_team_stats: Get final team statistics
- get_all_team_answers: Get all answers grouped by team (host view)
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..pub_quiz_models import QuizQuestion, QuizTeam, TeamAnswer
from ..utils.pub_quiz_helpers import get_session_by_code_or_id
from ..services.pub_quiz_service import PubQuizService

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_question_answer(request, question_id):
    """Get the correct answer and fun fact for a question."""
    question = get_object_or_404(QuizQuestion, id=question_id)

    return Response({
        'success': True,
        'answer': question.correct_answer,
        'fun_fact': question.fun_fact,
    })


@api_view(['POST'])
def submit_answer(request, question_id):
    """Submit or update a single answer for a team."""
    logger.info(f"[SUBMIT_ANSWER] === Received answer for question_id={question_id} ===")
    logger.info(f"[SUBMIT_ANSWER] Request data: {request.data}")
    
    question = get_object_or_404(QuizQuestion, id=question_id)
    logger.info(f"[SUBMIT_ANSWER] Question found: R{question.round_number}Q{question.question_number} - '{question.question_text[:50]}'")
    logger.info(f"[SUBMIT_ANSWER] Session: {question.session.session_code} (current R{question.session.current_round}Q{question.session.current_question})")
    
    team_id = request.data.get('team_id')
    team = get_object_or_404(QuizTeam, id=team_id)
    answer_text = request.data.get('answer', '')
    is_multiple_choice = request.data.get('is_multiple_choice', False)
    
    logger.info(f"[SUBMIT_ANSWER] Team: '{team.team_name}' (id={team_id}), Answer: '{answer_text}', MC: {is_multiple_choice}")
    logger.info(f"[SUBMIT_ANSWER] Correct answer: '{question.correct_answer}', correct_option: '{question.correct_option}'")

    result = PubQuizService.submit_answer(question, team, answer_text, is_multiple_choice)
    
    logger.info(f"[SUBMIT_ANSWER] Result: is_correct={result['is_correct']}, created={result['created']}")
    
    # Log current answer count for this question (for SSE detection)
    from ..pub_quiz_models import TeamAnswer
    total_answers = TeamAnswer.objects.filter(question=question).count()
    logger.info(f"[SUBMIT_ANSWER] Total answers for this question now: {total_answers}")

    return Response({
        'success': True,
        'message': 'Answer submitted successfully',
        'is_correct': result['is_correct'],
    })


@api_view(['POST'])
def record_buzz(request, question_id):
    """Record a buzzer press for a team on a question."""
    question = get_object_or_404(QuizQuestion, id=question_id)
    team_id = request.data.get('team_id')
    team = get_object_or_404(QuizTeam, id=team_id)

    result = PubQuizService.record_buzz(question, team)

    return Response({
        'success': True,
        'order': result['order'],
        'message': result['message'],
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_all_answers(request, session_id):
    """Batch-submit all answers from a team at the end of the quiz."""
    try:
        session = get_session_by_code_or_id(session_id)
        if not session:
            return Response({'error': 'Session not found'}, status=404)

        team_id = request.data.get('team_id')
        answers = request.data.get('answers', [])

        if not team_id:
            return Response({'error': 'team_id required'}, status=400)

        team = get_object_or_404(QuizTeam, id=team_id)
        saved_count = PubQuizService.submit_batch_answers(session, team, answers)

        logger.info(f"[SUBMIT_ALL] Saved {saved_count}/{len(answers)} answers for team {team.team_name}")

        return Response({
            'success': True,
            'message': f'Submitted {saved_count} answers',
            'saved_count': saved_count,
        })

    except Exception as e:
        logger.error(f"[SUBMIT_ALL] Error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def award_points(request, team_id):
    """Manually award or deduct points for a team."""
    try:
        team = get_object_or_404(QuizTeam, id=team_id)
        points = request.data.get('points', 1)

        team.total_score += points
        team.save()

        return Response({
            'success': True,
            'new_score': team.total_score,
            'message': f'Points updated for {team.team_name}',
        })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_team_stats(request, session_id, team_id):
    """Get final statistics for a team at quiz completion."""
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    try:
        team = QuizTeam.objects.get(id=team_id, session=session)
    except QuizTeam.DoesNotExist:
        return Response({"error": "Team not found"}, status=404)

    stats = PubQuizService.get_team_stats(session, team)

    return Response({'success': True, **stats})


@api_view(['GET'])
def get_all_team_answers(request, session_id):
    """
    Get all answers grouped by team for the host panel.
    Returns each team with their answers per round.
    """
    session = get_session_by_code_or_id(session_id)
    if not session:
        return Response({"error": "Session not found"}, status=404)

    teams = session.teams.all().order_by('-total_score', 'team_name')
    teams_data = []

    for team in teams:
        answers = TeamAnswer.objects.filter(
            team=team,
            question__session=session,
        ).select_related('question', 'question__genre').order_by(
            'question__round_number', 'question__question_number'
        )

        answers_by_round = {}
        correct_count = 0
        total_count = 0

        for ans in answers:
            q = ans.question
            rn = q.round_number
            if rn not in answers_by_round:
                answers_by_round[rn] = {
                    'round_number': rn,
                    'genre': q.genre.name if q.genre else 'General',
                    'answers': [],
                }

            answers_by_round[rn]['answers'].append({
                'question_number': q.question_number,
                'question_text': q.question_text,
                'correct_answer': q.correct_answer,
                'team_answer': ans.answer_text,
                'is_correct': ans.is_correct,
                'points': q.get_points_value(),
                'difficulty': q.difficulty,
            })

            total_count += 1
            if ans.is_correct:
                correct_count += 1

        teams_data.append({
            'team_id': team.id,
            'team_name': team.team_name,
            'table_number': team.table_number,
            'total_score': team.total_score,
            'correct_count': correct_count,
            'total_answered': total_count,
            'rounds': list(answers_by_round.values()),
        })

    return Response({
        'success': True,
        'teams': teams_data,
    })
