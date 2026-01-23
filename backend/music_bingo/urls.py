"""
URL configuration for music_bingo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from pathlib import Path

# Serve frontend static files
# In Docker: /app/music_bingo/urls.py -> parent = /app/music_bingo -> parent = /app
BASE_DIR = Path(__file__).resolve().parent.parent  # /app
FRONTEND_DIR = BASE_DIR / 'frontend'  # /app/frontend
DATA_DIR = BASE_DIR / 'data'  # /app/data

# Serve home page at root URL
def index_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'index.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def jingle_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'jingle.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def jingle_manager_view(request):
    from django.http import FileResponse, HttpResponse
    import logging
    logger = logging.getLogger(__name__)
    
    file_path = FRONTEND_DIR / 'jingle-manager.html'
    logger.info(f"🔍 Attempting to serve jingle-manager.html from: {file_path}")
    logger.info(f"   FRONTEND_DIR: {FRONTEND_DIR}")
    logger.info(f"   File exists: {file_path.exists()}")
    
    if not file_path.exists():
        logger.error(f"❌ File not found: {file_path}")
        # List files in FRONTEND_DIR
        try:
            files = list(FRONTEND_DIR.glob('*.html'))
            logger.info(f"   Available HTML files: {[f.name for f in files]}")
        except Exception as e:
            logger.error(f"   Error listing files: {e}")
        return HttpResponse(f"File not found: {file_path}", status=404)
    
    return FileResponse(open(file_path, 'rb'))

def pub_quiz_register_view(request):
    import logging
    import time
    logger = logging.getLogger(__name__)
    
    start = time.time()
    logger.info(f"🔵 START pub_quiz_register_view at {start}")
    
    from django.http import HttpResponse
    logger.info(f"⏱️ Imported HttpResponse in {time.time()-start:.3f}s")
    
    file_start = time.time()
    with open(FRONTEND_DIR / 'pub-quiz-register.html', 'rb') as f:
        content = f.read()
    logger.info(f"⏱️ Read file in {time.time()-file_start:.3f}s (total: {time.time()-start:.3f}s)")
    
    response_start = time.time()
    response = HttpResponse(content, content_type='text/html')
    logger.info(f"⏱️ Created response in {time.time()-response_start:.3f}s (total: {time.time()-start:.3f}s)")
    
    logger.info(f"✅ FINISH pub_quiz_register_view in {time.time()-start:.3f}s")
    return response

def pub_quiz_host_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'pub-quiz-host.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def pub_quiz_sessions_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'pub-quiz-sessions.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def game_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'game.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def karaoke_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'karaoke.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

def karaoke_host_view(request):
    from django.http import HttpResponse
    with open(FRONTEND_DIR / 'karaoke-host.html', 'rb') as f:
        return HttpResponse(f.read(), content_type='text/html')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    
    # HTML pages - MUST come before catch-all patterns
    path("jingle-manager", jingle_manager_view, name="jingle-manager-no-slash"),
    path("jingle-manager/", jingle_manager_view, name="jingle-manager"),
    path("jingle", jingle_view, name="jingle-no-slash"),
    path("jingle/", jingle_view, name="jingle"),
    
    # Pub Quiz pages
    path("pub-quiz-register.html", pub_quiz_register_view, name="pub-quiz-register"),
    path("pub-quiz-host.html", pub_quiz_host_view, name="pub-quiz-host"),
    path("pub-quiz-sessions.html", pub_quiz_sessions_view, name="pub-quiz-sessions"),
    
    # Game pages
    path("game.html", game_view, name="game"),
    path("karaoke.html", karaoke_view, name="karaoke"),
    path("karaoke-host.html", karaoke_host_view, name="karaoke-host"),
    
    # Static files
    re_path(r'^(?P<path>game\.js|styles\.css|config\.js|env-loader\.js|jingle\.js|jingle-manager\.js)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR))),
    re_path(r'^assets/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR / 'assets'))),
    re_path(r'^data/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(DATA_DIR))),
    
    # Index (catch-all) - MUST be last
    path("", index_view),
]

