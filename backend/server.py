"""
Music Bingo Backend Server
Flask API for serving game data and proxying ElevenLabs TTS requests
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes (allows frontend to call backend from different origin)
CORS(app)

# Configuration from environment variables
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

# ============================================================================
# STATIC FILES - Serve frontend and data
# ============================================================================

@app.route('/')
def index():
    """Serve the main game interface"""
    return send_from_directory(FRONTEND_DIR, 'game.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve frontend static files (CSS, JS)"""
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/data/<path:path>')
def serve_data(path):
    """Serve data files (JSON, PDFs)"""
    return send_from_directory(DATA_DIR, path)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Music Bingo API is running'
    })

@app.route('/api/pool', methods=['GET'])
def get_pool():
    """Get the song pool"""
    try:
        import json
        pool_path = os.path.join(DATA_DIR, 'pool.json')
        with open(pool_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({
            'error': 'Pool file not found. Run generate_pool.py first.'
        }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    """Get custom announcements"""
    try:
        import json
        announcements_path = os.path.join(DATA_DIR, 'announcements.json')
        with open(announcements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({
            'venue_name': 'this venue',
            'custom_announcements': [
                'Welcome to Music Bingo!',
                "Don't forget to mark your cards!",
                'Next round starting soon!'
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts', methods=['POST'])
def generate_tts():
    """
    Proxy endpoint for ElevenLabs TTS
    This keeps the API key secure on the server side
    """
    if not ELEVENLABS_API_KEY:
        return jsonify({
            'error': 'ElevenLabs API key not configured on server'
        }), 500
    
    try:
        # Get text from request
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Call ElevenLabs API
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}'
        
        response = requests.post(
            url,
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',  # Modelo más natural y rápido
                'voice_settings': {
                    'stability': 0.35,  # Bajo = más expresivo y melodioso (0-1)
                    'similarity_boost': 0.85,  # Alto = más fiel a la voz original (0-1)
                    'style': 0.5,  # Medio-alto = más estilo y emoción (0-1)
                    'use_speaker_boost': True  # Mejora claridad y calidez
                },
                'optimize_streaming_latency': 1,  # Latencia optimizada sin perder calidad
                'output_format': 'mp3_44100_128'  # Calidad estándar
            }
        )
        
        if not response.ok:
            return jsonify({
                'error': f'ElevenLabs API error: {response.status_code}',
                'details': response.text
            }), response.status_code
        
        # Return audio data
        return response.content, 200, {
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': 'inline'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    # Check if data files exist
    pool_exists = os.path.exists(os.path.join(DATA_DIR, 'pool.json'))
    cards_exist = os.path.exists(os.path.join(DATA_DIR, 'cards', 'music_bingo_cards.pdf'))
    
    print('\n' + '='*60)
    print('🎵 MUSIC BINGO SERVER')
    print('='*60)
    print(f'✓ Backend server starting...')
    print(f'✓ ElevenLabs API key configured: {bool(ELEVENLABS_API_KEY)}')
    print(f'✓ Pool file exists: {pool_exists}')
    print(f'✓ Bingo cards exist: {cards_exist}')
    
    if not pool_exists or not cards_exist:
        print('\n⚠️  WARNING: Missing data files!')
        print('   Run these commands first:')
        print('   python generate_pool.py')
        print('   python generate_cards.py')
    
    print('\n📡 Server will be available at:')
    print('   http://localhost:5001')
    print('='*60 + '\n')
    
    # Run server
    # For development: debug=True, host='0.0.0.0' allows external access
    # For production: Use gunicorn or similar WSGI server
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5001,  # Changed from 5000 (often used by macOS AirPlay)
        debug=True  # Set to False in production
    )
