from django.urls import path
from . import views

# Import karaoke views with explicit error handling
import logging
logger = logging.getLogger(__name__)

try:
    from . import karaoke_views
    logger.info("✅ Successfully imported karaoke_views module")
    logger.info(f"   Available functions: {dir(karaoke_views)}")
except Exception as e:
    logger.error(f"❌ Failed to import karaoke_views: {e}")
    raise

# Pub quiz views are now in views/ package (Phase 3 refactor)
# Imported via `views` module already loaded above

urlpatterns = [
    path('health', views.health_check, name='health'),
    path('pool', views.get_pool, name='pool'),
    path('session', views.get_session, name='session'),
    path('config', views.get_config, name='config'),
    path('announcements', views.get_announcements, name='announcements'),
    path('announcements-ai', views.get_ai_announcements, name='announcements-ai'),
    path('session-announcements', views.get_session_announcements, name='session-announcements'),
    path('generate-cards-async', views.generate_cards_async, name='generate-cards-async'),
    path('generate-tts', views.generate_tts, name='generate-tts'),
    path('generate-tts-preview', views.generate_tts_preview, name='generate-tts-preview'),
    path('generate-track-announcement', views.generate_track_announcement, name='generate-track-announcement'),
    path('tts', views.generate_tts, name='tts'),  # Alias for frontend compatibility
    path('upload-logo', views.upload_logo, name='upload-logo'),
    path('tasks/<str:task_id>', views.get_task_status, name='task-status'),
    # Jingle endpoints
    path('generate-jingle', views.generate_jingle, name='generate-jingle'),
    path('jingle-tasks/<str:task_id>', views.get_jingle_status, name='jingle-status'),
    path('jingles/<str:filename>', views.download_jingle, name='download-jingle'),
    path('jingles', views.list_jingles, name='list-jingles'),
    path('generate-music-preview', views.generate_music_preview, name='generate-music-preview'),
    path('playlist', views.manage_playlist, name='manage-playlist'),
    # Jingle Schedule Management - RESTful pattern
    path('jingle-schedules/active', views.get_active_jingles, name='active-schedules'),  # GET: Filter active
    path('jingle-schedules/<int:schedule_id>/delete', views.delete_jingle_schedule, name='delete-schedule'),  # DELETE
    path('jingle-schedules/<int:schedule_id>', views.update_jingle_schedule, name='update-schedule'),  # PUT: Update
    path('jingle-schedules', views.create_jingle_schedule, name='jingle-schedules'),  # POST: Create, GET: List all
    # Venue Configuration
    path('venue-config/<str:venue_name>', views.venue_config, name='venue-config'),  # GET/POST: Load/save config
    
    # ============================================================
    # PUB QUIZ ENDPOINTS (refactored — views/ package)
    # ============================================================
    # Session CRUD
    path('pub-quiz/sessions', views.pub_quiz_get_sessions, name='pub-quiz-sessions'),
    path('pub-quiz/create-session', views.create_quiz_session, name='pub-quiz-create-session'),
    path('pub-quiz/<str:session_id>/delete', views.pub_quiz_delete_session, name='pub-quiz-delete'),
    path('pub-quiz/bulk-delete', views.bulk_delete_sessions, name='pub-quiz-bulk-delete'),
    path('pub-quiz/<str:session_id>/reset', views.reset_quiz, name='pub-quiz-reset'),
    # Registration & QR
    path('pub-quiz/<str:session_id>/details', views.get_session_details, name='pub-quiz-details'),
    path('pub-quiz/<str:session_id>/check-team', views.check_existing_team, name='pub-quiz-check-team'),
    path('pub-quiz/<str:session_id>/register-team', views.register_team, name='pub-quiz-register-team'),
    path('pub-quiz/<str:session_id>/qr-code', views.generate_qr_code, name='pub-quiz-qr'),
    path('pub-quiz/initialize-genres', views.initialize_quiz_genres, name='initialize_quiz_genres'),
    # Game control
    path('pub-quiz/<str:session_id>/host-data', views.quiz_host_data, name='pub-quiz-host-data'),
    path('pub-quiz/<str:session_id>/start', views.start_quiz, name='pub-quiz-start'),
    path('pub-quiz/<str:session_id>/all-questions', views.get_all_questions, name='pub-quiz-all-questions'),
    path('pub-quiz/<str:session_id>/sync-question', views.sync_question_to_players, name='pub-quiz-sync'),
    path('pub-quiz/<str:session_id>/start-countdown', views.start_countdown, name='pub-quiz-start-countdown'),
    path('pub-quiz/<str:session_id>/next', views.next_question, name='pub-quiz-next'),
    path('pub-quiz/<str:session_id>/end', views.end_quiz, name='pub-quiz-end'),
    path('pub-quiz/<str:session_id>/toggle-auto-advance', views.toggle_auto_advance, name='pub-quiz-toggle-auto'),
    path('pub-quiz/<str:session_id>/pause-auto-advance', views.pause_auto_advance, name='pub-quiz-pause-auto'),
    path('pub-quiz/<str:session_id>/set-auto-advance-time', views.set_auto_advance_time, name='pub-quiz-set-timer'),
    path('pub-quiz/<str:session_id>/generate-questions', views.generate_quiz_questions, name='pub-quiz-generate'),
    # Answers & scoring
    path('pub-quiz/question/<int:question_id>/answer', views.get_question_answer, name='pub-quiz-answer'),
    path('pub-quiz/question/<int:question_id>/submit', views.submit_answer, name='pub-quiz-submit'),
    path('pub-quiz/question/<int:question_id>/buzz', views.record_buzz, name='pub-quiz-buzz'),
    path('pub-quiz/<str:session_id>/submit-answers', views.submit_all_answers, name='pub-quiz-submit-all'),
    path('pub-quiz/team/<int:team_id>/award-points', views.award_points, name='pub_quiz_award_points'),
    path('pub-quiz/<str:session_id>/team-answers', views.get_all_team_answers, name='pub-quiz-team-answers'),
    path('pub-quiz/<str:session_id>/team/<int:team_id>/stats', views.get_team_stats, name='pub-quiz-team-stats'),
    # SSE streams
    path('pub-quiz/<str:session_id>/stream', views.quiz_stream, name='pub-quiz-stream'),
    path('pub-quiz/<str:session_id>/host-stream', views.host_stream, name='pub-quiz-host-stream'),
    # TTS & PDF
    path('pub-quiz/tts', views.generate_quiz_tts, name='pub-quiz-tts'),
    path('pub-quiz/generate-answer-sheets', views.generate_answer_sheets, name='pub-quiz-answer-sheets'),
    
    # ============================================================
    # BINGO SESSION ENDPOINTS
    # ============================================================
    path('bingo/sessions', views.bingo_sessions, name='bingo-sessions'),  # POST: Create, GET: List
    path('bingo/session/<str:session_id>', views.bingo_session_detail, name='bingo-session-detail'),  # GET/PUT/DELETE
    path('bingo/session/<str:session_id>/status', views.update_bingo_session_status, name='update-bingo-session-status'),  # PATCH
    
    # ============================================================
    # KARAOKE ENDPOINTS
    # ============================================================
    # Session Management
    path('karaoke/session', karaoke_views.create_session, name='karaoke-create-session'),  # POST: Create session
    path('karaoke/session/<str:venue_name>', karaoke_views.get_session, name='karaoke-get-session'),  # GET: Get session
    
    # Queue Management
    path('karaoke/queue', karaoke_views.add_to_queue, name='karaoke-add-queue'),  # POST: Add to queue
    path('karaoke/queue/<int:session_id>', karaoke_views.get_queue, name='karaoke-get-queue'),  # GET: Get queue
    path('karaoke/queue/<int:entry_id>', karaoke_views.cancel_entry, name='karaoke-cancel'),  # DELETE: Cancel
    path('karaoke/queue/<int:entry_id>/complete', karaoke_views.complete_entry, name='karaoke-complete'),  # PATCH: Complete
    
    # Karafun API Integration
    path('karaoke/karafun/devices', karaoke_views.list_karafun_devices, name='karafun-devices'),  # GET: List devices
    path('karaoke/karafun/session', karaoke_views.create_karafun_session, name='karafun-create-session'),  # POST: Create Karafun session
    
    # ============================================================
    # BLIND DATE PUB GAME ENDPOINTS
    # ============================================================
    # Session CRUD
    path('blind-date/sessions', views.blind_date_get_sessions, name='blind-date-sessions'),
    path('blind-date/create-session', views.blind_date_create_session, name='blind-date-create-session'),
    path('blind-date/<str:session_id>/delete', views.blind_date_delete_session, name='blind-date-delete'),
    # Registration
    path('blind-date/<str:session_id>/details', views.blind_date_get_session_details, name='blind-date-details'),
    path('blind-date/<str:session_id>/join', views.blind_date_join_session, name='blind-date-join'),
    path('blind-date/<str:session_id>/player', views.blind_date_get_player_data, name='blind-date-player'),
    path('blind-date/<str:session_id>/qr-code', views.blind_date_qr_code, name='blind-date-qr'),
    # Game control
    path('blind-date/<str:session_id>/host-data', views.blind_date_host_data, name='blind-date-host-data'),
    path('blind-date/<str:session_id>/start', views.blind_date_start_game, name='blind-date-start'),
    path('blind-date/<str:session_id>/next', views.blind_date_next_step, name='blind-date-next'),
    path('blind-date/<str:session_id>/submit-answer', views.blind_date_submit_answer, name='blind-date-submit'),
    path('blind-date/<str:session_id>/evaluate', views.blind_date_evaluate_answers, name='blind-date-evaluate'),
    path('blind-date/<str:session_id>/end', views.blind_date_end_game, name='blind-date-end'),
    # Social / Likes
    path('blind-date/<str:session_id>/like', views.blind_date_like_player, name='blind-date-like'),
    path('blind-date/<str:session_id>/matches', views.blind_date_get_matches, name='blind-date-matches'),
    # Test helpers
    path('blind-date/<str:session_id>/seed-test-players', views.blind_date_seed_test_players, name='blind-date-seed-test-players'),
    # SSE Streams
    path('blind-date/<str:session_id>/player-stream', views.blind_date_player_stream, name='blind-date-player-stream'),
    path('blind-date/<str:session_id>/host-stream', views.blind_date_host_stream, name='blind-date-host-stream'),
    # TTS (reuse pub quiz TTS endpoint)
    path('blind-date/tts', views.generate_quiz_tts, name='blind-date-tts'),
]
