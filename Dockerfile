FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Django backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY data/ ./data/
COPY frontend/ ./frontend/

# Expose port
EXPOSE 8080

# Environment variables for better logging
ENV PYTHONUNBUFFERED=1
ENV DJANGO_LOG_LEVEL=INFO

# Create startup script (Django preload handled in wsgi.py)
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🔄 Running Django migrations..."\n\
python manage.py migrate --noinput\n\
echo "✅ Migrations complete"\n\
echo ""\n\
echo "🚀 Starting Gunicorn with gthread workers (threads handle SSE + API concurrently)..."\n\
exec gunicorn --workers 3 --threads 4 --bind 0.0.0.0:8080 --timeout 300 --preload --worker-class gthread --access-logfile - --error-logfile - --log-level info wsgi:application' > /app/start.sh \
    && chmod +x /app/start.sh

# Gunicorn gthread: 3 workers × 4 threads = 12 concurrent request slots
# - SSE streams (host + player) hold 2 threads but other 10 remain free for API
# - gthread works with openai library (no monkey patching like gevent)
# - --timeout 300 prevents SSE threads from being killed (long-lived connections)
# - Threads share memory within a worker = lower footprint than 6 sync workers
CMD ["/app/start.sh"]
