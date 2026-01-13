"""
Music Bingo Backend Server
Flask API for serving game data and proxying ElevenLabs TTS requests
"""

import os
import json
import logging
import threading
import uuid
from datetime import datetime
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes (allows frontend to call backend from different origin)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure max upload size (10MB)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

# Configuration from environment variables
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
VENUE_NAME = os.getenv('VENUE_NAME', 'this venue')

# In-memory task storage for async generation (Opción B)
# Format: {task_id: {'status': 'pending'|'processing'|'completed'|'failed', 'result': {...}, 'error': str, 'started_at': timestamp}}
tasks_storage = {}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

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

@app.route('/api/debug', methods=['GET'])
def debug_paths():
    """Debug endpoint to check paths and files"""
    try:
        info = {
            'BASE_DIR': BASE_DIR,
            'DATA_DIR': DATA_DIR,
            'pool_path': os.path.join(DATA_DIR, 'pool.json'),
            'BASE_DIR_exists': os.path.exists(BASE_DIR),
            'DATA_DIR_exists': os.path.exists(DATA_DIR),
            'pool_exists': os.path.exists(os.path.join(DATA_DIR, 'pool.json')),
            'BASE_DIR_contents': os.listdir(BASE_DIR) if os.path.exists(BASE_DIR) else [],
            'DATA_DIR_contents': os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else [],
            'cwd': os.getcwd(),
            '__file__': __file__
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pool', methods=['GET'])
def get_pool():
    """Get the song pool"""
    try:
        import json
        pool_path = os.path.join(DATA_DIR, 'pool.json')
        logger.info(f"Attempting to load pool from: {pool_path}")
        
        with open(pool_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded pool with {len(data.get('songs', []))} songs")
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
        # Get text and voice_id from request
        data = request.get_json()
        text = data.get('text', '')
        voice_id = data.get('voice_id', ELEVENLABS_VOICE_ID)  # Allow frontend to override
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Call ElevenLabs API
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        
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

@app.route('/api/upload-logo', methods=['POST'])
def upload_logo():
    """Upload pub logo and return URL"""
    try:
        if 'logo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['logo']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        # Create logos directory if it doesn't exist
        logos_dir = os.path.join(DATA_DIR, 'logos')
        os.makedirs(logos_dir, exist_ok=True)
        
        # Generate unique filename
        import time
        timestamp = int(time.time())
        safe_filename = f'pub_logo_{timestamp}.{file_ext}'
        file_path = os.path.join(logos_dir, safe_filename)
        
        # Save file
        file.save(file_path)
        
        # Return URL
        logo_url = f'/data/logos/{safe_filename}'
        
        return jsonify({
            'success': True,
            'url': logo_url,
            'filename': safe_filename
        })
        
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
    """Generate bingo cards SYNCHRONOUSLY (will timeout >60s on App Platform)
    
    DEPRECATED: Use /api/generate-cards-async for production to avoid timeouts
    """
    try:
        import subprocess
        import json
        from pathlib import Path
        from datetime import datetime
        
        # Get parameters from request
        data = request.get_json()
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        pub_logo = data.get('pub_logo')  # URL or path to logo
        social_media = data.get('social_media')  # Social media URL
        include_qr = data.get('include_qr', False)  # Include QR code
        game_number = data.get('game_number', 1)  # Game number (default 1)
        game_date = data.get('game_date')  # Optional custom date
        
        # If no date provided, use today's date
        if not game_date:
            game_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # Path to generate_cards.py (in Docker it's in same dir as server.py)
        script_path = os.path.join(os.path.dirname(__file__), 'generate_cards.py')
        
        # Build command with argparse arguments
        cmd = [
            'python3', script_path,
            '--venue_name', venue_name,
            '--num_players', str(num_players),
            '--game_number', str(game_number),
            '--game_date', game_date
        ]
        
        if pub_logo:
            cmd.extend(['--pub_logo', pub_logo])
        
        if social_media:
            cmd.extend(['--social_media', social_media])
        
        if include_qr:
            cmd.extend(['--include_qr', 'true'])
        
        # Run the generator script
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120  # Increased to 120 seconds for ReportLab PDF generation
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to generate cards',
                'details': result.stderr
            }), 500
        
        # Get file info
        cards_path = Path(DATA_DIR) / 'cards' / 'music_bingo_cards.pdf'
        file_size_mb = cards_path.stat().st_size / (1024 * 1024)
        
        # Parse output to get actual numbers
        num_cards_generated = 50  # Fixed from generator
        
        return jsonify({
            'success': True,
            'message': 'Cards generated successfully',
            'venue_name': venue_name,
            'num_players': num_players,
            'game_number': game_number,
            'game_date': game_date,
            'pub_logo': pub_logo if pub_logo else None,
            'social_media': social_media if social_media else None,
            'include_qr': include_qr,
            'filename': 'music_bingo_cards.pdf',
            'num_cards': num_cards_generated,
            'file_size_mb': round(file_size_mb, 2)
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Card generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-cards-async', methods=['POST'])
def generate_cards_async():
    """Generate bingo cards ASYNCHRONOUSLY with background thread (Opción B)
    
    Returns task_id immediately, then client polls /api/tasks/<task_id> for status.
    This avoids 60-second timeout on App Platform.
    """
    try:
        # Get parameters from request
        data = request.get_json()
        venue_name = data.get('venue_name', 'Music Bingo')
        num_players = data.get('num_players', 25)
        pub_logo = data.get('pub_logo')
        social_media = data.get('social_media')
        include_qr = data.get('include_qr', False)
        game_number = data.get('game_number', 1)
        game_date = data.get('game_date')
        
        if not game_date:
            game_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task in storage
        tasks_storage[task_id] = {
            'status': 'pending',
            'result': None,
            'error': None,
            'started_at': time.time(),
            'params': {
                'venue_name': venue_name,
                'num_players': num_players,
                'game_number': game_number,
                'game_date': game_date
            }
        }
        
        # Start background thread for PDF generation
        def background_generation():
            """Background thread that generates PDF without blocking HTTP response"""
            import subprocess
            from pathlib import Path
            
            try:
                # Update status to processing
                tasks_storage[task_id]['status'] = 'processing'
                
                # Path to generate_cards.py
                script_path = os.path.join(os.path.dirname(__file__), 'generate_cards.py')
                
                # Build command
                cmd = [
                    'python3', script_path,
                    '--venue_name', venue_name,
                    '--num_players', str(num_players),
                    '--game_number', str(game_number),
                    '--game_date', game_date
                ]
                
                if pub_logo:
                    cmd.extend(['--pub_logo', pub_logo])
                if social_media:
                    cmd.extend(['--social_media', social_media])
                if include_qr:
                    cmd.extend(['--include_qr', 'true'])
                
                # Run generator (can take 60-120s without timeout)
                result = subprocess.run(
                    cmd,
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minutes max
                )
                
                if result.returncode != 0:
                    tasks_storage[task_id]['status'] = 'failed'
                    tasks_storage[task_id]['error'] = result.stderr
                    return
                
                # Success - get file info
                cards_path = Path(DATA_DIR) / 'cards' / 'music_bingo_cards.pdf'
                file_size_mb = cards_path.stat().st_size / (1024 * 1024)
                
                tasks_storage[task_id]['status'] = 'completed'
                tasks_storage[task_id]['result'] = {
                    'success': True,
                    'message': 'Cards generated successfully',
                    'venue_name': venue_name,
                    'num_players': num_players,
                    'game_number': game_number,
                    'game_date': game_date,
                    'filename': 'music_bingo_cards.pdf',
                    'download_url': '/data/cards/music_bingo_cards.pdf',
                    'num_cards': 50,
                    'file_size_mb': round(file_size_mb, 2),
                    'generation_time': round(time.time() - tasks_storage[task_id]['started_at'], 2)
                }
                
            except subprocess.TimeoutExpired:
                tasks_storage[task_id]['status'] = 'failed'
                tasks_storage[task_id]['error'] = 'Card generation timed out after 3 minutes'
            except Exception as e:
                tasks_storage[task_id]['status'] = 'failed'
                tasks_storage[task_id]['error'] = str(e)
        
        # Start background thread
        thread = threading.Thread(target=background_generation, daemon=True)
        thread.start()
        
        # Return task_id immediately
        return jsonify({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Card generation started in background',
            'check_status_url': f'/api/tasks/{task_id}'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting async generation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Check status of async task (for polling)"""
    if task_id not in tasks_storage:
        return jsonify({
            'error': 'Task not found',
            'task_id': task_id
        }), 404
    
    task = tasks_storage[task_id]
    
    response = {
        'task_id': task_id,
        'status': task['status'],
        'started_at': task['started_at'],
        'elapsed_time': round(time.time() - task['started_at'], 2)
    }
    
    if task['status'] == 'completed':
        response['result'] = task['result']
    elif task['status'] == 'failed':
        response['error'] = task['error']
    
    return jsonify(response)

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
