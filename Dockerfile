FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY data/ ./data/
COPY frontend/assets/perfect-dj-logo.png ./assets/perfect-dj-logo.png

# Expose port
EXPOSE 8080

# Run gunicorn with 120s timeout
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "--timeout", "120", "wsgi:app"]
