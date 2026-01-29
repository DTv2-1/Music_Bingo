#!/usr/bin/env python3
"""
Check how many SSE connections are polling the backend
This will help identify if there are zombie connections
"""

import requests
import time
import sys

BASE_URL = "https://music-bingo-106397905288.europe-west2.run.app"
SESSION_CODE = "WPIXXNB1"

def monitor_backend_logs():
    """
    Since we can't directly check SSE connections, 
    we'll monitor backend behavior to infer connection count
    """
    
    print("\n" + "="*70)
    print("🔍 SSE CONNECTION MONITOR")
    print("="*70)
    print(f"\nMonitoring session: {SESSION_CODE}")
    print("This test will check if backend is responding to requests")
    print("\nPress Ctrl+C to stop\n")
    
    # Test 1: Simple health check
    print("-"*70)
    print("TEST 1: Health Check (should be instant)")
    print("-"*70)
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=3)
        elapsed = time.time() - start
        print(f"✅ Health check: {response.status_code} in {elapsed:.2f}s")
        
        if elapsed > 1:
            print(f"⚠️  Warning: Slow response ({elapsed:.2f}s), workers might be busy")
    except requests.Timeout:
        elapsed = time.time() - start
        print(f"❌ Health check TIMEOUT after {elapsed:.2f}s")
        print("   This means ALL workers are saturated!")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Session details (requires DB query)
    print("\n" + "-"*70)
    print("TEST 2: Session Details (requires DB + worker)")
    print("-"*70)
    
    start = time.time()
    try:
        response = requests.get(
            f"{BASE_URL}/api/pub-quiz/{SESSION_CODE}/details", 
            timeout=5
        )
        elapsed = time.time() - start
        print(f"✅ Session details: {response.status_code} in {elapsed:.2f}s")
        
        if elapsed > 2:
            print(f"⚠️  Warning: Slow DB query ({elapsed:.2f}s)")
            print("   Possible causes:")
            print("   - Workers occupied by SSE connections")
            print("   - Database under load")
    except requests.Timeout:
        elapsed = time.time() - start
        print(f"❌ Session details TIMEOUT after {elapsed:.2f}s")
        print("   Workers are definitely saturated!")
        return False
    except Exception as e:
        print(f"❌ Session details failed: {e}")
        return False
    
    # Test 3: Quick TTS request
    print("\n" + "-"*70)
    print("TEST 3: TTS Request (requires worker + ElevenLabs API)")
    print("-"*70)
    
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/tts",
            json={'text': 'Test', 'voice_id': 'daniel'},
            timeout=10,
            stream=True
        )
        
        # Read stream
        chunks = list(response.iter_content(chunk_size=4096))
        total_bytes = sum(len(c) for c in chunks if c)
        
        elapsed = time.time() - start
        print(f"✅ TTS: {response.status_code}, {total_bytes} bytes in {elapsed:.2f}s")
        
        if elapsed > 3:
            print(f"⚠️  Warning: Slow TTS ({elapsed:.2f}s)")
            print("   Workers might be busy with other tasks")
        
        return True
        
    except requests.Timeout:
        elapsed = time.time() - start
        print(f"❌ TTS TIMEOUT after {elapsed:.2f}s")
        print("   🔴 CRITICAL: Workers saturated, TTS cannot execute")
        print("\n   📊 Diagnosis:")
        print("   - With 2 workers and requests timing out:")
        print("   - At least 2 SSE connections are active")
        print("   - Each SSE polls every 1 second")
        print("   - No workers available for new requests")
        return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ TTS failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        return False


def diagnose_saturation():
    """Provide diagnosis based on test results"""
    
    print("\n" + "="*70)
    print("🔬 DIAGNOSIS & RECOMMENDATIONS")
    print("="*70)
    
    print("""
PROBLEM: Workers Saturated by SSE Connections

EVIDENCE:
- TTS requests timeout after 10+ seconds
- Backend logs show continuous SSE polling at 100%
- Other requests (health, session details) also slow

ROOT CAUSE:
1. Multiple browser tabs/windows have SSE connections open
2. Each SSE connection polls backend every 1 second
3. With only 2 Gunicorn workers, they are fully occupied
4. New requests (TTS, registration) queue up and timeout

SOLUTIONS:

Option 1: Force Close SSE from Backend (AGGRESSIVE)
  - Modify backend to stop sending events after 100%
  - Add timeout to SSE connections (e.g., 2 minutes max)
  - Pros: Guaranteed to work
  - Cons: Might break legitimate long-running connections

Option 2: Increase Workers (TEMPORARY FIX)  
  - Increase Gunicorn workers from 2 to 4 or 6
  - Pros: More capacity for concurrent requests
  - Cons: Doesn't fix root cause, costs more $$$

Option 3: Fix Frontend Cache (PERMANENT FIX)
  - Ensure all users hard-refresh to get new frontend code
  - New code properly closes SSE at 100%
  - Pros: Fixes root cause permanently
  - Cons: Requires user action (hard refresh)

RECOMMENDED: Option 1 + Option 3
1. Implement backend timeout for SSE (safety net)
2. Tell users to hard refresh (Cmd+Shift+R)
3. Test with fresh session
    """)


if __name__ == "__main__":
    success = monitor_backend_logs()
    
    if not success:
        diagnose_saturation()
        print("\n❌ Backend is saturated")
        sys.exit(1)
    else:
        print("\n✅ Backend is healthy")
        sys.exit(0)
