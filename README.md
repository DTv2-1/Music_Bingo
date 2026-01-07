# Music Bingo Prototype - Perfect DJ

Professional Music Bingo system for pubs and bars.

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Generate Song Pool (2-3 minutes)
```bash
python generate_pool.py
```

This creates `data/pool.json` with 250+ popular songs from iTunes.

### 3. Generate Bingo Cards (30 seconds)
```bash
python generate_cards.py
```

This creates `data/cards/music_bingo_cards.pdf` with 50 unique cards.

### 4. Configure ElevenLabs API Key

Copy template and add your API key:
```bash
cp .env.example .env
nano .env  # Add ELEVENLABS_API_KEY=sk_...
```

### 5. Start Backend Server

```bash
python server.py
```

Server will start on http://localhost:5000

### 6. Open Game Interface

Open browser and go to:
```
http://localhost:5000
```

Click page to unlock audio, then press "NEXT SONG"!

## Usage in Pub

### Local Demo (Laptop)
1. Start backend server: `python backend/server.py`
2. Connect laptop to pub's sound system
3. Open http://localhost:5000 in browser
4. Distribute printed cards to players
5. Press "NEXT SONG" button every ~15 seconds
6. AI voice announces song + plays 5-second preview
7. Players mark their cards
8. Verify winners manually against called songs list

### Online Demo (Digital Ocean)
1. Deploy to Digital Ocean (see DEPLOYMENT.md)
2. Share URL with client (e.g., http://musicbingo.perfectdj.co.uk)
3. Client can test from anywhere
4. Same interface, hosted online

## Keyboard Shortcuts

- **Space/Enter** - Next song
- **A** - Custom announcement
- **Ctrl+R** - Reset game

## Requirements

- Python 3.10+
- Modern web browser (Chrome recommended)
- Internet connection (for API calls)
- Sound system or laptop speakers
- **For deployment:** Digital Ocean account (~$6/month)

## Cost

**Local Demo (Laptop):**
- Song previews: £0 (iTunes API is free)
- PDF generation: £0 (local processing)
- Voice (ElevenLabs): Client provides Premium account
- Total: **£0**

**Online Demo (Digital Ocean):**
- Server hosting: £5-6/month
- Everything else: £0
- Total: **~£6/month**

## Project Structure

```
music-bingo/
├── backend/              # Python scripts + Flask server
│   ├── generate_pool.py  # Fetch songs from iTunes
│   ├── generate_cards.py # Create PDF bingo cards
│   ├── server.py         # Flask API server (NEW)
│   └── config.py         # Configuration
├── frontend/             # Web interface
│   ├── game.html         # Main game interface
│   ├── styles.css        # Styling
│   └── game.js           # Game logic
├── data/                 # Generated data
│   ├── pool.json         # Song pool (generated)
│   ├── announcements.json # Venue announcements
│   └── cards/            # PDF cards (generated)
├── docs/                 # Documentation
├── DEPLOYMENT.md         # Digital Ocean deployment guide (NEW)
└── LOCAL_TESTING.md      # Local testing guide (NEW)
```
│   ├── SETUP.md          # Setup instructions
│   ├── USAGE.md          # How to run in pub
│   └── API_KEYS.md       # API configuration
└── tests/                # Unit tests
```

## Features

✅ 250+ popular songs from iTunes  
✅ Professional AI voice announcements (British accent)  
✅ 50 unique printable bingo cards  
✅ Simple one-button operation  
✅ Track called songs automatically  
✅ Custom venue announcements  
✅ Mobile responsive design  
✅ Keyboard shortcuts  

## Documentation

- [Setup Instructions](docs/SETUP.md) - Installation and deployment
- [Usage Guide](docs/USAGE.md) - How to run in a pub
- [API Keys Configuration](docs/API_KEYS.md) - ElevenLabs setup

## Development Timeline

Estimated: 17-25 hours total
- Backend scripts: 4-6 hours
- Frontend interface: 6-8 hours
- Testing & polish: 4-6 hours
- Documentation: 3-5 hours

## Support

For issues or questions, contact Juan Diego Gutierrez.

---

**Version:** 1.0  
**Last Updated:** January 6, 2026  
**Client:** Perfect DJ (perfectdj.co.uk)
# Test deployment
