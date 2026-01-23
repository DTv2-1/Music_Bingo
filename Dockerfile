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

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🔄 Running Django migrations..."\n\
python manage.py migrate --noinput\n\
echo "✅ Migrations complete"\n\
echo ""\n\
echo "🚀 Starting Gunicorn server with preload..."\n\
exec gunicorn --workers 2 --bind 0.0.0.0:8080 --timeout 120 --preload --access-logfile - --error-logfile - --log-level info wsgi:application' > /app/start.sh \
    && chmod +x /app/start.sh

# Run gunicorn with 1 worker (required for in-memory task storage) and 120s timeout
# --access-logfile - enables access logs to stdout
# --error-logfile - enables error logs to stdout  
# --log-level info shows more details
CMD ["/app/start.sh"]
