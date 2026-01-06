# 🧪 TESTING CHECKLIST - Music Bingo Prototype

Use this checklist to verify all components are working before your demo.

## Pre-Testing Setup

- [ ] Python 3.10+ installed
- [ ] Dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] ElevenLabs account created
- [ ] API key configured in `frontend/game.js`

---

## Backend Scripts Testing

### generate_pool.py

**Run:**
```bash
cd backend
python generate_pool.py
```

**Verify:**
- [ ] Script completes without errors
- [ ] `data/pool.json` file created
- [ ] File contains 250+ songs
- [ ] All songs have `preview_url` field
- [ ] Preview URLs start with `https://`
- [ ] No duplicate song IDs

**Test with:**
```bash
python tests/test_pool.py
```

Expected output:
```
✓ Test passed: Pool has minimum songs
✓ Test passed: All songs have preview URLs
✓ Test passed: No duplicate songs
✓ Test passed: All songs have required fields
```

### generate_cards.py

**Run:**
```bash
python generate_cards.py
```

**Verify:**
- [ ] Script completes without errors
- [ ] `data/cards/music_bingo_cards.pdf` created
- [ ] PDF opens in Acrobat/Preview
- [ ] PDF has 50 pages
- [ ] Each card has 5×5 grid
- [ ] Center cell says "FREE" (red text)
- [ ] Songs are readable (not truncated)
- [ ] Card numbers 1-50 appear at bottom
- [ ] Perfect DJ footer visible

**Print Test:**
- [ ] Print 1 card on A4 paper
- [ ] Portrait orientation
- [ ] 100% scale (no "Fit to Page")
- [ ] Text is clear and readable
- [ ] Grid lines visible
- [ ] No text overflow

---

## Frontend Testing

### Page Load

**Open:** `frontend/game.html` in Chrome

**Verify:**
- [ ] Page loads without errors
- [ ] No console errors (press F12)
- [ ] Howler.js loaded (check console)
- [ ] Purple gradient background visible
- [ ] All buttons visible
- [ ] Stats show: 0 called, X remaining

### API Configuration

**Check Console:**
```
✓ Loaded 250 songs
✓ Loaded announcements for: The Royal Oak
✓ Music Bingo game script loaded
```

**If errors:**
- [ ] `pool.json not found` → Run `generate_pool.py`
- [ ] `announcements.json not found` → File should exist in `data/`

### Basic Functionality

#### Test: Next Song Button

**Steps:**
1. Click anywhere on page (unlock audio)
2. Press "NEXT SONG" button
3. Wait for full sequence

**Verify:**
- [ ] Button disables during playback
- [ ] Status shows: "🎙️ Announcing..."
- [ ] AI voice says: "Mark [Song] by [Artist]"
- [ ] Status shows: "🎵 Playing song preview..."
- [ ] 5-second preview plays
- [ ] Status returns to: "Ready for next song"
- [ ] Button re-enables
- [ ] Called count increases to 1
- [ ] Remaining count decreases by 1
- [ ] Current track displays (artwork + title + artist)
- [ ] Song appears in "Called Songs" list

**Repeat 3 times** to ensure consistency.

#### Test: Keyboard Shortcuts

**Space/Enter:**
- [ ] Space bar triggers next song
- [ ] Enter key triggers next song
- [ ] Works same as button click

**A Key:**
- [ ] Opens announcement prompt
- [ ] Shows pre-configured announcements
- [ ] Can select by number
- [ ] Can type custom text
- [ ] AI voice speaks announcement
- [ ] Returns to ready state

**Ctrl+R:**
- [ ] Shows confirmation dialog
- [ ] Resets called songs list
- [ ] Resets statistics
- [ ] Shuffles song order

#### Test: Custom Announcements

**Steps:**
1. Press "Announcement" button (or A key)
2. Enter "1" (first announcement)
3. Wait for playback

**Verify:**
- [ ] Announcement button disables
- [ ] Status shows: "📢 Playing announcement..."
- [ ] AI voice speaks announcement
- [ ] Status returns to normal
- [ ] Button re-enables

**Test custom text:**
1. Press "Announcement"
2. Type: "This is a test"
3. Submit

**Verify:**
- [ ] AI voice says: "This is a test"
- [ ] Pronunciation is clear

#### Test: Reset Game

**Steps:**
1. Call 5-10 songs
2. Press "Reset Game" button
3. Confirm dialog

**Verify:**
- [ ] Confirmation dialog appears
- [ ] Called songs list clears
- [ ] Called count returns to 0
- [ ] Remaining count returns to max
- [ ] Current track hides
- [ ] Audio stops (if playing)
- [ ] Songs are reshuffled (different order)

#### Test: Game Completion

**Steps:**
1. Call all 250+ songs (or modify code to use fewer)
2. Try to press "NEXT SONG"

**Verify:**
- [ ] Alert: "All songs have been called!"
- [ ] Status shows: "🎉 All songs called!"
- [ ] Button does nothing
- [ ] Must reset to continue

---

## Audio Testing

### TTS (ElevenLabs)

**Test Announcement:**
- [ ] Voice is clear and understandable
- [ ] British accent (not American)
- [ ] Male voice (or as configured)
- [ ] Volume is consistent
- [ ] No distortion
- [ ] No latency issues

**Test Different Songs:**
- [ ] "Bohemian Rhapsody by Queen" - clear
- [ ] "Let It Be by The Beatles" - clear
- [ ] Long titles don't get cut off
- [ ] Special characters pronounced correctly

### Song Previews (iTunes)

**Test Preview Playback:**
- [ ] Preview starts immediately after announcement
- [ ] Audio is clear (no distortion)
- [ ] Preview stops after exactly 5 seconds
- [ ] No overlap with next announcement
- [ ] Volume is consistent across songs

**Test Multiple Songs:**
- [ ] Rock song plays correctly
- [ ] Pop song plays correctly
- [ ] Dance song plays correctly
- [ ] No loading delays between songs

### Audio on Different Systems

**Laptop Speakers:**
- [ ] Voice audible at 80% volume
- [ ] Music preview audible
- [ ] No distortion at high volume

**External Speakers:**
- [ ] Connect via 3.5mm cable
- [ ] Voice clear through system
- [ ] Music clear through system
- [ ] Volume levels appropriate

**Bluetooth Speaker:**
- [ ] Pair successfully
- [ ] No audio lag
- [ ] Voice clear
- [ ] Music clear

---

## Browser Compatibility

### Chrome (Primary)

- [ ] Page loads correctly
- [ ] Audio plays without issues
- [ ] No console errors
- [ ] All buttons work
- [ ] Keyboard shortcuts work
- [ ] Responsive on laptop screen

### Firefox

- [ ] Page loads correctly
- [ ] Audio plays (may need click first)
- [ ] No console errors
- [ ] All buttons work
- [ ] Keyboard shortcuts work

### Safari

- [ ] Page loads correctly
- [ ] Audio plays (click required)
- [ ] No console errors
- [ ] All buttons work
- [ ] Keyboard shortcuts work

### Mobile (Optional)

**iOS Safari:**
- [ ] Page loads (landscape recommended)
- [ ] Buttons large enough to tap
- [ ] Audio works after tap
- [ ] Responsive layout

**Android Chrome:**
- [ ] Page loads
- [ ] Buttons work
- [ ] Audio works
- [ ] Responsive layout

---

## Integration Testing

### Full Game Simulation

**Setup:**
1. Print 5 bingo cards
2. Gather 2-3 friends
3. Distribute cards and markers

**Play 25 songs:**
- [ ] Timing feels right (~15-20s per song)
- [ ] Players can hear and recognize songs
- [ ] Players can mark cards in time
- [ ] Host can track called songs easily
- [ ] Winners can be verified

**Verify:**
- [ ] Someone gets a line (~15-20 songs)
- [ ] Can verify winner against screen
- [ ] Game can continue or reset
- [ ] No confusion about which songs were called

### Error Handling

**Test Network Failure:**
1. Start game
2. Disable internet
3. Press "NEXT SONG"

**Verify:**
- [ ] Clear error message displayed
- [ ] Game doesn't crash
- [ ] Can recover when internet returns

**Test Invalid API Key:**
1. Change API key to gibberish
2. Reload page
3. Press "NEXT SONG"

**Verify:**
- [ ] Error message: "ElevenLabs API error: 401"
- [ ] Game doesn't crash
- [ ] Song preview still plays

**Test Missing pool.json:**
1. Rename `data/pool.json`
2. Reload page

**Verify:**
- [ ] Error: "Failed to load pool.json"
- [ ] Clear instruction to run `generate_pool.py`

---

## Performance Testing

### Load Time

- [ ] Page loads in < 2 seconds
- [ ] `pool.json` loads in < 1 second
- [ ] No visible lag

### Memory Usage

**Check in Chrome DevTools:**
1. Open page
2. DevTools → Performance Monitor
3. Play 50 songs

**Verify:**
- [ ] Memory stays < 200MB
- [ ] No memory leaks
- [ ] CPU usage drops between songs

### Audio Latency

- [ ] TTS starts < 1 second after button press
- [ ] Preview starts < 1 second after TTS ends
- [ ] No perceptible lag between songs

---

## User Experience Testing

### Clarity

**Ask test users:**
- [ ] "Can you hear the announcements clearly?"
- [ ] "Can you recognize the songs?"
- [ ] "Is the timing too fast/slow?"
- [ ] "Are the cards easy to read?"
- [ ] "Is the interface intuitive?"

### Pub Environment Simulation

**Test in noisy environment:**
1. Play background music/TV
2. Simulate 70-80dB noise
3. Test audio clarity

**Verify:**
- [ ] Voice cuts through noise
- [ ] Song previews recognizable
- [ ] Volume adjustable to compensate

---

## Pre-Demo Checklist

**24 Hours Before:**
- [ ] All tests passed
- [ ] Fresh song pool generated
- [ ] 50+ cards printed
- [ ] Laptop fully charged
- [ ] API key has sufficient credits
- [ ] Backup plan prepared

**1 Hour Before:**
- [ ] Venue sound system tested
- [ ] Audio levels calibrated
- [ ] Internet connection verified
- [ ] Backup internet (phone hotspot)
- [ ] Page bookmarked/loaded
- [ ] Audio unlocked (clicked page)

**Go/No-Go Decision:**

✅ **GO** if:
- All critical tests passed
- Audio quality is good
- API key working
- Cards printed and readable

🛑 **NO-GO** if:
- TTS not working
- Songs won't play
- Cards unreadable
- Major bugs present

---

## Bug Tracking

Found a bug? Document it:

**Bug Template:**
```
Title: [Brief description]
Steps to Reproduce:
1. 
2. 
3. 
Expected: [What should happen]
Actual: [What actually happened]
Severity: [Critical/High/Medium/Low]
Browser: [Chrome/Firefox/Safari]
Screenshot: [If applicable]
```

**Example:**
```
Title: Button doesn't disable during playback
Steps to Reproduce:
1. Press "NEXT SONG"
2. Immediately press again
3. Two songs overlap
Expected: Button should be disabled
Actual: Can press multiple times
Severity: High
Browser: Chrome 120
```

---

## Sign-Off

**Tested by:** ___________________  
**Date:** ___________________  
**All critical tests passed:** ☐ Yes ☐ No  
**Ready for demo:** ☐ Yes ☐ No  
**Notes:**

---

**Last Updated:** January 6, 2026  
**Version:** 1.0
