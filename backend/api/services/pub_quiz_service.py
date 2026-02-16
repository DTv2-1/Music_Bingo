"""
Pub Quiz Service — Business logic for the Pub Quiz system

Extracts heavy logic from views so they stay thin.
Handles: session lifecycle, question generation, game flow, scoring.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.utils import timezone
from django.db import transaction
from django.db.models import Count

from ..pub_quiz_models import (
    PubQuizSession, QuizTeam, QuizGenre, QuizQuestion,
    QuizRound, TeamAnswer, GenreVote
)
from ..pub_quiz_generator import PubQuizGenerator, initialize_genres_in_db
from ..utils.pub_quiz_helpers import (
    check_answer_correctness,
    serialize_question_for_player,
    serialize_question_for_host,
    serialize_question_for_start,
    serialize_team_for_leaderboard,
    get_timing_config,
)

logger = logging.getLogger(__name__)


class PubQuizService:
    """
    Service layer for Pub Quiz business logic.
    All methods are static — no instance state needed.
    """

    # ================================================================
    # SESSION MANAGEMENT
    # ================================================================

    @staticmethod
    def create_session(data: dict) -> PubQuizSession:
        """Create a new quiz session and ensure genres are initialized."""
        session = PubQuizSession.objects.create(
            venue_name=data.get('venue_name', 'The Pub'),
            host_name=data.get('host_name', 'Perfect DJ'),
            total_rounds=data.get('total_rounds', 6),
            questions_per_round=data.get('questions_per_round', 10),
            duration_minutes=data.get('duration_minutes', 120),
            status='registration',
        )
        logger.info(f"[CREATE_SESSION] Created session {session.session_code} (ID {session.id})")

        # Auto-initialize genres on first session
        if QuizGenre.objects.count() == 0:
            initialize_genres_in_db()

        return session

    @staticmethod
    def reset_session(session: PubQuizSession) -> None:
        """Reset a quiz session to its initial state."""
        TeamAnswer.objects.filter(team__session=session).delete()
        QuizQuestion.objects.filter(session=session).delete()
        QuizRound.objects.filter(session=session).delete()

        session.teams.all().update(total_score=0)

        session.status = 'registration'
        session.current_round = 0
        session.current_question = 0
        session.generation_progress = None
        session.question_started_at = None
        session.save()
        logger.info(f"[RESET] Session {session.session_code} reset to registration")

    @staticmethod
    def delete_session(session: PubQuizSession) -> str:
        """Delete session and return its venue name for confirmation."""
        venue_name = session.venue_name
        session.delete()
        logger.info(f"[DELETE] Session '{venue_name}' deleted")
        return venue_name

    # ================================================================
    # QUESTION GENERATION
    # ================================================================

    @staticmethod
    def generate_questions(session, request_data: dict) -> dict:
        """
        Generate quiz questions based on genre votes.
        Updates session.generation_progress as it runs.
        
        Returns dict with 'structure' and 'selected_genres'.
        """
        # Parse preferences
        include_mc = request_data.get('include_multiple_choice', True)
        include_written = request_data.get('include_written', True)
        easy_count = request_data.get('easy_count', 3)
        medium_count = request_data.get('medium_count', 4)
        hard_count = request_data.get('hard_count', 3)

        if include_mc and include_written:
            question_types = {'multiple_choice': 0.7, 'written': 0.3}
        elif include_mc:
            question_types = {'multiple_choice': 1.0, 'written': 0.0}
        elif include_written:
            question_types = {'multiple_choice': 0.0, 'written': 1.0}
        else:
            question_types = {'multiple_choice': 0.7, 'written': 0.3}

        difficulty_mix = {'easy': easy_count, 'medium': medium_count, 'hard': hard_count}

        def _update_progress(progress, status_msg):
            session.generation_progress = {'progress': progress, 'status': status_msg}
            session.save(update_fields=['generation_progress'])
            logger.debug(f"[PROGRESS] {progress}% - {status_msg}")

        _update_progress(0, 'starting')

        # Collect genre votes
        genre_votes = GenreVote.objects.filter(
            team__session=session
        ).values('genre_id').annotate(
            vote_count=Count('genre_id')
        ).order_by('-vote_count')
        votes_dict = {v['genre_id']: v['vote_count'] for v in genre_votes}

        generator = PubQuizGenerator()
        selected_genres = generator.select_genres_by_votes(votes_dict, session.total_rounds)
        logger.info(f"[GENERATE] Selected genres: {[g['name'] for g in selected_genres]}")

        _update_progress(10, 'Selecting genres...')

        # Build quiz structure
        structure = generator.create_quiz_structure(
            selected_genres,
            questions_per_round=session.questions_per_round,
            include_halftime=True,
            include_buzzer_round=False,
        )

        _update_progress(20, 'Creating quiz structure...')

        # Create rounds in DB
        total_rounds = len(structure['rounds'])
        rounds_to_generate = []
        for round_data in structure['rounds']:
            genre = QuizGenre.objects.get(name=round_data['genre']['name'])
            QuizRound.objects.create(
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
                'questions_per_round': round_data['questions_per_round'],
            })

        _update_progress(30, 'Generating all questions (this may take 1-2 minutes)...')

        # Parallel question generation
        def _gen_round(round_info):
            return {
                'round_number': round_info['round_number'],
                'genre_obj': round_info['genre_obj'],
                'questions': generator.generate_sample_questions(
                    round_info['genre_name'],
                    round_info['questions_per_round'],
                    question_types=question_types,
                    difficulty_mix=difficulty_mix,
                ),
            }

        all_round_questions = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_gen_round, ri): ri for ri in rounds_to_generate}
            for idx, future in enumerate(as_completed(futures)):
                all_round_questions.append(future.result())
                progress = 30 + int(((idx + 1) / total_rounds) * 60)
                _update_progress(progress, f'Generated {idx + 1}/{total_rounds} rounds...')

        all_round_questions.sort(key=lambda x: x['round_number'])

        # Save questions to DB
        _update_progress(92, 'Saving questions to database...')
        total_saved = 0
        for rd in all_round_questions:
            for qd in rd['questions']:
                QuizQuestion.objects.create(
                    session=session,
                    genre=rd['genre_obj'],
                    round_number=rd['round_number'],
                    question_number=qd['question_number'],
                    question_text=qd['question'],
                    correct_answer=qd['answer'],
                    alternative_answers=qd.get('alternative_answers', []),
                    difficulty=qd.get('difficulty', 'medium'),
                    question_type=qd.get('question_type', 'written'),
                    options=qd.get('options', {}),
                    correct_option=qd.get('correct_option', ''),
                    fun_fact=qd.get('fun_fact', ''),
                    hints=qd.get('hints', ''),
                )
                total_saved += 1
        logger.info(f"[GENERATE] Saved {total_saved} questions")

        _update_progress(95, 'Finalizing quiz...')

        # Mark session ready
        session.status = 'ready'
        session.save()
        for gd in selected_genres:
            genre = QuizGenre.objects.get(name=gd['name'])
            session.selected_genres.add(genre)

        _update_progress(100, 'Complete!')

        return {
            'structure': structure,
            'selected_genres': [g['name'] for g in selected_genres],
        }

    # ================================================================
    # GAME FLOW
    # ================================================================

    @staticmethod
    def start_quiz(session) -> dict:
        """
        Start a quiz session: set status, mark first round, return all questions.
        """
        session.status = 'in_progress'
        session.current_round = 1
        session.current_question = 1
        session.save()

        # Mark first round as started
        first_round = session.rounds.filter(round_number=1).first()
        if first_round:
            first_round.started_at = timezone.now()
            first_round.save()

        # Get all questions
        all_questions = QuizQuestion.objects.filter(
            session=session
        ).order_by('round_number', 'question_number')

        questions_data = [serialize_question_for_start(q) for q in all_questions]

        team_count = session.teams.count()
        welcome_message = (
            f"Welcome to {session.venue_name}'s Pub Quiz! "
            f"We have {team_count} teams competing today. "
            f"Get ready for {session.total_rounds} rounds of trivia fun! "
            f"Good luck everyone!"
        )

        return {
            'welcome_message': welcome_message,
            'all_questions': questions_data,
            'timing': get_timing_config(session),
            'total_rounds': session.total_rounds,
            'questions_per_round': session.questions_per_round,
        }

    @staticmethod
    def advance_to_next_question(session) -> dict:
        """
        Advance the quiz to the next question / round / halftime / completed.
        
        Returns dict with current_round, current_question, status, message.
        """
        # If in halftime, resume
        if session.status == 'halftime':
            session.status = 'in_progress'
            session.save()
            return {
                'current_round': session.current_round,
                'current_question': session.current_question,
                'status': session.status,
                'message': f'Resuming to Round {session.current_round}, Question {session.current_question}',
            }

        total_q = session.questions_per_round

        if session.current_question < total_q:
            # Next question in same round
            session.current_question += 1
            session.question_started_at = None
            session.status = 'in_progress'
            logger.debug(f"[NEXT] Round {session.current_round}, Q{session.current_question}")
        else:
            # End of round — mark it completed
            current_round_obj = session.rounds.filter(round_number=session.current_round).first()
            if current_round_obj:
                current_round_obj.is_completed = True
                current_round_obj.completed_at = timezone.now()
                current_round_obj.save()

            if session.current_round < session.total_rounds:
                session.current_round += 1
                session.current_question = 1
                session.question_started_at = None

                # Check for halftime
                next_round_obj = session.rounds.filter(round_number=session.current_round).first()
                if next_round_obj and next_round_obj.is_halftime_before:
                    session.status = 'halftime'
                    logger.info(f"[NEXT] Halftime before round {session.current_round}")
                else:
                    session.status = 'in_progress'

                if next_round_obj:
                    next_round_obj.started_at = timezone.now()
                    next_round_obj.save()
            else:
                session.status = 'completed'
                logger.info("[NEXT] Quiz completed!")

        session.save()

        return {
            'current_round': session.current_round,
            'current_question': session.current_question,
            'status': session.status,
        }

    # ================================================================
    # ANSWERS & SCORING
    # ================================================================

    @staticmethod
    def submit_answer(question, team, answer_text, is_multiple_choice=False) -> dict:
        """Submit or update a single answer."""
        logger.info(f"[SVC_SUBMIT] Checking correctness: answer='{answer_text}', correct='{question.correct_answer}', option='{question.correct_option}', MC={is_multiple_choice}")
        is_correct = check_answer_correctness(question, answer_text, is_multiple_choice)
        logger.info(f"[SVC_SUBMIT] Correctness result: {is_correct}")

        ans, created = TeamAnswer.objects.get_or_create(
            team=team,
            question=question,
            defaults={
                'answer_text': answer_text,
                'is_correct': is_correct,
            }
        )
        if not created:
            logger.info(f"[SVC_SUBMIT] Updating existing answer (id={ans.id}): '{ans.answer_text}' -> '{answer_text}'")
            ans.answer_text = answer_text
            ans.is_correct = is_correct
            ans.save()
        else:
            logger.info(f"[SVC_SUBMIT] Created new answer (id={ans.id}) for team '{team.team_name}' on Q{question.question_number}")

        return {'is_correct': is_correct, 'created': created}

    @staticmethod
    def submit_batch_answers(session, team, answers: list) -> int:
        """
        Submit a batch of answers at once (end-of-quiz bulk submit).
        Returns number of successfully saved answers.
        """
        saved_count = 0
        for ans_data in answers:
            question_id = ans_data.get('question_id')
            answer_text = ans_data.get('answer', '')
            is_mc = ans_data.get('is_multiple_choice', False)

            try:
                question = QuizQuestion.objects.get(id=question_id, session=session)
                is_correct = check_answer_correctness(question, answer_text, is_mc)

                TeamAnswer.objects.update_or_create(
                    team=team,
                    question=question,
                    defaults={
                        'answer_text': answer_text,
                        'is_correct': is_correct,
                        'submitted_at': timezone.now(),
                    }
                )
                saved_count += 1
            except QuizQuestion.DoesNotExist:
                logger.warning(f"[SUBMIT_ALL] Question {question_id} not found")
                continue

        return saved_count

    @staticmethod
    def record_buzz(question, team) -> dict:
        """Record a buzz for a team on a question. Returns order and message."""
        with transaction.atomic():
            ans, _ = TeamAnswer.objects.get_or_create(
                team=team, question=question
            )
            if ans.buzz_timestamp is None:
                order = TeamAnswer.objects.filter(
                    question=question
                ).exclude(buzz_timestamp=None).count() + 1
                ans.buzz_timestamp = timezone.now()
                ans.buzz_order = order
                ans.save()
                return {'order': order, 'message': f'Buzzed! You are #{order}', 'already_buzzed': False}
            else:
                return {'order': ans.buzz_order, 'message': 'Already buzzed', 'already_buzzed': True}

    # ================================================================
    # STATS & DATA
    # ================================================================

    @staticmethod
    def get_team_stats(session, team) -> dict:
        """Get final statistics for a team, including per-question breakdown."""
        all_teams = session.teams.all().order_by('-total_score', 'team_name')
        rank = None
        for idx, t in enumerate(all_teams, 1):
            if t.id == team.id:
                rank = idx
                break

        # Build per-question breakdown
        all_questions = QuizQuestion.objects.filter(
            session=session
        ).select_related('genre').order_by('round_number', 'question_number')

        team_answers = {
            ta.question_id: ta
            for ta in TeamAnswer.objects.filter(team=team, question__session=session)
        }

        rounds_breakdown = {}
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0

        for q in all_questions:
            rn = q.round_number
            if rn not in rounds_breakdown:
                rounds_breakdown[rn] = {
                    'round_number': rn,
                    'genre': q.genre.name if q.genre else 'General',
                    'questions': [],
                }

            ta = team_answers.get(q.id)
            if ta:
                status = 'correct' if ta.is_correct else 'incorrect'
                team_answer_text = ta.answer_text
                if ta.is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1
            else:
                status = 'unanswered'
                team_answer_text = None
                unanswered_count += 1

            rounds_breakdown[rn]['questions'].append({
                'question_number': q.question_number,
                'question_text': q.question_text,
                'correct_answer': q.correct_answer,
                'team_answer': team_answer_text,
                'status': status,
                'points': q.get_points_value(),
                'difficulty': q.difficulty,
            })

        return {
            'team_name': team.team_name,
            'total_score': team.total_score,
            'bonus_points': team.bonus_points,
            'rank': rank,
            'total_teams': all_teams.count(),
            'answers_submitted': TeamAnswer.objects.filter(team=team).count(),
            'venue_name': session.venue_name,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'unanswered_count': unanswered_count,
            'total_questions': all_questions.count(),
            'rounds': list(rounds_breakdown.values()),
        }

    @staticmethod
    def get_host_update_data(session) -> dict:
        """
        Build the full host_update SSE payload: stats, leaderboard, question, answers.
        """
        teams = session.teams.all()
        current_q = None
        logger.info(f"[HOST_DATA] Building host_update for session {session.session_code}: R{session.current_round}Q{session.current_question}, status={session.status}")
        
        if session.current_round and session.current_question:
            current_q = QuizQuestion.objects.filter(
                session=session,
                round_number=session.current_round,
                question_number=session.current_question,
            ).first()
            if current_q:
                logger.info(f"[HOST_DATA] Current question found: id={current_q.id}, '{current_q.question_text[:50]}'")
            else:
                logger.warning(f"[HOST_DATA] NO question found for R{session.current_round}Q{session.current_question}!")

        # Answer count
        current_answer_count = 0
        recent_answers = []
        if current_q:
            answers_qs = TeamAnswer.objects.filter(
                question=current_q
            ).select_related('team').order_by('-submitted_at')
            current_answer_count = answers_qs.count()
            logger.info(f"[HOST_DATA] Found {current_answer_count} answers for question id={current_q.id}")
            for ans in answers_qs:
                logger.info(f"[HOST_DATA]   Answer: team='{ans.team.team_name}', text='{ans.answer_text}', correct={ans.is_correct}, submitted={ans.submitted_at}")
                recent_answers.append({
                    'team_name': ans.team.team_name,
                    'answer_text': ans.answer_text,
                    'is_correct': ans.is_correct,
                    'submitted_at': ans.submitted_at.isoformat() if ans.submitted_at else None,
                })
        else:
            logger.info(f"[HOST_DATA] No current question — skipping answers")

        # Leaderboard
        leaderboard = [
            serialize_team_for_leaderboard(t)
            for t in teams.order_by('-total_score', 'team_name')
        ]

        # Current question data
        question_data = None
        if session.status in ['in_progress', 'halftime', 'revealing_answer'] and current_q:
            question_data = {
                'id': current_q.id,
                'text': current_q.question_text,
                'answer': current_q.correct_answer if session.status == 'revealing_answer' else None,
                'fun_fact': current_q.fun_fact if session.status == 'revealing_answer' else None,
                'round': current_q.round_number,
                'number': current_q.question_number,
                'type': current_q.question_type,
                'points': current_q.get_points_value(),
                'difficulty': current_q.difficulty,
                'genre': current_q.genre.name if current_q.genre else 'General',
                'options': current_q.options if current_q.question_type == 'multiple_choice' else None,
            }

        return {
            'type': 'host_update',
            'stats': {
                'total_teams': teams.count(),
                'teams_answered': current_answer_count,
                'status': session.status,
                'current_round': session.current_round,
                'current_question': session.current_question,
                'total_rounds': session.total_rounds,
                'questions_per_round': session.questions_per_round,
                'questions_generated': QuizQuestion.objects.filter(session=session).exists(),
                'auto_advance_enabled': session.auto_advance_enabled,
                'auto_advance_seconds': session.auto_advance_seconds,
                'auto_advance_paused': session.auto_advance_paused,
                'question_started_at': session.question_started_at.isoformat() if session.question_started_at else None,
            },
            'leaderboard': leaderboard,
            'question': question_data,
            'recent_answers': recent_answers,
        }
