# 🎤 Jingle Generator

> Create professional 10-second advertising jingles with AI in minutes

## ✨ Quick Start

### 1. Install Dependencies
```bash
./install_jingle_generator.sh
```

Or manually:
```bash
pip install pydub ffmpeg-python
brew install ffmpeg  # macOS
```

### 2. Start the Server
```bash
cd backend
python manage.py runserver 0.0.0.0:8080
```

### 3. Create Your First Jingle
1. Open `http://localhost:8080/game.html`
2. Click **"🎤 Create Jingle"**
3. Enter your promotional text
4. Choose a voice and music style
5. Generate and download!

## 🎯 Features

- ✅ AI Text-to-Speech (ElevenLabs)
- ✅ AI Music Generation
- ✅ Automatic Audio Mixing
- ✅ 6 Music Styles (Pub Rock, Jazz, Electronic, Acoustic, Irish Folk, Funky)
- ✅ 3 Voice Options (British Male/Female, Energetic)
- ✅ Professional 10-second output
- ✅ Instant MP3 download

## 📖 Documentation

Full guide: [JINGLE_GENERATOR_GUIDE.md](docs/JINGLE_GENERATOR_GUIDE.md)

## 🎨 How It Works

```
User Input → TTS API → AI Music → Audio Mixer → 10s MP3 Jingle
   ↓            ↓          ↓           ↓
  Text     Voice Audio   Music    Mixed & Mastered
```

## 🔧 Technical Stack

**Backend:**
- Django REST Framework
- ElevenLabs API (TTS + Music)
- Pydub (Audio Mixing)
- FFmpeg (Audio Processing)

**Frontend:**
- Vanilla JavaScript
- HTML5 Audio API
- Responsive Design

## 📁 New Files

```
backend/
├── api/
│   ├── audio_mixer.py       # Audio mixing logic
│   ├── views.py             # Added jingle endpoints
│   └── urls.py              # Added routes
└── requirements.txt         # Added pydub, ffmpeg-python

frontend/
├── jingle.html              # Jingle generator UI
└── jingle.js                # Generation logic

data/
└── jingles/                 # Generated jingles stored here
```

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate-jingle` | Start jingle generation |
| GET | `/api/jingle-tasks/{id}` | Check generation status |
| GET | `/api/jingles/{filename}` | Download jingle |

## 💡 Example Usage

**Text Input:**
```
Every Wednesday Evening, Happy Hour two for one cocktails between 5pm and 7pm
```

**Output:**
- Professional voice announcement
- Upbeat background music
- 10-second MP3 file
- Ready for broadcast

## ⚡ Performance

- Generation Time: **15-30 seconds**
- File Size: **~150 KB** (128kbps MP3)
- Cost per Jingle: **~$0.10-0.30** (ElevenLabs API)

## 🎯 Use Cases

1. **Happy Hour Promotions**
2. **Event Announcements**
3. **Food & Drink Specials**
4. **Live Music Nights**
5. **Quiz Nights**
6. **Brand Identity Jingles**

## 🚀 Future Enhancements

- [ ] Voice preview before generation
- [ ] Music style preview
- [ ] Custom music upload
- [ ] Jingle library/management
- [ ] Scheduled playback
- [ ] Analytics tracking

## 📊 Status

**Version:** 1.0  
**Status:** ✅ Production Ready  
**Last Updated:** January 13, 2026

---

Made with ❤️ for Perfect DJ Music Bingo
