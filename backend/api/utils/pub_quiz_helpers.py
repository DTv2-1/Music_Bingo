"""
Pub Quiz Helper Utilities

Shared helper functions used across all pub quiz view modules:
- Session lookup by code or ID
- Question/Team/Session serialization
- Timing configuration
- Answer correctness checking
"""

import logging
from ..pub_quiz_models import PubQuizSession

logger = logging.getLogger(__name__)


# ============================================================================
# SESSION LOOKUP
# ============================================================================

def get_session_by_code_or_id(session_identifier):
    """
    Get session by session_code (string) or id (int).
    This allows backward compatibility with numeric IDs.
    """
    try:
        session = PubQuizSession.objects.get(session_code=session_identifier)
        logger.debug(f"[GET_SESSION] Found by session_code: {session.id}")
        return session
    except PubQuizSession.DoesNotExist:
        try:
            session = PubQuizSession.objects.get(id=int(session_identifier))
            logger.debug(f"[GET_SESSION] Found by numeric ID: {session.id}")
            return session
        except (PubQuizSession.DoesNotExist, ValueError):
            logger.warning(f"[GET_SESSION] Session not found: '{session_identifier}'")
            return None
    except ValueError:
        logger.warning(f"[GET_SESSION] Invalid session identifier: '{session_identifier}'")
        return None


# ============================================================================
# SERIALIZERS
# ============================================================================

def serialize_question_for_player(question):
    """Serialize a QuizQuestion for player-facing endpoints (no answer)."""
    return {
        'id': question.id,
        'text': question.question_text,
        'round': question.round_number,
        'number': question.question_number,
        'genre': question.genre.name if question.genre else 'General',
        'difficulty': question.difficulty,
        'points': question.get_points_value(),
        'type': question.question_type,
        'options': question.options if question.question_type == 'multiple_choice' else None,
    }


def serialize_question_for_host(question):
    """Serialize a QuizQuestion for host-facing endpoints (includes answer)."""
    data = serialize_question_for_player(question)
    data['answer'] = question.correct_answer
    data['fun_fact'] = question.fun_fact
    data['correct_option'] = question.correct_option if question.question_type == 'multiple_choice' else None
    return data


def serialize_question_for_start(question):
    """Serialize a QuizQuestion for quiz start (includes correct_option for MC grading)."""
    data = serialize_question_for_player(question)
    if question.question_type == 'multiple_choice':
        data['correct_option'] = question.correct_option
    return data


def serialize_team(team):
    """Serialize a QuizTeam for API responses."""
    return {
        'id': team.id,
        'team_name': team.team_name,
        'total_score': team.total_score,
        'bonus_points': team.bonus_points,
        'table_number': team.table_number,
    }


def serialize_team_for_leaderboard(team):
    """Serialize a QuizTeam for leaderboard display."""
    return {
        'team_name': team.team_name,
        'total_score': team.total_score,
        'table_number': team.table_number,
    }


def serialize_session_summary(session):
    """Serialize a PubQuizSession for list/summary views."""
    from ..pub_quiz_models import QuizQuestion
    team_count = session.teams.count()
    question_count = QuizQuestion.objects.filter(session=session).count()
    return {
        'id': session.id,
        'session_code': session.session_code,
        'venue_name': session.venue_name,
        'host_name': session.host_name,
        'date': session.date.isoformat(),
        'status': session.status,
        'team_count': team_count,
        'total_rounds': session.total_rounds,
        'current_round': session.current_round,
        'current_question': session.current_question,
        'questions_per_round': session.questions_per_round,
        'question_count': question_count,
        'duration_minutes': session.duration_minutes,
    }


# ============================================================================
# TIMING CONFIG
# ============================================================================

def get_timing_config(session=None):
    """Get timing configuration dict, optionally enriched with session data."""
    config = {
        'seconds_per_question': 15,
        'halftime_duration': 90,
        'halftime_after_round': 1,
    }
    if session:
        config['total_rounds'] = session.total_rounds
    return config


# ============================================================================
# ANSWER CHECKING
# ============================================================================

def check_answer_correctness(question, answer_text, is_multiple_choice=False):
    """
    Check if an answer is correct for a given question.
    Handles both multiple choice and written answers.
    
    Returns:
        bool: True if the answer is correct
    """
    if not answer_text:
        return False

    if is_multiple_choice and question.question_type == 'multiple_choice':
        return answer_text.upper() == question.correct_option.upper()

    # Written answer: exact match against correct answer and alternatives
    answer_lower = answer_text.lower().strip()
    correct_lower = question.correct_answer.lower().strip()

    if answer_lower == correct_lower:
        return True

    # Check alternative answers
    if question.alternative_answers:
        for alt in question.alternative_answers:
            if answer_lower == alt.lower().strip():
                return True

    return False
