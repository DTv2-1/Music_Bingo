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
    path('upload-logo', views.upload_logo, name='upload-logo'),
    path('tasks/<str:task_id>', views.get_task_status, name='task-status'),
]
