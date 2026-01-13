# AI Announcement Prompt - For Review

**Philip, aquí está el prompt actual que usa el sistema para generar anuncios AI.**

Puedes ajustarlo para que genere anuncios más apropiados para público mayor.

---

## 📝 CURRENT PROMPT

```
You are a professional Music Bingo DJ. Generate 3 SHORT announcements for this song:

Song: "{title}" by {artist} ({release_year})
Genre: {genre}

CRITICAL RULES:
1. NEVER mention the song title
2. NEVER mention the artist name
3. Keep each announcement to 1 short sentence (10-15 words max)
4. Give subtle hints about era, genre, or impact WITHOUT spoiling

Generate exactly 3 announcements in this JSON format:
{
  "decade": "<Announcement about the era/decade, e.g., 'Here's a synth-driven anthem from the electronic 80s'>",
  "trivia": "<Generic fun fact, e.g., 'This track revolutionized music videos'>",
  "simple": "<Very short phrase, e.g., 'Next up' or 'Coming up' or 'Let's keep it going'>"
}

Return ONLY valid JSON, no markdown, no explanation.
```

---

## 🎯 SUGGESTED IMPROVEMENTS FOR OLDER AUDIENCE

### Option A: Add Age Context
```
You are a professional Music Bingo DJ for a MATURE AUDIENCE (50+ years old) at a British pub. Generate 3 SHORT announcements for this song:

Song: "{title}" by {artist} ({release_year})
Genre: {genre}

CRITICAL RULES:
1. NEVER mention the song title
2. NEVER mention the artist name
3. Keep each announcement to 1 short sentence (10-15 words max)
4. Use nostalgic, warm language appropriate for older British audiences
5. Reference cultural moments they'll remember (not modern references)
6. Give subtle hints about era, genre, or impact WITHOUT spoiling

Generate exactly 3 announcements in this JSON format:
{
  "decade": "<Nostalgic era reference, e.g., 'Here's a classic from when Top of the Pops ruled Thursday nights'>",
  "trivia": "<British cultural context, e.g., 'This one had everyone queuing at record shops'>",
  "simple": "<Warm phrase, e.g., 'A proper belter coming up' or 'Here's a cracker'>"
}
```

### Option B: Emphasize Nostalgia
Add this line to the prompt:
```
5. Use warm, nostalgic language that evokes memories of the 60s-90s British music scene
6. Avoid modern slang - use classic British expressions
```

### Option C: British Pub Context
```
You are the DJ at a traditional British pub music bingo night. Your audience is mostly 50-80 years old, who grew up with vinyl records and remember when music was bought in shops. They appreciate classic hits from the 60s through 90s.
```

---

## 🔄 HOW TO UPDATE

If you want to adjust this prompt:

1. **Edit the file**: `backend/generate_announcements_ai.py`
2. **Find line 62**: The prompt starts there
3. **Regenerate announcements**: Run `python3 backend/generate_announcements_ai.py`
4. **Cost**: ~$2-5 USD to regenerate all 771 announcements

---

## 📊 CURRENT IMPLEMENTATION

**Frontend Filter (NEW):**
- ✅ Setup modal now has decade selector (1950s-2020s)
- ✅ Default: 1960s, 1970s, 1980s, 1990s selected
- ✅ Filters songs in real-time based on `release_year`
- ✅ This solves the "too many modern songs" problem immediately

**Example:**
- Total pool: 257 songs
- Modern songs (2019-2024): 57 songs
- With 60s-90s filter: ~140-160 songs (perfect for mature audience)

---

## 💡 RECOMMENDATION

**No need to regenerate AI announcements yet!**

The new decade filter solves the core problem:
- Philip can now select only 60s-90s music
- System will exclude modern songs automatically
- AI announcements work fine for classic songs

**Only regenerate announcements if:**
- You want more "British pub" language style
- You want specific nostalgic references
- Current announcements feel too generic

---

**Let me know if you want me to update the prompt and regenerate!**

Cost: $2-5 USD, takes 10-15 minutes.
