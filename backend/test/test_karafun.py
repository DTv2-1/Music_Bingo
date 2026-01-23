#!/usr/bin/env python
"""Test script for Karafun Business API integration"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')
django.setup()

from api.karafun_service import KarafunAPI

def test_karafun_api():
    # Set the token
    token = "d7006237dd2b79071487c3a134b3118c2e9921ee2ec8243d35cf852dc718"
    api = KarafunAPI(api_token=token)
    
    print("=" * 60)
    print("🎤 TESTING KARAFUN BUSINESS API")
    print("=" * 60)
    
    # Test 1: List devices
    print("\n📱 Test 1: Listing devices...")
    try:
        devices = api.list_devices()
        if devices.get('success'):
            print(f"✅ Success! Found {len(devices.get('data', []))} devices:")
            for device in devices.get('data', []):
                print(f"   - {device.get('name', 'Unknown')} (ID: {device.get('id', 'N/A')})")
        else:
            print(f"❌ Error: {devices.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Test 2: Get sessions
    print("\n🎵 Test 2: Getting sessions...")
    try:
        sessions = api.get_sessions()
        if sessions.get('success'):
            session_list = sessions.get('data', [])
            print(f"✅ Success! Found {len(session_list)} sessions:")
            for session in session_list:
                print(f"   - Session ID: {session.get('id', 'N/A')}")
                print(f"     Status: {session.get('status', 'Unknown')}")
        else:
            print(f"❌ Error: {sessions.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✨ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_karafun_api()
