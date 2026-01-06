"""
WSGI entry point for production deployment with Gunicorn
"""

from server import app

if __name__ == "__main__":
    app.run()
