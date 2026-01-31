#!/usr/bin/env python3
"""
Test to simulate the FULL frontend flow for TTS
This replicates what happens in the browser to find the bug
"""

import os
import sys
import time
import threading
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_bingo.settings')

import django
django.setup()

from api.pub_quiz_models import PubQuizSession, QuizTeam, QuizQuestion

BASE_URL = "https://music-bingo-106397905288.europe-west2.run.app"
# BASE_URL = "http://localhost:8000"  # Uncomment for local testing

class QuizFlowSimulator:
    """Simulates the complete quiz flow like the frontend does"""
    
    def __init__(self, session_code):
        self.session_code = session_code
        self.base_url = BASE_URL
        self.sse_active = False
        self.sse_thread = None
        
    def log(self, emoji, message):
        """Pretty log output"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {emoji} {message}")
    
    def simulate_host_sse(self):
        """Simulate HOST SSE connection that polls every second"""
        self.log("🔌", "HOST: Opening SSE connection to /host-stream")
        
        url = f"{self.base_url}/api/pub-quiz/{self.session_code}/host-stream"
        
        try:
            response = requests.get(url, stream=True, timeout=None)
            self.log("✅", f"HOST SSE: Connected (status {response.status_code})")
            
            for line in response.iter_lines():
                if not self.sse_active:
                    self.log("🔌", "HOST SSE: Closing connection (sse_active=False)")
                    break
                    
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data:'):
                        import json
                        data = json.loads(line_str[5:].strip())
                        
                        if data.get('type') == 'generation_progress':
                            progress = data.get('progress', 0)
                            status = data.get('status', '')
                            self.log("📊", f"HOST SSE: Progress {progress}% - {status}")
                            
                            # This is what frontend SHOULD do but might not be doing
                            if progress >= 100:
                                self.log("✅", "HOST SSE: Received 100%, should CLOSE now")
                                self.sse_active = False
                                break
                        
        except Exception as e:
            self.log("❌", f"HOST SSE Error: {type(e).__name__}: {e}")
        finally:
            self.log("🔌", "HOST SSE: Connection closed")
    
    def start_host_sse(self):
        """Start HOST SSE in background thread"""
        self.sse_active = True
        self.sse_thread = threading.Thread(target=self.simulate_host_sse, daemon=True)
        self.sse_thread.start()
        time.sleep(1)  # Let it connect
    
    def stop_host_sse(self):
        """Stop HOST SSE"""
        self.sse_active = False
        if self.sse_thread:
            self.sse_thread.join(timeout=2)
    
    def register_team(self):
        """Simulate team registration"""
        self.log("👥", "PLAYER: Registering team 'Test Team'")
        
        url = f"{self.base_url}/api/pub-quiz/{self.session_code}/register-team"
        response = requests.post(url, json={
            'team_name': 'Test Team',
            'table_number': 1
        }, timeout=10)
        
        if response.status_code == 200:
            self.log("✅", "PLAYER: Team registered successfully")
            return True
        else:
            self.log("❌", f"PLAYER: Registration failed: {response.status_code}")
            return False
    
    def start_quiz(self):
        """Simulate host starting the quiz"""
        self.log("🎬", "HOST: Starting quiz...")
        
        url = f"{self.base_url}/api/pub-quiz/{self.session_code}/start"
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            self.log("✅", "HOST: Quiz started")
            return True
        else:
            self.log("❌", f"HOST: Start failed: {response.status_code}")
            return False
    
    def call_tts(self, text, description):
        """Simulate TTS call with timeout monitoring"""
        self.log("🎤", f"HOST: Calling TTS for '{description}'")
        self.log("📝", f"      Text: {text[:50]}...")
        
        url = f"{self.base_url}/api/pub-quiz/tts"
        
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                json={'text': text, 'voice_id': 'daniel'},
                timeout=15,  # Frontend uses 50 seconds
                stream=True
            )
            
            elapsed = time.time() - start_time
            
            self.log("📡", f"TTS: Response status {response.status_code} in {elapsed:.2f}s")
            
            if response.status_code == 200:
                # Stream response like frontend does
                chunks = []
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        chunks.append(chunk)
                        chunk_count += 1
                
                total_bytes = sum(len(c) for c in chunks)
                self.log("✅", f"TTS: Received {chunk_count} chunks, {total_bytes} bytes in {elapsed:.2f}s")
                return True
            else:
                self.log("❌", f"TTS: Failed with status {response.status_code}")
                return False
                
        except requests.Timeout:
            elapsed = time.time() - start_time
            self.log("❌", f"TTS: TIMEOUT after {elapsed:.2f}s")
            self.log("⚠️", "     This indicates workers are saturated!")
            return False
        except Exception as e:
            elapsed = time.time() - start_time
            self.log("❌", f"TTS: Exception after {elapsed:.2f}s: {type(e).__name__}: {e}")
            return False
    
    def check_backend_workers(self):
        """Check how many SSE connections are active"""
        self.log("🔍", "Checking backend worker status...")
        
        # This simulates what we see in logs
        self.log("📊", "Backend has 2 Gunicorn workers")
        self.log("📊", "Each SSE connection occupies 1 worker while polling")


def test_full_flow():
    """
    Test the complete flow:
    1. HOST opens SSE connection
    2. PLAYER registers team
    3. HOST starts quiz
    4. HOST calls TTS for welcome message
    5. HOST calls TTS for round announcement
    6. Check if workers are available
    """
    
    print("\n" + "="*70)
    print("🧪 FULL QUIZ FLOW TEST - Simulating Browser Behavior")
    print("="*70)
    
    # Use existing session
    session_code = "WPIXXNB1"  # From your logs
    
    simulator = QuizFlowSimulator(session_code)
    
    # Step 0: Check workers
    print("\n" + "-"*70)
    print("STEP 0: Initial Worker Check")
    print("-"*70)
    simulator.check_backend_workers()
    
    # Step 1: Start HOST SSE (this is the problem!)
    print("\n" + "-"*70)
    print("STEP 1: HOST Opens SSE Connection")
    print("-"*70)
    simulator.start_host_sse()
    
    # Wait for generation to complete (simulate waiting)
    simulator.log("⏳", "Waiting 5 seconds for SSE to poll...")
    time.sleep(5)
    
    # Step 2: Check if SSE closed
    print("\n" + "-"*70)
    print("STEP 2: Check if SSE Closed After 100%")
    print("-"*70)
    
    if simulator.sse_active:
        simulator.log("❌", "BUG FOUND: SSE still active after 100%!")
        simulator.log("⚠️", "This means workers are still occupied polling every 1 second")
    else:
        simulator.log("✅", "SSE properly closed after 100%")
    
    # Step 3: Register team
    print("\n" + "-"*70)
    print("STEP 3: Player Registers Team")
    print("-"*70)
    simulator.register_team()
    
    # Step 4: Start quiz
    print("\n" + "-"*70)
    print("STEP 4: Host Starts Quiz")
    print("-"*70)
    simulator.start_quiz()
    
    # Step 5: Try TTS with SSE active
    print("\n" + "-"*70)
    print("STEP 5: TTS Call #1 - Welcome Message")
    print("-"*70)
    
    welcome_text = "Welcome to JuanPub's Pub Quiz! We have 1 teams competing today. Get ready for an exciting game!"
    tts_success_1 = simulator.call_tts(welcome_text, "Welcome message")
    
    # Step 6: Try TTS again
    print("\n" + "-"*70)
    print("STEP 6: TTS Call #2 - Round Announcement")
    print("-"*70)
    
    round_text = "Round 1: General Knowledge"
    tts_success_2 = simulator.call_tts(round_text, "Round 1")
    
    # Step 7: Stop SSE and try again
    print("\n" + "-"*70)
    print("STEP 7: Manually Close SSE and Retry TTS")
    print("-"*70)
    
    simulator.log("🔌", "Manually closing SSE to free workers...")
    simulator.stop_host_sse()
    time.sleep(2)
    
    simulator.log("🎤", "Retrying TTS after closing SSE...")
    tts_success_3 = simulator.call_tts(round_text, "Round 1 (retry)")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    results = {
        'SSE Closed After 100%': not simulator.sse_active,
        'TTS #1 (with SSE active)': tts_success_1,
        'TTS #2 (with SSE active)': tts_success_2,
        'TTS #3 (SSE closed)': tts_success_3
    }
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    # Analysis
    print("\n" + "="*70)
    print("🔬 ANALYSIS")
    print("="*70)
    
    if not results['SSE Closed After 100%']:
        print("❌ BUG CONFIRMED: SSE connection stays open after 100%")
        print("   - This occupies 1 of 2 workers continuously")
        print("   - Every 1 second, it polls the database")
        print("   - Other requests (like TTS) must wait in queue")
        print("   - Result: TTS timeouts")
        print("\n💡 ROOT CAUSE: Frontend not closing SSE when progress >= 100%")
        print("   OR: Backend keeps sending events after 100%")
    
    if not tts_success_1 or not tts_success_2:
        print("\n❌ TTS FAILS when SSE is active")
        print("   - Confirms worker saturation theory")
    
    if tts_success_3:
        print("\n✅ TTS WORKS when SSE is closed")
        print("   - Confirms that TTS endpoint itself is functional")
        print("   - Problem is resource contention, not TTS code")
    
    print("\n" + "="*70)
    
    return all(results.values())


if __name__ == "__main__":
    success = test_full_flow()
    sys.exit(0 if success else 1)
