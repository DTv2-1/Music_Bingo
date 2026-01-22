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

# Import pub quiz views
try:
    from . import pub_quiz_views
    logger.info("✅ Successfully imported pub_quiz_views module")
except Exception as e:
    logger.error(f"❌ Failed to import pub_quiz_views: {e}")
    pub_quiz_views = None

urlpatterns = [
    path('health', views.health_check, name='health'),
    path('pool', views.get_pool, name='pool'),
    path('config', views.get_config, name='config'),
    path('announcements', views.get_announcements, name='announcements'),
    path('announcements-ai', views.get_ai_announcements, name='announcements-ai'),
    path('generate-cards-async', views.generate_cards_async, name='generate-cards-async'),
    path('generate-tts', views.generate_tts, name='generate-tts'),
    path('generate-tts-preview', views.generate_tts_preview, name='generate-tts-preview'),
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
    # PUB QUIZ ENDPOINTS
    # ============================================================
    path('pub-quiz/sessions', pub_quiz_views.get_sessions, name='pub-quiz-sessions'),
    # Removed: leaderboard endpoint - replaced by SSE
    path('pub-quiz/team/<int:team_id>/award-points', pub_quiz_views.award_points, name='pub_quiz_award_points'),
    path('pub-quiz/initialize-genres', pub_quiz_views.initialize_quiz_genres, name='initialize_quiz_genres'),
    path('pub-quiz/create-session', pub_quiz_views.create_quiz_session, name='pub-quiz-create-session'),
    path('pub-quiz/<int:session_id>/details', pub_quiz_views.get_session_details, name='pub-quiz-details'),
    path('pub-quiz/<int:session_id>/check-team', pub_quiz_views.check_existing_team, name='pub-quiz-check-team'),
    path('pub-quiz/<int:session_id>/register-team', pub_quiz_views.register_team, name='pub-quiz-register-team'),
    path('pub-quiz/<int:session_id>/generate-questions', pub_quiz_views.generate_quiz_questions, name='pub-quiz-generate'),
    path('pub-quiz/<int:session_id>/host-data', pub_quiz_views.quiz_host_data, name='pub-quiz-host-data'),
    path('pub-quiz/<int:session_id>/start', pub_quiz_views.start_quiz, name='pub-quiz-start'),
    path('pub-quiz/<int:session_id>/reset', pub_quiz_views.reset_quiz, name='pub-quiz-reset'),
    path('pub-quiz/<int:session_id>/next', pub_quiz_views.next_question, name='pub-quiz-next'),
    path('pub-quiz/<int:session_id>/stream', pub_quiz_views.quiz_stream, name='pub-quiz-stream'),  # SSE endpoint for players
    path('pub-quiz/<int:session_id>/host-stream', pub_quiz_views.host_stream, name='pub-quiz-host-stream'),  # SSE endpoint for host
    path('pub-quiz/question/<int:question_id>/answer', pub_quiz_views.get_question_answer, name='pub-quiz-answer'),
    path('pub-quiz/question/<int:question_id>/submit', pub_quiz_views.submit_answer, name='pub-quiz-submit'),
    path('pub-quiz/question/<int:question_id>/buzz', pub_quiz_views.record_buzz, name='pub-quiz-buzz'),
    # Removed polling endpoints - replaced by SSE:
    # path('pub-quiz/<int:session_id>/leaderboard', ...)
    # path('pub-quiz/<int:session_id>/stats', ...)
    path('pub-quiz/<int:session_id>/qr-code', pub_quiz_views.generate_qr_code, name='pub-quiz-qr'),
    path('pub-quiz/tts', pub_quiz_views.generate_quiz_tts, name='pub-quiz-tts'),
    
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
]
