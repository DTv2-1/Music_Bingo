"""
Audio Mixer Module for Jingle Generation
Combines TTS audio with AI-generated music background
"""

import io
import logging
from pydub import AudioSegment
from pydub.effects import normalize

logger = logging.getLogger(__name__)


def mix_tts_with_music(tts_bytes, music_bytes, tts_volume=3, music_volume=-12):
    """
    Mix TTS audio with background music
    
    Args:
        tts_bytes: MP3 bytes of TTS audio
        music_bytes: MP3 bytes of background music
        tts_volume: Volume adjustment for TTS in dB (3 = boosted for clarity)
        music_volume: Volume adjustment for music in dB (-12 = very soft background)
    
    Returns:
        bytes: Mixed audio as MP3
    """
    try:
        # Load audio segments
        logger.info("Loading TTS audio...")
        tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
        logger.info(f"TTS duration: {len(tts_audio)}ms ({len(tts_audio)/1000:.1f}s)")
        
        logger.info("Loading background music...")
        bg_audio = AudioSegment.from_mp3(io.BytesIO(music_bytes))
        logger.info(f"Music duration BEFORE adjustments: {len(bg_audio)}ms")
        logger.info(f"Music volume adjustment: {music_volume}dB")
        
        # Apply volume adjustments
        tts_audio = tts_audio + tts_volume
        bg_audio = bg_audio + music_volume
        logger.info(f"Volume adjustments applied - TTS: {tts_volume}dB, Music: {music_volume}dB")
        
        # Apply fade in/out to background music
        logger.info("Applying fade effects...")
        bg_audio = bg_audio.fade_in(500).fade_out(500)
        logger.info(f"Fade effects applied - Music duration: {len(bg_audio)}ms ({len(bg_audio)/1000:.1f}s)")
        
        # Music should be at least as long as TTS
        if len(bg_audio) < len(tts_audio):
            logger.warning(f"Background music shorter than TTS, extending...")
            # Loop the background music if needed
            repetitions = (len(tts_audio) // len(bg_audio)) + 1
            bg_audio = bg_audio * repetitions
            bg_audio = bg_audio[:len(tts_audio)]
        
        logger.info(f"Final music duration: {len(bg_audio)}ms ({len(bg_audio)/1000:.1f}s)")
        
        # Overlay TTS on top of background music (both start at position 0)
        logger.info("Mixing audio tracks...")
        logger.info(f"Final pre-mix - TTS: {len(tts_audio)}ms, Music: {len(bg_audio)}ms")
        
        # Always start TTS at position 0 (beginning of music)
        mixed = bg_audio.overlay(tts_audio, position=0)
        
        logger.info(f"Mixed audio duration: {len(mixed)}ms")
        
        # No normalization - preserve volume balance between voice and music
        logger.info(f"Final jingle duration: {len(mixed)}ms ({len(mixed)/1000:.1f}s)")
        
        # Export to MP3
        logger.info("Exporting final mix...")
        output = io.BytesIO()
        mixed.export(output, format="mp3", bitrate="128k")
        
        output.seek(0)
        result = output.getvalue()
        
        logger.info(f"Successfully mixed audio: {len(result)} bytes")
        return result
        
    except Exception as e:
        logger.error(f"Error mixing audio: {e}", exc_info=True)
        raise


def validate_audio(audio_bytes, max_duration_ms=15000):
    """
    Validate audio file
    
    Args:
        audio_bytes: Audio data in bytes
        max_duration_ms: Maximum duration in milliseconds
    
    Returns:
        dict: Audio info (duration, channels, sample_rate)
    
    Raises:
        ValueError: If audio is invalid
    """
    try:
        audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        
        duration_ms = len(audio)
        if duration_ms > max_duration_ms:
            raise ValueError(f"Audio too long: {duration_ms}ms (max: {max_duration_ms}ms)")
        
        return {
            'duration_ms': duration_ms,
            'duration_seconds': duration_ms / 1000,
            'channels': audio.channels,
            'sample_rate': audio.frame_rate,
            'sample_width': audio.sample_width
        }
        
    except Exception as e:
        logger.error(f"Error validating audio: {e}")
        raise ValueError(f"Invalid audio file: {e}")
