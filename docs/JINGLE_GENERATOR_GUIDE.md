# 🎤 Jingle Generator - Installation & Testing Guide

## 📋 Overview

The Jingle Generator allows pub owners to create professional 10-second advertising jingles by combining:
- AI-generated voice (Text-to-Speech)
- AI-generated background music
- Automatic audio mixing and mastering

---

## 🔧 Installation

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install the new dependencies:
- `pydub` - Python audio manipulation library
- `ffmpeg-python` - Python bindings for FFmpeg

### 2. Install FFmpeg

FFmpeg is required for audio processing.

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH.

**Verify installation:**
```bash
ffmpeg -version
```

### 3. Configure Environment Variables

Make sure your `.env` file has the ElevenLabs API key:

```env
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

---

## 🚀 Running the Application

### Development Mode

1. **Start Backend:**
```bash
cd backend
python manage.py runserver 0.0.0.0:8080
```

2. **Access Frontend:**
Open `http://localhost:8080/game.html` in your browser

3. **Click "Create Jingle" button** to access the jingle generator

---

## 🎵 Using the Jingle Generator

### Step 1: Enter Text
- Type your promotional message (max 150 characters)
- Or choose from predefined templates:
  - Happy Hour
  - Live Music
  - Food Special
  - Quiz Night

**Example:**
```
Every Wednesday Evening, Happy Hour two for one cocktails between 5pm and 7pm
```

### Step 2: Choose Voice
Select from available voices:
- **British Male** - Professional & Clear
- **British Female** - Friendly & Warm
- **Energetic** - Upbeat & Fun

### Step 3: Select Music Style
Choose background music genre:
- 🎸 **Pub Rock** - Upbeat guitar-driven
- 🎹 **Jazz Piano** - Smooth and sophisticated
- 🎧 **Electronic** - Modern and energetic
- 🎵 **Acoustic** - Indie folk style
- 🍀 **Irish Folk** - Traditional pub atmosphere
- 💃 **Funky** - Disco groove

### Step 4: Generate & Download
1. Review your configuration
2. Click **"Generate Jingle"**
3. Wait 20-40 seconds for processing
4. Preview the jingle in the audio player
5. Click **"Download Jingle"** to save as MP3

---

## 📁 File Structure

### Backend Files
```
backend/
├── api/
│   ├── views.py              # Added jingle endpoints
│   ├── urls.py               # Added jingle routes
│   └── audio_mixer.py        # NEW: Audio mixing logic
├── requirements.txt          # Updated with pydub, ffmpeg-python
└── data/
    └── jingles/              # NEW: Generated jingles stored here
```

### Frontend Files
```
frontend/
├── jingle.html               # NEW: Jingle generator UI
├── jingle.js                 # NEW: Jingle generation logic
└── game.html                 # Updated: Added "Create Jingle" button
```

---

## 🔗 API Endpoints

### POST `/api/generate-jingle`
Start jingle generation (asynchronous)

**Request Body:**
```json
{
  "text": "Your promotional message here",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "music_prompt": "upbeat energetic pub background music",
  "duration": 10
}
```

**Response:**
```json
{
  "task_id": "uuid-here",
  "status": "pending",
  "message": "Jingle generation started"
}
```

### GET `/api/jingle-tasks/{task_id}`
Check generation status

**Response:**
```json
{
  "status": "processing",
  "progress": 75,
  "current_step": "mixing",
  "result": null
}
```

**Completed Response:**
```json
{
  "status": "completed",
  "progress": 100,
  "current_step": "completed",
  "result": {
    "audio_url": "/api/jingles/jingle_123456_abc.mp3",
    "filename": "jingle_123456_abc.mp3",
    "duration_seconds": 10,
    "size_bytes": 123456
  }
}
```

### GET `/api/jingles/{filename}`
Download generated jingle

**Response:** MP3 audio file

---

## 🧪 Testing

### Manual Testing Steps

1. **Test Text Input:**
   - Enter short text (< 10 chars) → Should show error
   - Enter long text (> 150 chars) → Should be prevented
   - Use template buttons → Should populate textarea

2. **Test Voice Selection:**
   - Click different voice cards → Should highlight selected
   - Ensure selection persists through wizard steps

3. **Test Music Selection:**
   - Click different music styles → Should highlight selected
   - Verify all 6 styles are clickable

4. **Test Generation:**
   - Complete all steps and click "Generate Jingle"
   - Progress bar should update smoothly
   - Status messages should change:
     - "Generating voice with AI..."
     - "Creating background music..."
     - "Mixing audio tracks..."
     - "Finalizing your jingle..."
   - After ~30 seconds, audio player should appear
   - Audio should auto-play (if browser allows)

5. **Test Download:**
   - Click "Download Jingle" button
   - MP3 file should download
   - File should be ~10 seconds duration
   - Audio should be clear and mixed properly

6. **Test Error Handling:**
   - Remove API key from `.env` → Should show error
   - Disconnect internet → Should show timeout error
   - Click "Create Another" → Should reset wizard

### API Testing with curl

**Start generation:**
```bash
curl -X POST http://localhost:8080/api/generate-jingle \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Happy Hour every Wednesday 5-7pm",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "music_prompt": "upbeat pub guitar music",
    "duration": 10
  }'
```

**Check status:**
```bash
curl http://localhost:8080/api/jingle-tasks/{task_id}
```

**Download jingle:**
```bash
curl -O http://localhost:8080/api/jingles/{filename}
```

---

## 🐛 Troubleshooting

### Issue: "FFmpeg not found"
**Solution:** Install FFmpeg (see Installation section)

### Issue: "ElevenLabs API error"
**Solution:** 
- Check API key in `.env`
- Verify API credits remain
- Check internet connection

### Issue: Audio quality is poor
**Solution:**
- Try different music prompts
- Adjust volume levels in `audio_mixer.py`
- Ensure input text is clear and well-formatted

### Issue: Generation takes too long (>60s)
**Solution:**
- Check ElevenLabs API status
- Verify network speed
- Consider increasing timeout in `views.py`

### Issue: "Music API error, using fallback"
**Solution:**
- ElevenLabs Music API may not be available in your plan
- System will use a simple tone as placeholder
- Upgrade ElevenLabs plan for full music generation

---

## 📊 Performance Metrics

### Expected Timings
- TTS Generation: 3-5 seconds
- Music Generation: 10-20 seconds
- Audio Mixing: 2-3 seconds
- **Total:** 15-30 seconds

### File Sizes
- TTS Audio: ~50-100 KB
- Music Audio: ~150-200 KB
- Final Mixed Jingle: ~120-180 KB (128kbps MP3)

---

## 🔐 Security Considerations

1. **API Key Protection:** Never commit `.env` to git
2. **File Storage:** Jingles stored in `data/jingles/` (gitignored)
3. **Rate Limiting:** Consider adding rate limits to prevent abuse
4. **File Cleanup:** Old jingles should be cleaned up periodically

---

## 💰 Cost Considerations

### ElevenLabs Pricing
- **TTS:** ~$0.18 per 1000 characters
- **Music Generation:** ~$0.10 per 10 seconds
- **Estimated cost per jingle:** $0.10 - $0.30

### Optimization Tips
1. Cache common phrases
2. Implement usage limits per venue
3. Monitor API usage in ElevenLabs dashboard

---

## 🚀 Next Steps

### Potential Enhancements
1. **Voice Preview:** Add preview button for voices
2. **Music Preview:** Add 5-second preview for music styles
3. **Custom Music:** Allow users to upload their own background music
4. **Jingle Library:** Save and manage previously created jingles
5. **Scheduling:** Schedule jingles to play at specific times
6. **Analytics:** Track which jingles are most effective

---

## 📞 Support

For issues or questions:
1. Check logs in terminal/console
2. Review Django logs for backend errors
3. Check browser console for frontend errors
4. Verify all dependencies are installed
5. Ensure FFmpeg is properly configured

---

**Version:** 1.0  
**Last Updated:** January 13, 2026  
**Status:** ✅ Ready for Testing
