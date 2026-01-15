"""
Audio Mixer Module for Jingle Generation
Combines TTS audio with AI-generated music background
"""

import io
import logging
from pydub import AudioSegment
from pydub.effects import normalize

logger = logging.getLogger(__name__)


def mix_tts_with_music(tts_bytes, music_bytes, tts_volume=0, music_volume=-6):
    """
    Mix TTS audio with background music
    
    Args:
        tts_bytes: MP3 bytes of TTS audio
        music_bytes: MP3 bytes of background music
        tts_volume: Volume adjustment for TTS in dB (0 = no change)
        music_volume: Volume adjustment for music in dB (-6 = half volume, clearly audible)
    
    Returns:
        bytes: Mixed audio as MP3
    """
    try:
        # Load audio segments
        logger.info("Loading TTS audio...")
        tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
        
        # Trim TTS if longer than 9 seconds to ensure final output is 10s
        max_tts_duration = 9000  # 9 seconds in milliseconds
        if len(tts_audio) > max_tts_duration:
            logger.warning(f"TTS too long ({len(tts_audio)}ms), trimming to {max_tts_duration}ms")
            tts_audio = tts_audio[:max_tts_duration]
        
        logger.info(f"TTS duration: {len(tts_audio)}ms")
        
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
        logger.info(f"Fade effects applied - Music duration AFTER fade: {len(bg_audio)}ms")
        
        # Ensure background music is at least 10 seconds (target duration)
        target_duration = 10000  # 10 seconds in milliseconds
        if len(bg_audio) < target_duration:
            logger.warning(f"Background music too short ({len(bg_audio)}ms), extending to {target_duration}ms...")
            # Loop the background music if needed
            repetitions = (target_duration // len(bg_audio)) + 1
            bg_audio = bg_audio * repetitions
        
        # Trim background to exactly 10 seconds
        bg_audio = bg_audio[:target_duration]
        logger.info(f"Music duration set to target: {len(bg_audio)}ms")
        
        # Overlay TTS on top of background music (centered if TTS is shorter)
        logger.info("Mixing audio tracks...")
        logger.info(f"Final pre-mix - TTS: {len(tts_audio)}ms, Music: {len(bg_audio)}ms")
        
        # Center the TTS if it's shorter than 10 seconds
        if len(tts_audio) < target_duration:
            tts_start_position = (target_duration - len(tts_audio)) // 2
            logger.info(f"Centering TTS at position {tts_start_position}ms")
            mixed = bg_audio.overlay(tts_audio, position=tts_start_position)
        else:
            mixed = bg_audio.overlay(tts_audio, position=0)
        
        logger.info(f"Mixed audio duration: {len(mixed)}ms")
        
        # Normalize audio to prevent clipping
        logger.info("Normalizing audio...")
        mixed = normalize(mixed)
        
        # Final check: ensure exactly 10 seconds
        if len(mixed) > target_duration:
            logger.info(f"Trimming to 10 seconds (was {len(mixed)}ms)...")
            mixed = mixed[:target_duration]
        elif len(mixed) < target_duration:
            logger.warning(f"Audio shorter than target, padding to 10 seconds (was {len(mixed)}ms)...")
            silence = AudioSegment.silent(duration=target_duration - len(mixed))
            mixed = mixed + silence
        
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
