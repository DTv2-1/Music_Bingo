FROM python:3.11-slim

WORKDIR /app

# Copy Django backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY data/ ./data/
COPY frontend/ ./frontend/

# Expose port
EXPOSE 8080

# Run gunicorn with 1 worker (required for in-memory task storage) and 120s timeout
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8080", "--timeout", "120", "wsgi:application"]
