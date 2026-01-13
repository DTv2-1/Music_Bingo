To allow your Pub Radio subscribers to self-generate 10-second jingles (TTS
announcements mixed with short music or sound effects), the best approach is to build a
simple web-based interface that leverages readily available APIs for generation and mixing.
This keeps it user-friendly: subscribers input text (e.g., "Happy Hour: Buy one get one free
on all drafts from 5-7 PM!"), select options (voice style, music genre/effect type), and get a
downloadable MPЗ.
Focus on APIs that are developer-friendly, cost-effective (pay-per-use), and high-quality.
Avoid services without APIs (e.g., Al JingleMaker is Ul-only). The top all-in-one option is
AudioStack API, which handles TTS, music/sound generation, and automatic mixing in one
call-ideal for jingles. If you prefer modular control, use ElevenLabs (for TTS and
music/sounds) + a library for mixing.
Recommended Stack: AudioStack API (All-in-One)
AudioStack is enterprise-grade but accessible via API/SDK, specialized in ad/jingle
production. It combines TTS, generative music/sounds, and mixing/mastering
automatically, outputting broadcast-ready audio in seconds. No need for separate mixing
code.
• Why? Streamlines the process (text → mixed jingle). Supports 400+ voices, 50+
languages, 50+ sound designs/genres (e.g., upbeat pub vibe, jingle bells).
Customizable with SSML for emphasis/pauses. Commercially licensed outputs.
• Pricing: Credit-based (varies by endpoint; e.g., ~$0.01-0.05 per short clip). Starter
plans ~$50-100/mo for low volume; scales for enterprises. Sign up at audiostack.ai for
API key.
• Integration Steps:
1. Create an account and get API key.
2. Use their Python or JS SDK in your backend (e.g., Flask/Node.js app) to handle
requests securely (don't expose keys client-side).
3. Subscriber flow: Form submits text + options → API generates → Download link.
Example Python backend snippet (using their SDK; install via pip install audiostack):
Python
import audiostack
# Initialize with your key
audiostack.api_key = 'YOUR_AUDIOSTACK_API_KEY'
def generate_jingle(text, voice='en-US-Wavenet-D', music_genre='upbeat pub ji
# Create script with TTS
script = audiostack.Content.Script.create(script_text=text)
# TTS synthesis
speech = audiostack. Speech.Tts.create(script_item=script, voice=voice)
# Generative sound/music
sound_template = audiostack.Production.SoundTemplate.create(template_name
非 Mix: Auto-combines speech + music, masters to 10s
mix = audiostack.Production.Mix.create(
speech_items=[speech],
sound_template_item=sound_template,
mastering_preset='balanced', # Or 'dynamic' for ads
trim_silence=True,
target_duration=duration
ㅑ
# Get MP3 URL
delivery = audiostack.Delivery.Output.download (mix)
return delivery.url # Return downloadable link
Usage in web app: Call on form submit, e.g., jingle_url = generate_jingle(,
• Frontend: Simple HTML/JS form (e.g., via React/Vue) to collect input and fetch from
backend.
Enhancements: Add previews, voice previews, or webhook for async generation if
high volume.
• Limitations: More enterprise-oriented; test for pub-specific sounds. If credits are too
pricey for starters, fallback below.
Alternative Modular Stack: ElevenLabs APIs + Pydub for Mixing
If you want finer control or lower costs for high volume, generate components separately
with ElevenLabs (TTS + music/sounds) and mix via a free library. ElevenLabs is excellent for
natural voices and Al-generated audio; their Music API (new as of Dec 2025) handles short
instrumentals/vocals.
Why? One provider for generation (reduces latency). Pay-per-use (~$0.01-0.10 per
clip). Royalty-free outputs.
APIs Used:
TTS API: Text to voice audio.
• Sound Effects API: Text to short sounds (e.g., "cheerful pub crowd").
• Music API: Text to music (e.g., "10-second upbeat folk jingle instrumental").
Pricing: Starter free tier (limited credits); scales to $5-99/mo. API key from
elevenlabs.io.
Mixing: Use pydub (Python lib) server-side to overlay TTS on background, trim to 10s,
add fades.
• Integration Steps:
1. Get ElevenLabs API key.
2. Backend: Fetch audio blobs, mix with pydub ( pip install pydub ffmpeg).
3. Output MP3.
Example Python backend:
Python
import requests
from pydub import AudioSegment
import io
ELEVENLABS_KEY = 'YOUR_ELEVENLABS_API_KEY'
VOICE_ID = '21m00Tcm4T1vDq8ikWAM' # Default; list via API
def generate_tts(text):
url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
payload = {"text": text, "model_id": "eleven_monolingual_v1"{
headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/jso
response = requests.post(url, json=payload)
return io.BytesIO(response.content) # MP3 bytes
def generate_background (prompt, is_music=True):
if is_music:
else:
url = "https://api.elevenlabs.io/v1/music" # Music API endpoint
payload = {"prompt": prompt, "duration_seconds": 10} # Short clip
url = "https://api.elevenlabs.io/v1/sound-generation"
payload = {"text": prompt, "duration_seconds": 10{
headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/jso
response = requests.post(url, json=payload)
return io.BytesIO(response.content)
def mix_jingle(tts_bytes, bg_bytes):
tts_audio = AudioSegment.from_mp3(tts_bytes)
bg_audio = AudioSegment.from_mp3(bg_bytes).fade_in(1).fade_out(1)
非 Overlay: TTS over background, lower BG volume
mixed = bg_audio.overlay(tts_audio, gain_during_overlay=-6)
mixed = mixed[:10000] # Trim to 10s (ms)
output = io.BytesIO()
mixed.export(output, format="mp3")
return output.getvalue() # Bytes for download
# Soft
# -6dB on T7
# Usage: tts = generate_tts("Special offer: Free appetizers!")
# bg = generate_background("Upbeat pub guitar riff", is_music=True)
# jingle_mp3 = mix_jingle(tts, bg)
# Save or serve as file
Frontend: Similar to above; POST to backend, get MP3 URL.
Enhancements: Prompt templates (e.g., "Energetic Irish pub tune"). Handle errors
(e.g., if music min is 10s).
Limitations: Music API min 10s; sound effects for non-musical. Mixing adds ~1-2s
latency.
General Tips for Implementation
Self-Service Security: Backend handles API calls to protect keys. Use auth (e.g., JWT)
for subscribers.
Web App Framework: Flask/Django (Python) or Express (Node) for backend; host on
Vercel/AWS for free/low-cost.
User Experience: Preview clips, dropdowns for voices/genres (fetch from API). Limit
to 10s to avoid abuse.
Alternatives if Needed:
Stable Audio API (stability.ai): For backgrounds (~$0.01/clip); pair with ElevenLabs
TTS + pydub.
Soundverse API: Good for music-focused jingles ($99/mo starter); similar to
Eleven but with refinement chat.
Legal/Quality: Ensure outputs are royalty-free. Test for pub ambiance (e.g., prompts
like "cozy bar jazz with clinking glasses").
Scaling: Start local, add queueing (e.g., Celery) for many users.
This setup is quick to prototype (1-2 days) and extensible for Pub Radio integration. If you
need full code or hosting advice, provide more details!

I want to do the following additions to the demo:



1. Jingle creation



2. karaoke



3. Pub quiz



4. Singles blind date

PH
Philip Hill
10:19 AM
yes, so Jingle Creation is ability for the pub owner to quickly make a jingle to advertise promotions etc

so, they will enter the text such as 'Every Wednesday Evening, Happy hour two for one cocktails between 5pm and 7pm, check out our Happy Hour cocktails at the bar'

first we create the voice using TTS, when customer is happy with voice then we use AI to create music jingle