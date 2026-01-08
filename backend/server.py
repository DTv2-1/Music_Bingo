"""
Music Bingo Backend Server
Flask API for serving game data and proxying ElevenLabs TTS requests
"""

import os
import json
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
VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')

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

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get public configuration (venue name, etc)"""
    return jsonify({
        'venue_name': VENUE_NAME
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
    """Get custom announcements with venue name"""
    try:
        import json
        announcements_path = os.path.join(DATA_DIR, 'announcements.json')
        with open(announcements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Add venue name from environment
        data['venue_name'] = VENUE_NAME
        return jsonify(data)
    except FileNotFoundError:
        # Return default with venue name from environment
        return jsonify({
            'venue_name': VENUE_NAME,
            'custom_announcements': [
                f'Welcome to Music Bingo at {VENUE_NAME}!',
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

@app.route('/api/announcements-ai')
def get_ai_announcements():
    """Serve AI-generated announcements if available"""
    ai_announcements_path = os.path.join(DATA_DIR, 'announcements_ai.json')
    
    if os.path.exists(ai_announcements_path):
        with open(ai_announcements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    else:
        return jsonify({'error': 'AI announcements not generated yet'}), 404

@app.route('/api/generate-cards', methods=['POST'])
def generate_cards_api():
    """Generate bingo cards with custom venue name and player count"""
    try:
        import subprocess
        import json
        from pathlib import Path
        
        # Get parameters from request
        data = request.get_json()
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        optimal_songs = data.get('optimal_songs', 48)
        
        # Path to generate_cards.py
        script_path = os.path.join(BASE_DIR, 'backend', 'generate_cards.py')
        
        # Run the generator script with venue name and num_players
        result = subprocess.run(
            ['python3', script_path, venue_name, str(num_players)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to generate cards',
                'details': result.stderr
            }), 500
        
        # Get file info
        cards_path = Path(DATA_DIR) / 'cards' / 'music_bingo_cards.pdf'
        file_size_mb = cards_path.stat().st_size / (1024 * 1024)
        
        # Calculate actual number of cards generated (20% margin)
        num_cards_generated = int(num_players * 1.2)
        num_cards_generated = max(10, min(100, num_cards_generated))
        num_pages = (num_cards_generated + 1) // 2  # 2 cards per page
        
        return jsonify({
            'success': True,
            'message': 'Cards generated successfully',
            'venue_name': venue_name,
            'num_players': num_players,
            'optimal_songs': optimal_songs,
            'filename': 'music_bingo_cards.pdf',
            'num_cards': num_cards_generated,
            'num_pages': num_pages,
            'file_size_mb': round(file_size_mb, 2)
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Card generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate-songs', methods=['POST'])
def calculate_songs_api():
    """Calculate optimal songs for given number of players"""
    try:
        data = request.get_json()
        num_players = data.get('num_players', 25)
        target_duration = data.get('target_duration_minutes', 45)
        
        # Import calculation function from generate_cards
        import sys
        sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))
        from generate_cards import calculate_optimal_songs, estimate_game_duration
        
        optimal_songs = calculate_optimal_songs(num_players, target_duration)
        estimated_minutes = estimate_game_duration(optimal_songs)
        
        return jsonify({
            'num_players': num_players,
            'optimal_songs': optimal_songs,
            'estimated_duration_minutes': estimated_minutes,
            'target_duration_minutes': target_duration
        })
        
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
