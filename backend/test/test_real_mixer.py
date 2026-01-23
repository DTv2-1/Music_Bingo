"""
Test script for audio mixer with REAL TTS and Music
Generates actual ElevenLabs TTS and Suno music, then mixes them
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from api.audio_mixer import mix_tts_with_music

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')

def generate_tts(text="Happy Hour! Two for one cocktails between 5pm and 7pm this Wednesday!"):
    """Generate real TTS from ElevenLabs"""
    print(f"Generating TTS: '{text}'")
    
    if not ELEVENLABS_API_KEY:
        print("❌ ELEVENLABS_API_KEY not found in environment")
        return None
    
    url = 'https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM'
    
    payload = {
        'text': text,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {
            'stability': 0.65,
            'similarity_boost': 0.9,
            'style': 0.4,
            'use_speaker_boost': True
        }
    }
    
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ TTS generation failed: {response.status_code}")
        print(response.text)
        return None
    
    tts_bytes = response.content
    print(f"✅ TTS generated: {len(tts_bytes)} bytes")
    
    # Save for inspection
    with open('test_tts_only.mp3', 'wb') as f:
        f.write(tts_bytes)
    print("📁 TTS saved to: test_tts_only.mp3")
    
    return tts_bytes

def generate_music(prompt="upbeat energetic pub background music with guitar", duration=10):
    """Generate real music from ElevenLabs Sound Generation"""
    print(f"\nGenerating music: '{prompt}' ({duration}s)")
    
    if not ELEVENLABS_API_KEY:
        print("❌ ELEVENLABS_API_KEY not found in environment")
        return None
    
    url = 'https://api.elevenlabs.io/v1/sound-generation'
    
    payload = {
        'text': prompt,
        'duration_seconds': duration
    }
    
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    
    if response.status_code != 200:
        print(f"❌ Music generation failed: {response.status_code}")
        print(response.text)
        return None
    
    music_bytes = response.content
    print(f"✅ Music generated: {len(music_bytes)} bytes")
    
    # Save for inspection
    with open('test_music_only.mp3', 'wb') as f:
        f.write(music_bytes)
    print("📁 Music saved to: test_music_only.mp3")
    
    return music_bytes

def test_real_mixer():
    """Test mixer with real TTS and music"""
    print("\n" + "="*60)
    print("🧪 TESTING AUDIO MIXER WITH REAL TTS + MUSIC")
    print("="*60 + "\n")
    
    # Generate TTS
    tts_bytes = generate_tts()
    if not tts_bytes:
        print("\n❌ Cannot proceed without TTS")
        return
    
    # Calculate TTS duration to generate matching music
    from pydub import AudioSegment
    import io
    tts_audio = AudioSegment.from_mp3(io.BytesIO(tts_bytes))
    tts_duration = len(tts_audio) / 1000  # ms to seconds
    music_duration = int(tts_duration) + 2  # Add 2 seconds for intro/outro
    print(f"\n⏱️  TTS duration: {tts_duration:.2f}s")
    print(f"🎵 Music target: {music_duration}s\n")
    
    # Generate Music with calculated duration
    music_bytes = generate_music(duration=music_duration)
    if not music_bytes:
        print("\n❌ Cannot proceed without music")
        return
    
    # Mix them
    print("\n" + "="*60)
    print("🎚️ MIXING AUDIO...")
    print("="*60 + "\n")
    
    result = mix_tts_with_music(tts_bytes, music_bytes)
    
    print(f"\n✅ Mixed audio created: {len(result)} bytes")
    
    # Save result
    output_path = "test_real_mixed.mp3"
    with open(output_path, 'wb') as f:
        f.write(result)
    
    print(f"\n📁 Output saved to: {output_path}")
    print(f"📍 Full path: {os.path.abspath(output_path)}")
    
    print("\n" + "="*60)
    print("🔊 LISTEN TO THESE FILES:")
    print("="*60)
    print(f"\n1️⃣  TTS only:   afplay test_tts_only.mp3")
    print(f"2️⃣  Music only: afplay test_music_only.mp3")
    print(f"3️⃣  Mixed:      afplay {output_path}")
    print("\nCompare them to verify music is audible in the mix!\n")

if __name__ == "__main__":
    test_real_mixer()
