#!/usr/bin/env python3
"""
Test script to verify TTS endpoint is working
Tests both locally and in production
"""

import os
import sys
import django
import requests
from pathlib import Path

# Setup Django environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

def test_tts_local():
    """Test TTS endpoint locally using Django test client"""
    from django.test import Client
    from django.contrib.auth import get_user_model
    
    print("\n" + "="*60)
    print("TEST 1: LOCAL TTS ENDPOINT (Django Test Client)")
    print("="*60)
    
    client = Client()
    
    # Test data
    test_text = "Round 1: General Knowledge"
    
    print(f"\n📤 Sending POST to /api/pub-quiz/tts")
    print(f"   Text: '{test_text}'")
    print(f"   Voice: daniel")
    
    response = client.post(
        '/api/pub-quiz/tts',
        data={
            'text': test_text,
            'voice_id': 'daniel'
        },
        content_type='application/json'
    )
    
    print(f"\n📥 Response Status: {response.status_code}")
    print(f"   Content-Type: {response.get('Content-Type', 'N/A')}")
    
    if response.status_code == 200:
        content_length = len(response.content) if hasattr(response, 'content') else 0
        print(f"   Content Length: {content_length} bytes")
        
        if content_length > 0:
            print("\n✅ SUCCESS: TTS endpoint returned audio data")
            return True
        else:
            print("\n❌ FAIL: TTS endpoint returned empty response")
            return False
    else:
        print(f"\n❌ FAIL: Status {response.status_code}")
        try:
            print(f"   Error: {response.json()}")
        except:
            print(f"   Response: {response.content[:200]}")
        return False


def test_tts_production():
    """Test TTS endpoint in production Cloud Run"""
    print("\n" + "="*60)
    print("TEST 2: PRODUCTION TTS ENDPOINT (Cloud Run)")
    print("="*60)
    
    base_url = "https://music-bingo-106397905288.europe-west2.run.app"
    endpoint = f"{base_url}/api/pub-quiz/tts"
    
    test_text = "Round 1: General Knowledge"
    
    print(f"\n📤 Sending POST to {endpoint}")
    print(f"   Text: '{test_text}'")
    print(f"   Voice: daniel")
    print(f"   Timeout: 10 seconds")
    
    try:
        import time
        start_time = time.time()
        
        response = requests.post(
            endpoint,
            json={
                'text': test_text,
                'voice_id': 'daniel'
            },
            timeout=10,
            stream=True
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            # Read streamed content
            chunks = []
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    chunks.append(chunk)
            
            total_bytes = sum(len(c) for c in chunks)
            print(f"   Chunks received: {len(chunks)}")
            print(f"   Total bytes: {total_bytes}")
            
            if total_bytes > 0:
                print("\n✅ SUCCESS: Production TTS endpoint working")
                return True
            else:
                print("\n❌ FAIL: Production returned empty response")
                return False
        else:
            print(f"\n❌ FAIL: Status {response.status_code}")
            try:
                print(f"   Error: {response.json()}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print(f"\n❌ FAIL: Request timed out after 10 seconds")
        print("   This suggests workers are saturated or endpoint is unresponsive")
        return False
    except Exception as e:
        print(f"\n❌ FAIL: Exception: {type(e).__name__}: {e}")
        return False


def test_elevenlabs_api_key():
    """Check if ElevenLabs API key is configured"""
    print("\n" + "="*60)
    print("TEST 0: ELEVENLABS API KEY CHECK")
    print("="*60)
    
    api_key = os.getenv('ELEVENLABS_API_KEY', '')
    
    if api_key:
        print(f"\n✅ API Key configured: {api_key[:10]}...{api_key[-4:]}")
        return True
    else:
        print("\n❌ ELEVENLABS_API_KEY not configured in environment")
        print("   Set it in .env file or environment variables")
        return False


def main():
    print("\n🎤 TTS ENDPOINT TEST SUITE")
    print("Testing Text-to-Speech API endpoint\n")
    
    results = {}
    
    # Test 0: API Key
    results['api_key'] = test_elevenlabs_api_key()
    
    if not results['api_key']:
        print("\n⚠️  Skipping tests - API key not configured")
        return
    
    # Test 1: Local endpoint
    results['local'] = test_tts_local()
    
    # Test 2: Production endpoint
    results['production'] = test_tts_production()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
