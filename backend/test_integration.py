#!/usr/bin/env python3
"""
Integration test to verify nothing is broken by SSE timeout fix
Tests complete quiz flow from start to finish
"""

import requests
import time
import sys

BASE_URL = "https://music-bingo-106397905288.europe-west2.run.app"

def test_quiz_flow_integration():
    """Test complete quiz flow to ensure nothing is broken"""
    
    print("\n" + "="*70)
    print("🧪 INTEGRATION TEST - Complete Quiz Flow")
    print("="*70)
    
    tests_passed = []
    tests_failed = []
    
    # Test 1: Create new session
    print("\n📝 TEST 1: Create new quiz session")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/create-session",
            json={
                'venue_name': 'Test Venue',
                'host_name': 'Test Host',
                'total_rounds': 2,
                'questions_per_round': 5
            },
            timeout=10
        )
        
        if response.status_code == 201:
            session_data = response.json()
            session_code = session_data.get('session_code')
            print(f"   ✅ Session created: {session_code}")
            tests_passed.append("Create session")
        else:
            print(f"   ❌ Failed to create session: {response.status_code}")
            tests_failed.append("Create session")
            return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Create session")
        return False
    
    # Test 2: Generate questions
    print("\n🤖 TEST 2: Generate questions (this will test SSE)")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/{session_code}/generate-questions",
            timeout=120  # Generation can take time
        )
        
        if response.status_code == 200:
            print(f"   ✅ Questions generated")
            tests_passed.append("Generate questions")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("Generate questions")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Generate questions")
    
    # Test 3: Register team
    print("\n👥 TEST 3: Register team")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/{session_code}/register-team",
            json={'team_name': 'Test Team', 'table_number': 1},
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"   ✅ Team registered")
            tests_passed.append("Register team")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("Register team")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Register team")
    
    # Test 4: Start quiz
    print("\n🎬 TEST 4: Start quiz")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/{session_code}/start",
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"   ✅ Quiz started")
            tests_passed.append("Start quiz")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("Start quiz")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Start quiz")
    
    # Test 5: TTS (the critical one)
    print("\n🎤 TEST 5: TTS generation")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/tts",
            json={'text': 'Round 1: General Knowledge', 'voice_id': 'daniel'},
            timeout=10,
            stream=True
        )
        
        if response.status_code == 200:
            chunks = list(response.iter_content(chunk_size=4096))
            total_bytes = sum(len(c) for c in chunks if c)
            print(f"   ✅ TTS working: {total_bytes} bytes")
            tests_passed.append("TTS generation")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("TTS generation")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("TTS generation")
    
    # Test 6: Get session details
    print("\n📊 TEST 6: Get session details")
    try:
        response = requests.get(
            f"{BASE_URL}/api/pub-quiz/{session_code}/details",
            timeout=10
        )
        
        if response.status_code == 200:
            details = response.json()
            print(f"   ✅ Details retrieved: {details.get('status')}")
            tests_passed.append("Get details")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("Get details")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Get details")
    
    # Test 7: Next question
    print("\n➡️ TEST 7: Next question")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pub-quiz/{session_code}/next-question",
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"   ✅ Moved to next question")
            tests_passed.append("Next question")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            tests_failed.append("Next question")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        tests_failed.append("Next question")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"\n✅ Passed: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)}")
    for test in tests_passed:
        print(f"   ✅ {test}")
    
    if tests_failed:
        print(f"\n❌ Failed: {len(tests_failed)}/{len(tests_passed) + len(tests_failed)}")
        for test in tests_failed:
            print(f"   ❌ {test}")
    
    print("\n" + "="*70)
    
    if tests_failed:
        print("❌ Some tests failed - SSE fix may have broken something")
        return False
    else:
        print("✅ All tests passed - SSE fix working correctly!")
        return True


if __name__ == "__main__":
    success = test_quiz_flow_integration()
    sys.exit(0 if success else 1)
