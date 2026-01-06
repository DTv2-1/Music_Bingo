# API Keys Configuration

This guide explains how to obtain and configure API keys for the Music Bingo system.

## ElevenLabs Text-to-Speech API

ElevenLabs provides the professional British voice announcements for the game.

### Getting Your API Key

#### 1. Create Account

Visit: https://elevenlabs.io/

1. Click "Sign Up" (top right)
2. Enter email and password
3. Verify email address
4. Complete account setup

#### 2. Choose Plan

**Free Tier (Testing Only):**
- 10,000 characters/month
- Enough for ~30-40 complete games
- Good for prototype testing

**Starter Plan ($5/month - Recommended for Production):**
- 30,000 characters/month
- ~100+ complete games
- Better voice quality
- Commercial license

**Creator Plan ($22/month - Recommended for Client):**
- 100,000 characters/month
- 300+ complete games
- Best value for regular use
- Priority support

#### 3. Get API Key

1. Log in to ElevenLabs dashboard
2. Click your profile (top right)
3. Select "Profile"
4. Find "API Key" section
5. Click "Copy API Key"
6. Save securely (treat like a password!)

**Example API key format:**
```
sk_1234567890abcdef1234567890abcdef1234567890abcdef
```

### Getting Voice ID

ElevenLabs provides pre-made voices. We recommend a British accent for UK pubs.

#### Recommended Voices

**British Male (Default):**
- **Voice ID:** `21m00Tcm4TlvDq8ikWAM`
- **Name:** "Rachel" (ironically named but British male voice)
- **Characteristics:** Clear, professional, authoritative
- **Best for:** Pubs, bars, professional events

**British Female Alternative:**
- **Voice ID:** `EXAVITQu4vr4xnSDxMaL`
- **Name:** "Bella"
- **Characteristics:** Warm, friendly, clear
- **Best for:** Younger crowds, casual venues

#### Finding Voice IDs

1. Go to: https://elevenlabs.io/voice-library
2. Browse pre-made voices
3. Filter by:
   - Language: English (UK)
   - Gender: Male/Female
   - Style: Professional
4. Click voice to hear sample
5. Copy Voice ID from URL or page

**Pro Tip:** Test multiple voices to find the best fit for your venue's vibe.

### Configuring in Code

#### Method 1: Direct in JavaScript (Quick)

Edit `frontend/game.js`:

```javascript
const CONFIG = {
    ELEVENLABS_API_KEY: 'sk_your_actual_api_key_here',  // Paste your key
    VOICE_ID: '21m00Tcm4TlvDq8ikWAM',  // British male (or your choice)
    // ...
};
```

**Pros:**
- Quick setup
- No environment variables needed

**Cons:**
- API key visible in code
- Must change in two places if deployed

#### Method 2: Environment Variables (Production)

Create `.env` file in project root:

```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=sk_your_actual_api_key_here
VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

Then update `game.js` to read from environment (requires build step):

```javascript
const CONFIG = {
    ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY,
    VOICE_ID: process.env.VOICE_ID,
    // ...
};
```

**Pros:**
- More secure
- Easy to change without code edits

**Cons:**
- Requires build process or server-side rendering
- More complex setup

**For Prototype:** Use Method 1 (direct in code).

### Testing API Configuration

#### Quick Test

1. Open `frontend/game.html` in browser
2. Open browser console (F12)
3. Click "NEXT SONG"
4. Check console for messages:

**Success:**
```
✓ Loaded 250 songs
🎙️ Announcing: "Mark Bohemian Rhapsody by Queen"
✓ Announcement complete
```

**Failure (Wrong API Key):**
```
✗ ElevenLabs API error: 401 - Unauthorized
```

**Failure (Wrong Voice ID):**
```
✗ ElevenLabs API error: 404 - Voice not found
```

#### Manual Test (cURL)

Test API directly from terminal:

```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM" \
  -H "xi-api-key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to Music Bingo!",
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
      "stability": 0.75,
      "similarity_boost": 0.75
    }
  }' \
  --output test.mp3
```

**Success:** Creates `test.mp3` file you can play.  
**Failure:** Shows error message.

---

## iTunes Search API

**Good news:** No API key needed! iTunes Search API is completely free and open.

### How It Works

The `generate_pool.py` script fetches songs from iTunes:

```python
ITUNES_SEARCH_BASE = "https://itunes.apple.com/search"

params = {
    "term": "Queen greatest hits",
    "entity": "song",
    "limit": 20,
    "country": "GB",  # UK catalog
    "media": "music"
}

response = requests.get(ITUNES_SEARCH_BASE, params=params)
```

**No authentication required!**

### Rate Limits

Apple doesn't publish official limits, but:
- **Recommended:** < 20 requests/minute
- **Our script:** ~15 requests total (with delays)
- **Safe usage:** Built-in 0.5s delay between requests

### Troubleshooting iTunes API

#### Issue: "Failed to fetch songs"

**Possible causes:**
1. No internet connection
2. iTunes API temporarily down
3. Too many requests (rate limited)

**Solutions:**
```bash
# Test API manually
curl "https://itunes.apple.com/search?term=test&entity=song&limit=1"

# Should return JSON with results
```

#### Issue: "No preview URLs"

Some songs don't have 30-second previews. The script automatically:
- Filters out songs without previews
- Keeps only songs with valid `previewUrl`
- Ensures 250+ songs with previews

---

## Security Best Practices

### Protecting API Keys

❌ **DON'T:**
- Commit API keys to Git (use `.gitignore`)
- Share API keys in screenshots
- Hard-code keys in public repositories
- Use production keys in development

✅ **DO:**
- Use `.env` files (add to `.gitignore`)
- Rotate keys regularly
- Use different keys for dev/production
- Monitor usage in ElevenLabs dashboard

### `.gitignore` Configuration

Ensure these are in `.gitignore`:

```bash
# Environment variables
.env
.env.local
.env.production

# API keys (if in separate file)
api_keys.txt
secrets.json

# Logs that might contain keys
*.log
```

### Rotating Keys

**When to rotate:**
- Keys accidentally committed to Git
- Team member leaves
- Suspicious usage detected
- Every 90 days (best practice)

**How to rotate:**
1. Generate new key in ElevenLabs dashboard
2. Update `.env` file
3. Update `game.js` with new key
4. Delete old key in ElevenLabs
5. Test to ensure working

---

## Cost Management

### Monitoring Usage

#### ElevenLabs Dashboard

1. Log in to ElevenLabs
2. Go to "Usage" page
3. View:
   - Characters used this month
   - Remaining credits
   - Usage history

#### Estimate Characters Per Game

**Average game (25 songs):**
- Each announcement: ~30-50 characters
- Total: 25 × 40 = ~1,000 characters
- Plus custom announcements: ~200 characters
- **Total per game: ~1,200 characters**

**Monthly estimates:**
- 4 games/week = ~5,000 characters/month (Free tier OK)
- 20 games/week = ~25,000 characters/month (Starter plan)
- 50 games/week = ~60,000 characters/month (Creator plan)

### Reducing Costs

**Option 1: Shorter Announcements**

Instead of:
```javascript
const text = `Mark ${track.title} by ${track.artist}`;
// "Mark Bohemian Rhapsody by Queen" (33 characters)
```

Use:
```javascript
const text = `${track.title}`;
// "Bohemian Rhapsody" (17 characters)
```

Saves ~50% on API costs.

**Option 2: Cache Announcements**

Generate all announcements once:
1. Run script to pre-generate TTS for all songs
2. Save MP3 files locally
3. Play from cache instead of API

**Pros:** Zero ongoing API costs  
**Cons:** Large storage (250 songs × 50KB = ~12MB)

**Option 3: Hybrid Approach**

- Pre-generate common announcements (welcome, rules, etc.)
- Use API for song-specific announcements
- Best balance of cost and flexibility

---

## Troubleshooting

### "ElevenLabs API error: 401"

**Cause:** Invalid API key

**Solutions:**
1. Copy API key again from ElevenLabs dashboard
2. Check for extra spaces before/after key
3. Ensure key starts with `sk_`
4. Try regenerating key

### "ElevenLabs API error: 402"

**Cause:** Out of credits

**Solutions:**
1. Check usage in dashboard
2. Upgrade plan or wait for monthly reset
3. Use cached audio temporarily

### "ElevenLabs API error: 404"

**Cause:** Invalid Voice ID

**Solutions:**
1. Check Voice ID is correct (copy from voice library)
2. Ensure voice is available in your region
3. Try default voice: `21m00Tcm4TlvDq8ikWAM`

### "ElevenLabs API error: 429"

**Cause:** Rate limit exceeded

**Solutions:**
1. Wait 1 minute and try again
2. Slow down requests (add delays)
3. Upgrade to higher plan for better limits

---

## Quick Setup Checklist

Use this checklist to verify your API configuration:

- [ ] ElevenLabs account created
- [ ] API key copied from dashboard
- [ ] Voice ID selected (British accent)
- [ ] API key added to `game.js`
- [ ] Voice ID added to `game.js`
- [ ] `.env` file created (optional)
- [ ] `.gitignore` includes `.env`
- [ ] Test announcement successful
- [ ] Usage monitored in dashboard
- [ ] Plan appropriate for usage

---

## Support Resources

### ElevenLabs
- **Documentation:** https://docs.elevenlabs.io/
- **Support:** support@elevenlabs.io
- **Discord:** https://discord.gg/elevenlabs
- **Status Page:** https://status.elevenlabs.io/

### iTunes API
- **Documentation:** https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
- **No official support** (free API)
- **Community:** Stack Overflow

### This Project
- **Developer:** Juan Diego Gutierrez
- **Email:** [Your email]
- **Issues:** Check README.md for contact info

---

**Last Updated:** January 6, 2026  
**Version:** 1.0
