"""
Jingle Service - Orchestrates complete jingle creation
Combines TTS, music generation, and audio mixing
"""

import logging
import io
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from pydub import AudioSegment

from .tts_service import TTSService
from .music_service import MusicGenerationService
from .storage_service import GCSStorageService
from ..utils.config import AppConfig, DATA_DIR

logger = logging.getLogger(__name__)


class JingleService:
    """
    High-level service for jingle creation and management
    
    Features:
    - Complete jingle generation (TTS + Music + Mixing)
    - Jingle file management (list, delete, metadata)
    - Playlist management
    - Audio mixing and processing
    """
    
    def __init__(
        self,
        tts_service: Optional[TTSService] = None,
        music_service: Optional[MusicGenerationService] = None,
        storage_service: Optional[GCSStorageService] = None
    ):
        """
        Initialize Jingle Service with dependencies
        
        Args:
            tts_service: TTS service instance (created if not provided)
            music_service: Music service instance (created if not provided)
            storage_service: Storage service instance (created if not provided)
        """
        self.tts_service = tts_service or TTSService()
        self.music_service = music_service or MusicGenerationService()
        self.storage_service = storage_service or GCSStorageService()
        self.jingles_dir = AppConfig.get_data_path('jingles')
    
    def create_jingle(
        self,
        text: str,
        voice_id: str,
        music_prompt: str,
        voice_settings: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete jingle with TTS + Music + Mixing
        
        Args:
            text: Text for TTS generation
            voice_id: ElevenLabs voice ID
            music_prompt: Music generation prompt
            voice_settings: Voice settings for TTS
            task_id: Optional task ID for filename
            
        Returns:
            dict: Jingle information including filename and metadata
            
        Example:
            >>> service = JingleService()
            >>> result = service.create_jingle(
            ...     text="Happy Hour 2x1 cocktails",
            ...     voice_id="voice123",
            ...     music_prompt="upbeat pub music",
            ...     voice_settings={'stability': 0.5}
            ... )
            >>> print(result['filename'])
        """
        logger.info(f"🎵 Creating jingle: '{text[:50]}...'")
        
        # Step 1: Generate TTS
        logger.info("Step 1/4: Generating TTS...")
        tts_bytes = self.tts_service.generate_audio(
            text=text,
            voice_id=voice_id,
            voice_settings=voice_settings,
            model_id='eleven_multilingual_v2'
        )
        
        # Calculate TTS duration
        tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
        tts_duration_seconds = len(tts_audio) / 1000  # ms to seconds
        logger.info(f"TTS duration: {tts_duration_seconds:.2f}s")
        
        # Step 2: Generate matching music
        music_duration = min(max(int(tts_duration_seconds) + 2, 5), 30)
        logger.info(f"Step 2/4: Generating music ({music_duration}s)...")
        
        music_bytes = self.music_service.generate_music(
            prompt=music_prompt,
            duration_seconds=music_duration,
            use_fallback_on_error=True
        )
        
        # Step 3: Mix audio
        logger.info("Step 3/4: Mixing audio...")
        mixed_audio = self.mix_tts_with_music(tts_bytes, music_bytes)
        
        # Step 4: Save file
        logger.info("Step 4/4: Saving jingle...")
        self.jingles_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        task_suffix = f"_{task_id[:8]}" if task_id else ""
        filename = f'jingle_{timestamp}{task_suffix}.mp3'
        file_path = self.jingles_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(mixed_audio)
        
        # Calculate final duration
        final_audio = AudioSegment.from_mp3(io.BytesIO(mixed_audio))
        actual_duration = len(final_audio) / 1000
        
        logger.info(f"✅ Jingle created: {filename} ({actual_duration:.2f}s)")
        
        return {
            'filename': filename,
            'duration_seconds': actual_duration,
            'size_bytes': len(mixed_audio),
            'file_path': str(file_path),
            'created_at': datetime.now().isoformat()
        }
    
    def mix_tts_with_music(self, tts_bytes: bytes, music_bytes: bytes) -> bytes:
        """
        Mix TTS audio with background music
        
        Algorithm:
        1. Load both audio tracks
        2. Reduce music volume to -15dB
        3. Center TTS over music
        4. Export combined audio
        
        Args:
            tts_bytes: TTS audio as bytes
            music_bytes: Music audio as bytes
            
        Returns:
            bytes: Mixed audio as MP3
        """
        try:
            # Load audio segments
            tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
            music_audio = AudioSegment.from_mp3(io.BytesIO(music_bytes))
            
            # Reduce music volume (background)
            music_audio = music_audio - 15  # Reduce by 15dB
            
            # Calculate positioning to center TTS
            tts_duration_ms = len(tts_audio)
            music_duration_ms = len(music_audio)
            
            if music_duration_ms > tts_duration_ms:
                # Center TTS over music
                start_position = (music_duration_ms - tts_duration_ms) // 2
                mixed = music_audio.overlay(tts_audio, position=start_position)
            else:
                # TTS is longer, center music under TTS
                start_position = (tts_duration_ms - music_duration_ms) // 2
                mixed = tts_audio.overlay(music_audio, position=start_position, gain_during_overlay=-15)
            
            # Export to bytes
            output = io.BytesIO()
            mixed.export(output, format='mp3')
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Audio mixing failed: {e}")
            raise
    
    def list_jingles(self, include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        List all available jingles
        
        Args:
            include_metadata: Include JSON metadata if available
            
        Returns:
            list: List of jingle information dictionaries
            
        Example:
            >>> service = JingleService()
            >>> jingles = service.list_jingles()
            >>> for jingle in jingles:
            ...     print(jingle['filename'], jingle['size'])
        """
        if not self.jingles_dir.exists():
            logger.warning(f"Jingles directory does not exist: {self.jingles_dir}")
            return []
        
        jingles = []
        for file_path in self.jingles_dir.glob('*.mp3'):
            stat = file_path.stat()
            
            jingle_info = {
                'filename': file_path.name,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'size': stat.st_size,
            }
            
            # Load metadata if requested
            if include_metadata:
                metadata_path = file_path.with_suffix('.json')
                if metadata_path.exists():
                    try:
                        import json
                        with open(metadata_path, 'r') as f:
                            jingle_info['metadata'] = json.load(f)
                    except Exception as e:
                        logger.warning(f"Error loading metadata for {file_path.name}: {e}")
                        jingle_info['metadata'] = {}
                else:
                    jingle_info['metadata'] = {}
            
            jingles.append(jingle_info)
        
        # Sort by creation time (newest first)
        jingles.sort(key=lambda x: x['created'], reverse=True)
        
        logger.info(f"Found {len(jingles)} jingles")
        return jingles
    
    def delete_jingle(self, filename: str) -> bool:
        """
        Delete a jingle file and its metadata
        
        Args:
            filename: Name of jingle file to delete
            
        Returns:
            bool: True if deleted successfully
        """
        file_path = self.jingles_dir / filename
        
        if not file_path.exists():
            logger.warning(f"Jingle not found: {filename}")
            return False
        
        try:
            # Delete MP3 file
            file_path.unlink()
            logger.info(f"✅ Deleted jingle: {filename}")
            
            # Delete metadata if exists
            metadata_path = file_path.with_suffix('.json')
            if metadata_path.exists():
                metadata_path.unlink()
                logger.info(f"✅ Deleted metadata: {metadata_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting jingle: {e}")
            return False
    
    def get_jingle_path(self, filename: str) -> Optional[Path]:
        """
        Get full path to a jingle file
        
        Args:
            filename: Jingle filename
            
        Returns:
            Path or None if not found
        """
        file_path = self.jingles_dir / filename
        return file_path if file_path.exists() else None
    
    def get_jingle_metadata(self, filename: str) -> Dict[str, Any]:
        """
        Get metadata for a specific jingle
        
        Args:
            filename: Jingle filename
            
        Returns:
            dict: Metadata dictionary (empty if not found)
        """
        metadata_path = (self.jingles_dir / filename).with_suffix('.json')
        
        if not metadata_path.exists():
            return {}
        
        try:
            import json
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return {}
    
    def save_jingle_metadata(self, filename: str, metadata: Dict[str, Any]) -> bool:
        """
        Save metadata for a jingle
        
        Args:
            filename: Jingle filename
            metadata: Metadata to save
            
        Returns:
            bool: True if saved successfully
        """
        metadata_path = (self.jingles_dir / filename).with_suffix('.json')
        
        try:
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"✅ Saved metadata for {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving metadata: {e}")
            return False
    
    def get_playlist(self) -> Dict[str, Any]:
        """
        Get current jingle playlist configuration
        
        Returns:
            dict: Playlist configuration
        """
        playlist_file = DATA_DIR / 'jingle_playlist.json'
        
        if not playlist_file.exists():
            return {
                'jingles': [],
                'enabled': False,
                'interval': 3
            }
        
        try:
            import json
            with open(playlist_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading playlist: {e}")
            return {
                'jingles': [],
                'enabled': False,
                'interval': 3
            }
    
    def save_playlist(self, jingles: List[str], enabled: bool, interval: int) -> bool:
        """
        Save jingle playlist configuration
        
        Args:
            jingles: List of jingle filenames
            enabled: Whether playlist is enabled
            interval: Play jingle every X rounds
            
        Returns:
            bool: True if saved successfully
        """
        playlist_file = DATA_DIR / 'jingle_playlist.json'
        
        # Validate jingle files exist
        validated_jingles = []
        for filename in jingles:
            if self.get_jingle_path(filename):
                validated_jingles.append(filename)
            else:
                logger.warning(f"Jingle not found, skipping: {filename}")
        
        playlist = {
            'jingles': validated_jingles,
            'enabled': enabled,
            'interval': max(1, int(interval))  # Ensure interval >= 1
        }
        
        try:
            import json
            with open(playlist_file, 'w') as f:
                json.dump(playlist, f, indent=2)
            logger.info(f"✅ Saved playlist: {len(validated_jingles)} jingles, enabled={enabled}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving playlist: {e}")
            return False
