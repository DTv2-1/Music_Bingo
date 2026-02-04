"""
Card Generation Background Tasks
Handles async card generation using subprocess
"""

import json
import logging
import subprocess
import threading
from pathlib import Path
from django.utils import timezone
from api.services.storage_service import upload_to_gcs

logger = logging.getLogger(__name__)


def run_card_generation_task(task_id: str, task_model, cmd: list, base_dir: Path) -> None:
    """
    Run card generation task in background thread
    
    Args:
        task_id: Unique task identifier
        task_model: TaskStatus model instance
        cmd: Command list to execute
        base_dir: Base directory for command execution
    """
    def background_task():
        try:
            logger.info(f"Task {task_id}: Processing started")
            task_model.status = 'processing'
            task_model.save(update_fields=['status'])
            
            logger.info(f"Task {task_id}: Running command: {' '.join(cmd)}")
            
            # Run with real-time output capture for progress tracking
            # Use bufsize=1 for line buffering and universal_newlines for text mode
            process = subprocess.Popen(
                cmd,
                cwd=str(base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # Read output line by line for progress tracking
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    stdout_lines.append(line)
                    logger.info(f"Task {task_id}: {line}")
                    
                    # Parse progress from output
                    if 'progress' in line.lower() or '%' in line:
                        try:
                            # Try to extract percentage from line
                            if '%' in line:
                                pct_str = line.split('%')[0].split()[-1]
                                progress = int(float(pct_str))
                                task_model.progress = min(progress, 95)  # Cap at 95 until complete
                                task_model.save(update_fields=['progress'])
                        except (ValueError, IndexError):
                            pass
            
            # Capture any remaining stderr
            stderr = process.stderr.read()
            if stderr:
                stderr_lines.append(stderr)
                logger.warning(f"Task {task_id}: stderr: {stderr}")
            
            # Wait for completion
            return_code = process.wait()
            
            if return_code == 0:
                # Success - find generated PDF
                task_model.progress = 100
                task_model.status = 'completed'
                
                # Try to find the generated PDF
                cards_dir = base_dir / 'data' / 'cards'
                pdf_files = sorted(cards_dir.glob('*.pdf'), key=lambda x: x.stat().st_mtime, reverse=True)
                
                if pdf_files:
                    latest_pdf = pdf_files[0]
                    
                    # Upload PDF to Google Cloud Storage
                    try:
                        logger.info(f"Task {task_id}: Uploading {latest_pdf.name} to GCS...")
                        public_url = upload_to_gcs(
                            str(latest_pdf),
                            f'cards/{latest_pdf.name}'
                        )
                        
                        # Update session file with GCS URL and upload to GCS
                        session_file = cards_dir / 'current_session.json'
                        session_json_url = None
                        session_data = None
                        
                        if session_file.exists():
                            try:
                                with open(session_file, 'r', encoding='utf-8') as f:
                                    session_data = json.load(f)
                                session_data['pdf_url'] = public_url
                                
                                # Save updated session file locally
                                with open(session_file, 'w', encoding='utf-8') as f:
                                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                                
                                # Upload session file to GCS with unique name
                                venue_safe = session_data.get('venue_name', 'venue').replace(' ', '_').replace('/', '_')
                                players = session_data.get('num_players', 25)
                                game_num = session_data.get('game_number', 1)
                                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                                session_filename = f'sessions/{venue_safe}_{players}p_game{game_num}_{timestamp}.json'
                                
                                logger.info(f"Task {task_id}: Uploading session file to GCS as {session_filename}...")
                                session_json_url = upload_to_gcs(
                                    str(session_file),
                                    session_filename
                                )
                                logger.info(f"Task {task_id}: Session file uploaded to {session_json_url}")
                                
                                # Update BingoSession in database with song_pool and pdf_url
                                session_id = task_model.metadata.get('session_id') if task_model.metadata else None
                                logger.info(f"Task {task_id}: Attempting to update BingoSession {session_id}")
                                
                                if session_id:
                                    try:
                                        from api.models import BingoSession
                                        bingo_session = BingoSession.objects.get(session_id=session_id)
                                        logger.info(f"Task {task_id}: Found BingoSession {session_id}")
                                        logger.info(f"   Venue: {bingo_session.venue_name}")
                                        logger.info(f"   Current song_pool size: {len(bingo_session.song_pool)}")
                                        
                                        songs_to_save = session_data.get('songs', [])
                                        logger.info(f"   New song_pool size: {len(songs_to_save)}")
                                        
                                        bingo_session.song_pool = songs_to_save
                                        bingo_session.pdf_url = public_url
                                        bingo_session.save(update_fields=['song_pool', 'pdf_url'])
                                        
                                        logger.info(f"Task {task_id}: ✅ Updated BingoSession {session_id}")
                                        logger.info(f"   Saved {len(songs_to_save)} songs to database")
                                        logger.info(f"   PDF URL: {public_url}")
                                        
                                        # Verify save
                                        bingo_session.refresh_from_db()
                                        logger.info(f"   Verification: song_pool now has {len(bingo_session.song_pool)} songs")
                                    except Exception as db_error:
                                        logger.error(f"Task {task_id}: ❌ Could not update BingoSession: {db_error}", exc_info=True)
                                else:
                                    logger.warning(f"Task {task_id}: No session_id in metadata - cannot update database")
                                
                            except Exception as session_error:
                                logger.warning(f"Task {task_id}: Could not upload session file: {session_error}")
                        
                        task_model.result = {
                            'pdf_url': public_url,
                            'session_url': session_json_url,
                            'session_data': session_data,  # Include full session data in response
                            'session_id': task_model.metadata.get('session_id') if task_model.metadata else None,
                            'filename': latest_pdf.name,
                            'message': 'Cards generated and uploaded successfully'
                        }
                        logger.info(f"Task {task_id}: SUCCESS - Uploaded to {public_url}")
                        
                    except Exception as upload_error:
                        # If upload fails, still provide local path as fallback
                        logger.error(f"Task {task_id}: Upload failed - {upload_error}")
                        task_model.result = {
                            'pdf_url': f'/api/cards/{latest_pdf.name}',
                            'filename': latest_pdf.name,
                            'message': 'Cards generated but upload failed',
                            'error': str(upload_error)
                        }
                else:
                    task_model.result = {
                        'message': 'Cards generated but PDF not found'
                    }
                    logger.warning(f"Task {task_id}: Completed but no PDF found")
                
                task_model.completed_at = timezone.now()
                task_model.save(update_fields=['progress', 'status', 'result', 'completed_at'])
                
            else:
                # Failed
                error_msg = f"Card generation failed with return code {return_code}"
                if stderr_lines:
                    error_msg += f": {' '.join(stderr_lines)}"
                
                task_model.status = 'failed'
                task_model.error = error_msg
                task_model.completed_at = timezone.now()
                task_model.save(update_fields=['status', 'error', 'completed_at'])
                
                logger.error(f"Task {task_id}: FAILED - {error_msg}")
                
        except Exception as e:
            logger.error(f"Task {task_id}: ERROR - {e}", exc_info=True)
            task_model.status = 'failed'
            task_model.error = str(e)
            task_model.completed_at = timezone.now()
            task_model.save(update_fields=['status', 'error', 'completed_at'])
    
    # Start background thread
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    
    logger.info(f"Task {task_id}: Background thread started")
