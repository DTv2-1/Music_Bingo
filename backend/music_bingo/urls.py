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
    from django.http import FileResponse
    return FileResponse(open(FRONTEND_DIR / 'index.html', 'rb'))

def jingle_view(request):
    from django.http import FileResponse
    return FileResponse(open(FRONTEND_DIR / 'jingle.html', 'rb'))

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

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    
    # HTML pages - MUST come before catch-all patterns
    path("jingle-manager", jingle_manager_view, name="jingle-manager-no-slash"),
    path("jingle-manager/", jingle_manager_view, name="jingle-manager"),
    path("jingle", jingle_view, name="jingle-no-slash"),
    path("jingle/", jingle_view, name="jingle"),
    
    # Static files
    re_path(r'^(?P<path>game\.js|styles\.css|config\.js|env-loader\.js|jingle\.js|jingle-manager\.js)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR))),
    re_path(r'^assets/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR / 'assets'))),
    re_path(r'^data/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(DATA_DIR))),
    
    # Index (catch-all) - MUST be last
    path("", index_view),
]

