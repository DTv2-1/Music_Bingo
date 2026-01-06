# 🚀 QUICK START - Testing Locally

Before deploying to Digital Ocean, test the server setup locally.

## Step 1: Install Server Dependencies

```bash
cd /Users/1di/Music_Bingo/backend
pip install -r requirements.txt
```

This installs Flask, Flask-CORS, and Gunicorn (in addition to existing packages).

## Step 2: Configure ElevenLabs API Key

```bash
# Copy template
cp .env.example .env

# Edit the file
nano .env
```

Add your ElevenLabs API key:
```bash
ELEVENLABS_API_KEY=sk_your_actual_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

Save and exit.

## Step 3: Make Sure Data Files Exist

```bash
# If you haven't generated them yet:
python generate_pool.py
python generate_cards.py
```

## Step 4: Start Backend Server

```bash
cd /Users/1di/Music_Bingo/backend
python server.py
```

You should see:
```
============================================================
🎵 MUSIC BINGO SERVER
============================================================
✓ Backend server starting...
✓ ElevenLabs API key configured: True
✓ Pool file exists: True
✓ Bingo cards exist: True

📡 Server will be available at:
   http://localhost:5000
============================================================

 * Running on http://0.0.0.0:5000
```

## Step 5: Open Game in Browser

Open your browser and go to:
```
http://localhost:5000
```

Or just:
```bash
open http://localhost:5000
```

## Step 6: Test the Game

1. **Click anywhere** on the page (unlocks audio in browser)
2. **Press "NEXT SONG"** button
3. You should hear:
   - AI voice announcing the song
   - 5-second preview of the song
4. Check that:
   - Statistics update (songs called/remaining)
   - Called songs list displays
   - Status messages show progress

## Step 7: Test API Endpoints

Open a new terminal and test:

```bash
# Health check
curl http://localhost:5000/api/health

# Get song pool
curl http://localhost:5000/api/pool | head -n 20

# Get announcements
curl http://localhost:5000/api/announcements
```

## Step 8: Download Bingo Cards

Go to:
```
http://localhost:5000/data/cards/music_bingo_cards.pdf
```

Download and print a few cards for testing.

---

## ✅ Success Checklist

- [ ] Backend server starts without errors
- [ ] Game interface loads at http://localhost:5000
- [ ] TTS announcements play correctly
- [ ] Song previews play for 5 seconds
- [ ] Statistics update after each song
- [ ] Called songs list displays correctly
- [ ] PDF cards download successfully

---

## If Everything Works:

**You're ready to deploy to Digital Ocean!**

See `DEPLOYMENT.md` for complete deployment guide.

---

## Troubleshooting

### Backend won't start

**Check Python version:**
```bash
python3 --version  # Need 3.10+
```

**Check if port 5000 is already in use:**
```bash
lsof -i :5000
# If something is using it, stop it or change port in server.py
```

### TTS not working

**Check API key:**
```bash
cat backend/.env | grep ELEVENLABS_API_KEY
# Make sure it's not empty
```

**Check logs in terminal** where server is running - look for error messages.

### Songs not loading

**Make sure pool.json exists:**
```bash
ls data/pool.json
```

**If not, generate it:**
```bash
cd backend
python generate_pool.py
```

---

## Architecture

**How it works:**

1. **Backend (server.py):**
   - Flask server on port 5000
   - Serves frontend static files
   - Provides API endpoints:
     - `/api/health` - Health check
     - `/api/pool` - Get songs
     - `/api/announcements` - Get announcements
     - `/api/tts` - Generate TTS (proxies ElevenLabs)
   - Keeps API key secure (not exposed to frontend)

2. **Frontend (game.html + game.js):**
   - Loaded from backend server
   - Makes API calls to backend
   - Uses Howler.js for audio playback
   - No direct API keys in frontend code

3. **Data:**
   - `pool.json` - 250+ songs
   - `announcements.json` - Venue info
   - `cards/music_bingo_cards.pdf` - Printable cards

---

## Next Step

Once local testing is complete, proceed to:

**→ DEPLOYMENT.md** - Deploy to Digital Ocean for client access

---

**Testing time:** 5-10 minutes  
**Local cost:** £0  
**Ready for production?** ✅
