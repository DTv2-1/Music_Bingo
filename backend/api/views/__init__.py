"""
Modular Views Package

This package organizes API views by domain:
- core_views: Health check, pool data, task status, config
- card_views: Card generation and logo upload
- tts_views: Text-to-Speech operations and announcements
- jingle_views: Jingle generation, listing, and playlist management
- schedule_views: Jingle schedule CRUD operations
- venue_views: Venue-specific configuration
- session_views: Bingo session management
"""

# Core utilities
from .core_views import (
    health_check,
    get_pool,
    get_session,
    get_task_status,
    get_config
)

# Card generation
from .card_views import (
    generate_cards_async,
    upload_logo
)

# Text-to-Speech
from .tts_views import (
    generate_tts,
    generate_tts_preview,
    get_announcements,
    get_ai_announcements,
    get_session_announcements,
    generate_track_announcement
)

# Jingle management
from .jingle_views import (
    generate_jingle,
    get_jingle_status,
    download_jingle,
    generate_music_preview,
    list_jingles,
    manage_playlist
)

# Schedule management
from .schedule_views import (
    create_jingle_schedule,
    get_active_jingles,
    update_jingle_schedule,
    delete_jingle_schedule
)

# Venue configuration
from .venue_views import (
    venue_config
)

# Session management
from .session_views import (
    bingo_sessions,
    bingo_session_detail,
    update_bingo_session_status
)

# Pub Quiz — Session CRUD
from .pub_quiz_session_views import (
    get_sessions as pub_quiz_get_sessions,
    create_quiz_session,
    delete_session as pub_quiz_delete_session,
    bulk_delete_sessions,
    reset_quiz,
)

# Pub Quiz — Registration & QR
from .pub_quiz_registration_views import (
    get_session_details,
    check_existing_team,
    register_team,
    generate_qr_code,
    initialize_quiz_genres,
)

# Pub Quiz — Game control
from .pub_quiz_game_views import (
    quiz_host_data,
    start_quiz,
    get_all_questions,
    sync_question_to_players,
    start_countdown,
    next_question,
    end_quiz,
    toggle_auto_advance,
    pause_auto_advance,
    set_auto_advance_time,
    generate_quiz_questions,
)

# Pub Quiz — Answers & scoring
from .pub_quiz_answer_views import (
    get_question_answer,
    submit_answer,
    record_buzz,
    submit_all_answers,
    award_points,
    get_team_stats,
    get_all_team_answers,
)

# Pub Quiz — SSE streams
from .pub_quiz_stream_views import (
    quiz_stream,
    host_stream,
)

# Pub Quiz — TTS & PDF
from .pub_quiz_tts_views import (
    generate_quiz_tts,
    generate_answer_sheets,
)

# ============================================================
# BLIND DATE PUB GAME
# ============================================================
from .blind_date_session_views import (
    get_sessions as blind_date_get_sessions,
    create_session as blind_date_create_session,
    delete_session as blind_date_delete_session,
    get_session_details as blind_date_get_session_details,
    join_session as blind_date_join_session,
    get_player_data as blind_date_get_player_data,
    generate_qr_code as blind_date_qr_code,
    seed_test_players as blind_date_seed_test_players,
)

from .blind_date_game_views import (
    start_game as blind_date_start_game,
    host_data as blind_date_host_data,
    next_step as blind_date_next_step,
    submit_answer as blind_date_submit_answer,
    evaluate_answers as blind_date_evaluate_answers,
    like_player as blind_date_like_player,
    get_matches as blind_date_get_matches,
    end_game as blind_date_end_game,
)

from .blind_date_stream_views import (
    player_stream as blind_date_player_stream,
    host_stream as blind_date_host_stream,
)

__all__ = [
    # Core
    'health_check',
    'get_pool',
    'get_session',
    'get_task_status',
    'get_config',
    # Card
    'generate_cards_async',
    'upload_logo',
    # TTS
    'generate_tts',
    'generate_tts_preview',
    'get_announcements',
    'get_ai_announcements',
    # Jingle
    'generate_jingle',
    'get_jingle_status',
    'download_jingle',
    'generate_music_preview',
    'list_jingles',
    'manage_playlist',
    # Schedule
    'create_jingle_schedule',
    'get_active_jingles',
    'update_jingle_schedule',
    'delete_jingle_schedule',
    # Venue
    'venue_config',
    # Session
    'bingo_sessions',
    'bingo_session_detail',
    'update_bingo_session_status',
    # Pub Quiz — Session
    'pub_quiz_get_sessions',
    'create_quiz_session',
    'pub_quiz_delete_session',
    'bulk_delete_sessions',
    'reset_quiz',
    # Pub Quiz — Registration
    'get_session_details',
    'check_existing_team',
    'register_team',
    'generate_qr_code',
    'initialize_quiz_genres',
    # Pub Quiz — Game
    'quiz_host_data',
    'start_quiz',
    'get_all_questions',
    'sync_question_to_players',
    'start_countdown',
    'next_question',
    'toggle_auto_advance',
    'pause_auto_advance',
    'set_auto_advance_time',
    'generate_quiz_questions',
    # Pub Quiz — Answers
    'get_question_answer',
    'submit_answer',
    'record_buzz',
    'submit_all_answers',
    'award_points',
    'get_team_stats',
    'get_all_team_answers',
    # Pub Quiz — Streams
    'quiz_stream',
    'host_stream',
    # Pub Quiz — TTS & PDF
    'generate_quiz_tts',
    'generate_answer_sheets',
    # Blind Date
    'blind_date_get_sessions',
    'blind_date_create_session',
    'blind_date_delete_session',
    'blind_date_get_session_details',
    'blind_date_join_session',
    'blind_date_get_player_data',
    'blind_date_qr_code',
    'blind_date_start_game',
    'blind_date_host_data',
    'blind_date_next_step',
    'blind_date_submit_answer',
    'blind_date_evaluate_answers',
    'blind_date_like_player',
    'blind_date_get_matches',
    'blind_date_end_game',
    'blind_date_player_stream',
    'blind_date_host_stream',
    'blind_date_seed_test_players',
]
