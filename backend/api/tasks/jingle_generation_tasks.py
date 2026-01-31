"""
Jingle Generation Background Tasks
Handles async jingle generation using services
"""

import logging
import threading
from typing import Callable, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


def run_jingle_generation_task(
    task_id: str,
    task_model,
    jingle_service,
    text: str,
    voice_id: str,
    music_prompt: str,
    voice_settings: dict
) -> None:
    """
    Run jingle generation task in background thread
    
    Args:
        task_id: Unique task identifier
        task_model: TaskStatus model instance
        jingle_service: JingleService instance
        text: TTS text to generate
        voice_id: ElevenLabs voice ID
        music_prompt: Music generation prompt
        voice_settings: Voice configuration dict
    """
    def background_jingle_generation():
        try:
            logger.info(f"Task {task_id}: Starting generation process")
            task_model.status = 'processing'
            task_model.save(update_fields=['status'])
            
            # Progress callback to update task status
            def task_callback(progress: int, step: str):
                """Update task progress and current step"""
                task_model.progress = progress
                task_model.current_step = step
                task_model.save(update_fields=['progress', 'current_step'])
                logger.info(f"Task {task_id}: {step} ({progress}%)")
            
            # Use JingleService for complete jingle creation
            result = jingle_service.create_jingle(
                text=text,
                voice_id=voice_id,
                music_prompt=music_prompt,
                voice_settings=voice_settings,
                task_id=task_id,
                task_callback=task_callback
            )
            
            # Update task status with result
            task_model.status = 'completed'
            task_model.progress = 100
            task_model.current_step = 'completed'
            task_model.result = result
            task_model.completed_at = timezone.now()
            task_model.save(update_fields=['status', 'progress', 'current_step', 'result', 'completed_at'])
            
            logger.info(f"Task {task_id}: COMPLETED successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id}: ERROR - {e}", exc_info=True)
            task_model.status = 'failed'
            task_model.error = str(e)
            task_model.completed_at = timezone.now()
            task_model.save(update_fields=['status', 'error', 'completed_at'])
    
    # Start background thread
    thread = threading.Thread(target=background_jingle_generation)
    thread.daemon = True
    thread.start()
    
    logger.info(f"Task {task_id}: Background thread started")
