from django.test import LiveServerTestCase
from api.pub_quiz_models import PubQuizSession, QuizTeam, QuizQuestion, QuizGenre
from django.utils import timezone
import requests
import threading
import json
import time

class PubQuizSSETest(LiveServerTestCase):
    def setUp(self):
        # Create session (using numeric ID for simplicity or fake code setup)
        # Note: PubQuizSession.objects.create doesn't auto-generate code unless save() logic does.
        # Assuming it does or we provide one.
        self.session = PubQuizSession.objects.create(
            session_code="TESTSSE",
            venue_name="Test Pub",
            status="in_progress",
            current_round=1,
            current_question=1,
            questions_per_round=5,
            total_rounds=1,
            question_started_at=timezone.now()
        )
        self.team = QuizTeam.objects.create(session=self.session, team_name="TestTeam")
        self.genre = QuizGenre.objects.create(name="General")
        self.question = QuizQuestion.objects.create(
            session=self.session,
            question_text="What is 2+2?",
            correct_answer="4",
            round_number=1,
            question_number=1,
            genre=self.genre
        )

    def test_sse_receives_answer(self):
        # Start SSE listener in a thread
        received_events = []
        stop_event = threading.Event()
        
        def sse_worker():
            url = f"{self.live_server_url}/api/pub-quiz/{self.session.session_code}/host-stream"
            print(f"Connecting to {url}")
            try:
                # Set stream=True to keep connection open
                with requests.get(url, stream=True, timeout=10) as response:
                    for line in response.iter_lines():
                        if stop_event.is_set():
                            break
                        if line:
                            decoded = line.decode('utf-8')
                            if decoded.startswith("data:"):
                                try:
                                    data = json.loads(decoded[5:])
                                    received_events.append(data)
                                    # If we find our answer, we can stop
                                    if data.get('type') == 'host_update':
                                        answers = data.get('recent_answers', [])
                                        if any(a['answer_text'] == "4" for a in answers):
                                            stop_event.set()
                                except json.JSONDecodeError:
                                    print(f"JSON Error: {decoded}")
                                    pass
            except Exception as e:
                print(f"SSE Error: {e}")

        t = threading.Thread(target=sse_worker)
        t.daemon = True
        t.start()

        # Wait for connection to establish and initial events to pass
        time.sleep(2)

        # Submit answer
        submit_url = f"{self.live_server_url}/api/pub-quiz/question/{self.question.id}/submit"
        print(f"Submitting answer to {submit_url}")
        resp = requests.post(submit_url, json={
            "team_id": self.team.id,
            "answer": "4",
            "is_multiple_choice": False
        })
        print(f"Submit response: {resp.status_code} {resp.text}")

        # Wait for SSE to pick it up (the loop runs every 1s + logic)
        for i in range(10):
            if stop_event.is_set():
                break
            time.sleep(1)
            print(f"Waiting for SSE... {i+1}/10")
        
        stop_event.set()
        
        # Verify findings
        found_answer = False
        print(f"Total events received: {len(received_events)}")
        for event in received_events:
            print(f"Event: {event}")
            if event.get('type') == 'host_update':
                answers = event.get('recent_answers', [])
                if answers:
                     print(f"Found answers in event: {answers}")
                for ans in answers:
                    if ans['team_name'] == "TestTeam" and ans['answer_text'] == "4":
                        found_answer = True
                        print(f"✅ Found matching answer in SSE!")

            
        self.assertTrue(found_answer, "Did not receive recent_answer in SSE stream")
