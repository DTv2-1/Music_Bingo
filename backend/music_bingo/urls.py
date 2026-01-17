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

def index_view(request):
    from django.http import FileResponse
    return FileResponse(open(FRONTEND_DIR / 'game.html', 'rb'))

def jingle_view(request):
    from django.http import FileResponse
    return FileResponse(open(FRONTEND_DIR / 'jingle.html', 'rb'))

def jingle_manager_view(request):
    from django.http import FileResponse
    return FileResponse(open(FRONTEND_DIR / 'jingle-manager.html', 'rb'))

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("jingle-manager", jingle_manager_view, name="jingle-manager"),
    path("jingle", jingle_view, name="jingle"),
    path("", index_view),
    re_path(r'^(?P<path>game\.js|styles\.css|config\.js|env-loader\.js|jingle\.js|jingle-manager\.js)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR))),
    re_path(r'^assets/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(FRONTEND_DIR / 'assets'))),
    re_path(r'^data/(?P<path>.*)$', lambda request, path: serve(request, path, document_root=str(DATA_DIR))),
]

