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
            process = subprocess.Popen(
                cmd,
                cwd=str(base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
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
                        
                        # Update session file with GCS URL for caching
                        session_file = cards_dir / 'current_session.json'
                        if session_file.exists():
                            try:
                                with open(session_file, 'r', encoding='utf-8') as f:
                                    session_data = json.load(f)
                                session_data['pdf_url'] = public_url
                                with open(session_file, 'w', encoding='utf-8') as f:
                                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                                logger.info(f"Task {task_id}: Updated session file with GCS URL")
                            except Exception as session_error:
                                logger.warning(f"Task {task_id}: Could not update session file: {session_error}")
                        
                        task_model.result = {
                            'pdf_url': public_url,
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
