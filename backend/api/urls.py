from django.urls import path
from . import views

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
]
