# How to Run Music Bingo in a Pub

## Before the Event

### Day Before Event

#### 1. Generate Fresh Song Pool (Optional but Recommended)
```bash
python backend/generate_pool.py
```

This fetches the latest popular songs. Recommended to run weekly to keep content fresh.

#### 2. Print Bingo Cards

Print `data/cards/music_bingo_cards.pdf`:
- **Paper:** A4 size
- **Orientation:** Portrait
- **Scale:** 100% (DO NOT use "Fit to Page")
- **Quantity:** 50 cards (one per player)
- **Extras:** Print 10-20 extra cards as backup

**Printing Tips:**
- Use slightly heavier paper (100-120gsm) for durability
- Consider laminating cards if reusing
- Print in color for better visual appeal
- Number cards in top corner for easy tracking

#### 3. Test Equipment
- [ ] Charge laptop fully (bring charger as backup)
- [ ] Test audio output with headphones
- [ ] Open `frontend/game.html` and test one song
- [ ] Verify ElevenLabs API is working (check voice announcement)
- [ ] Bookmark game page for quick access

#### 4. Prepare Materials
- [ ] Printed bingo cards (50+)
- [ ] Daubers/markers (1 per player)
- [ ] Prize for winner (£50 bar tab, gift card, etc.)
- [ ] Laptop + charger
- [ ] Audio cable (3.5mm to venue's sound system)
- [ ] Extension cord/power strip

### 1 Hour Before Event

#### Arrive Early
Get to venue 60 minutes before start time to set up.

#### 1. Connect to Sound System

**Option A: Direct Cable**
```
Laptop headphone jack → 3.5mm cable → Venue's AUX input
```

**Option B: Bluetooth**
- Pair laptop with venue's Bluetooth speaker
- Test latency (should be minimal)

**Option C: Laptop Speakers Only**
- Last resort if no sound system
- Position laptop centrally
- Crank volume to maximum

#### 2. Test Audio Levels

1. Open `frontend/game.html`
2. Click "NEXT SONG" to play one track
3. Adjust laptop volume to 80-90%
4. Adjust venue's sound system to comfortable level
5. Test from back of room - should be clearly audible

**Volume Guidelines:**
- Pub environment is loud (70-80dB ambient)
- Voice announcements should be 5-10dB louder
- Music preview should be recognizable but not overwhelming
- Test during actual crowd noise if possible

#### 3. Position Laptop

- Central location for host to see
- Angle screen away from crowd (host only)
- Near sound system or long cable
- Stable surface (not wobbly table)
- Power outlet nearby

#### 4. Unlock Browser Audio

**CRITICAL:** Click anywhere on the page BEFORE starting. This unlocks browser audio due to autoplay policies.

---

## During the Game

### Starting the Event

#### 1. Distribute Cards
- Give 1 card per player (or group)
- Hand out daubers/markers
- Keep 5-10 cards as spares

#### 2. Explain Rules (2 minutes)

**Say this:**

> "Welcome to Music Bingo! Here's how to play:
> 
> 1. You'll hear a voice announce a song: 'Mark [Song Title] by [Artist]'
> 2. Then you'll hear a 5-second preview of that song
> 3. If it's on your card, mark it with your dauber
> 4. First person to get a winning pattern shouts 'BINGO!'
> 
> **Winning Patterns:**
> - Any full line (horizontal, vertical, or diagonal)
> - Four corners
> - Full house (entire card)
> 
> **Important:**
> - Listen carefully - songs go by fast!
> - Mark the FREE space in the center (it's automatic)
> - When you win, bring your card to the bar immediately
> 
> Good luck! Let's start!"

#### 3. Start Game

Press **"NEXT SONG"** button (or press Space/Enter).

Sequence per song:
1. Voice announces: "Mark [Song] by [Artist]" (2-3 seconds)
2. 5-second preview plays
3. ~10 seconds of silence (players marking cards)
4. Press "NEXT SONG" again

**Timing:** Approximately 15-20 seconds per song total.

### Running the Game

#### Host Responsibilities

✅ **DO:**
- Press "NEXT SONG" every 15-20 seconds
- Watch for raised hands (winners)
- Verify winners promptly
- Keep energy high between songs
- Make eye contact with players
- Use custom announcements for breaks

❌ **DON'T:**
- Rush through songs (15s minimum)
- Skip verification (check every card)
- Let technical issues show (stay calm)
- Turn your back to crowd
- Forget to hydrate (long sessions)

#### Keyboard Shortcuts (For Efficiency)

- **Space/Enter** - Next song (faster than clicking)
- **A** - Custom announcement
- **Ctrl+R** - Reset game (start new round)

#### Handling Winner Claims

When someone shouts "BINGO!":

1. **Pause Game Immediately**
   - Don't start next song
   - Tell crowd: "Hold on, checking winner!"

2. **Get Their Card**
   - Player brings card to you
   - Stay at laptop (can see called songs list)

3. **Verify Card**
   - Check "Called Songs" list on screen
   - Ensure they have winning pattern:
     - **Line:** 5 in a row (any direction)
     - **Four Corners:** All 4 corners marked
     - **Full House:** Entire card marked
   - Each marked song must be in called list

4. **Declare Result**
   
   **If VALID:**
   ```
   "We have a WINNER! [Player name], congratulations!"
   *Applause*
   "Come to the bar to claim your prize!"
   ```
   
   **If INVALID:**
   ```
   "Not quite - you're missing [song name]. Keep playing!"
   *Polite applause for effort*
   ```

5. **Continue or Start New Round**
   - If minor prize: Continue same round
   - If major prize: Reset game for new round

### Custom Announcements

Press **"Announcement"** button (or press A key).

**Pre-configured announcements:**
1. Welcome message
2. Reminder to mark cards
3. Winner verification
4. Happy hour announcement
5. Next round starting
6. Thank you message

**Custom text:**
- Type any message in prompt
- AI voice reads it out
- Use for:
  - Special offers
  - Event updates
  - Funny commentary
  - Crowd engagement

**Example announcements:**

```
"Don't forget - happy hour ends in 10 minutes!"
"We're halfway through! Still time to win!"
"If you need another dauber, raise your hand!"
"The next winner gets a free pint!"
"Remember to share photos with #MusicBingo!"
```

### Between Rounds

#### When to Reset

- After full house winner
- Every 25-30 songs (prevents fatigue)
- Between game "sessions" (e.g., every hour)
- If multiple winners and need fresh start

#### How to Reset

1. Press **"Reset Game"** button
2. Confirm popup
3. Collect used cards
4. Distribute fresh cards
5. Quick rules reminder (30 seconds)
6. Start new round

---

## Troubleshooting During Event

### Audio Not Playing

**Symptoms:** Button pressed but no sound

**Solutions:**
1. Check laptop volume (should be 80-90%)
2. Check venue sound system input
3. Try pressing "Next Song" again
4. Click page and try again (re-unlock audio)
5. Refresh page as last resort

### Button Not Working

**Symptoms:** Can't press "Next Song"

**Causes:**
- Song still playing (wait)
- Browser frozen (refresh page)
- Clicked too many times (wait 5 seconds)

**Solution:** Wait for current audio to finish, then try again.

### Wrong Song Announced

**Rare but possible:**

1. Check "Called Songs" list - that's the source of truth
2. Verbally correct: "Sorry, that was [Correct Song], mark that one!"
3. Continue as normal

### Laptop Battery Dying

1. Connect to power immediately
2. Announce 2-minute break if needed
3. Keep playing if possible (race against time!)
4. Worst case: Switch to backup plan (see below)

### Internet Connection Lost

**Good news:** Game works offline after initial load!

**But:** No new TTS announcements

**Solution:**
- Continue with music previews only
- You verbally announce songs
- Or use pre-loaded announcements

### Backup Plan (Nuclear Option)

If tech completely fails:

1. **Manual Mode:** You read song titles from printed list
2. **Phone Playlist:** Switch to pre-made Spotify playlist
3. **Traditional Host:** Abandon tech, be the DJ yourself

---

## After the Event

### Immediate (Before Leaving Venue)

- [ ] Thank players
- [ ] Collect leftover cards (reusable if not damaged)
- [ ] Ask for feedback
- [ ] Take photos (marketing material)
- [ ] Schedule next event if successful

### Next Day

- [ ] Email thank you to venue owner
- [ ] Share photos on social media
- [ ] Note any issues for improvement
- [ ] Update announcements.json if needed

### Collect Feedback

Ask venue staff:
- "How was the crowd reaction?"
- "Would you book this again?"
- "Any technical issues I missed?"
- "Suggested improvements?"

Ask players (casual):
- "Did you enjoy it?"
- "Was audio clear enough?"
- "Cards easy to read?"

---

## Tips for Success

### Engagement Tips

✅ **High Energy:**
- Smile and make eye contact
- Hype up winners
- Encourage crowd singing along
- Make jokes between songs

✅ **Smooth Operation:**
- Practice timing (15-20s per song)
- Keep laptop screen visible to you
- Have water nearby (lots of talking)
- Stand/sit where you can see whole room

✅ **Professional Polish:**
- Arrive early (never rush setup)
- Dress appropriately (smart casual)
- Stay sober (you're working!)
- Have backup plan ready

### Common Mistakes to Avoid

❌ Going too fast (< 10s between songs)  
❌ Not testing audio beforehand  
❌ Forgetting to verify winners  
❌ Turning back to crowd  
❌ Getting flustered by technical issues  

### Timing Guide

**Full Game (25 songs):**
- Duration: ~8-10 minutes
- Winners: Usually 1-3
- Best for: Quick rounds

**Long Game (50 songs):**
- Duration: ~15-20 minutes
- Winners: 3-6
- Best for: Main event

**Marathon (All songs):**
- Duration: ~60-90 minutes
- Take breaks every 30 minutes
- Best for: Dedicated bingo nights

---

## Emergency Contacts

**Technical Issues:**
- Developer: [Your contact info]
- ElevenLabs Support: support@elevenlabs.io

**Client Contact:**
- Perfect DJ: [Philip's contact]

---

## Quick Reference Card

Print this and keep near laptop:

```
=================================
MUSIC BINGO QUICK REFERENCE
=================================

KEYBOARD SHORTCUTS:
  Space/Enter → Next Song
  A → Announcement  
  Ctrl+R → Reset Game

TIMING:
  Per Song: 15-20 seconds
  Full Round: 25 songs = 10 min

WINNING PATTERNS:
  - Any line (5 in row)
  - Four corners
  - Full house

VERIFICATION:
  1. Check their card
  2. Match against screen list
  3. Confirm pattern
  4. Announce result

TROUBLESHOOTING:
  - No sound? Check volume + system
  - Button stuck? Wait for audio
  - Battery low? Plug in NOW

EMERGENCY:
  Manual mode: Read songs yourself
  Backup: Phone playlist

=================================
```

---

**Good luck with your Music Bingo event!** 🎵🎉

Remember: Stay calm, have fun, and the crowd will too!
