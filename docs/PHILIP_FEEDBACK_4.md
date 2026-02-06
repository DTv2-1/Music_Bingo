# Philip's Feedback - February 6, 2026 (Testing Session)

## Testing Context
- **Date**: February 6, 2026 (7:25 AM - 11:38 AM)
- **Environment**: Development branch
- **Tester**: Philip Hill

---

## 🐛 Critical Bugs

### 1. **Pause Button Not Working During Background Music**
- **Issue**: Pause functionality only works during track playback, not during background music
- **Location**: `frontend/game.js` - `pauseCurrentTrack()` function
- **Priority**: HIGH
- **Current Behavior**: Button doesn't pause when background music is playing
- **Expected Behavior**: Pause should work at any point in the game

### 2. **10-Song Summary Timing Issue**
- **Issue**: Summary plays after songs 1-9 (before track 10), not after track 10
- **Location**: `frontend/game.js` - `playNextTrack()` function (line ~1525-1540)
- **Priority**: HIGH
- **Current Code Logic**: 
  ```javascript
  if (songsPlayed > 0 && songsPlayed % 10 === 0)
  ```
- **Problem**: Triggers at song 10, 20, 30 but BEFORE playing that track
- **Expected Behavior**: Should play summary AFTER tracks 10, 20, 30, etc.
- **Same Issue**: Occurs at 10-19 (summary after song 19 instead of 20)

---

## 🎯 New Feature Requests

### 3. **Add Interesting Track Info for Every Track**
- **Request**: Add AI-generated interesting facts/trivia for each song announcement
- **Location**: `frontend/game.js` - `announceTrack()` function
- **Priority**: MEDIUM
- **Current Behavior**: Only announces title and artist
- **Requested Behavior**: Add interesting facts about the song/artist
- **Example**: "Straight out of the disco fuelled 1970's, here's Stayin' Alive by the Bee Gees"

### 4. **Increase Track Preview Duration to 20 Seconds**
- **Request**: Extend song preview from current duration to 20 seconds
- **Location**: `frontend/game.js` - `CONFIG.PREVIEW_DURATION_MS`
- **Priority**: MEDIUM
- **Current Value**: Unknown (need to check)
- **Requested Value**: 20,000ms (20 seconds)

### 5. **Expand Track Info Variation**
- **Request**: Add more variety to AI-generated track introductions
- **Location**: Backend TTS generation or track announcement logic
- **Priority**: MEDIUM
- **Issue**: Repetitive phrases like "Straight out of the disco fuelled 1970's"
- **Solution**: 
  - Expand AI prompt templates with more variations
  - Add decade-specific introduction templates
  - Include genre-specific phrases
  - Add artist background variations

### 6. **Thank You Message When Game Ends**
- **Request**: Add closing announcement when all tracks are called
- **Location**: `frontend/game.js` - End of `playNextTrack()` or new `announceGameEnd()` function
- **Priority**: MEDIUM
- **Content Examples**:
  - "That's all the tracks, folks! Thanks for playing Music Bingo tonight!"
  - "And that's a wrap! Hope you had a great time. See you next week!"
  - "All done! Thanks for joining us for Music Bingo at The Admiral Rodney!"

---

## 🎁 Prize Claiming Interface

### 7. **Add Three Buttons for Prize Claims**
- **Request**: Add buttons for different prize types when someone wins
- **Location**: `frontend/game.html` + `frontend/game.js`
- **Priority**: HIGH
- **Buttons Needed**:
  1. **"Line Prize Claimed"** - For single line winners
  2. **"Two Lines Prize Claimed"** - For double line winners  
  3. **"Full House Prize Claimed"** - For full card winners
- **Functionality**:
  - Buttons should appear when host needs to verify/confirm a winner
  - Should log the prize claim with timestamp
  - Should allow game to continue after prize is claimed
  - May need to pause game temporarily during verification
- **UI Placement**: Near the host controls (probably below NEXT SONG/PAUSE button)
- **Reference**: See attached screenshot from Philip

---

## 🎵 Jingle Generator Issues

### 8. **Jingle Text Not Preserved on Preview**
- **Issue**: When user clicks "Previous" button after previewing, entered text is deleted
- **Location**: `frontend/jingle-manager.html` + `frontend/jingle-manager.js`
- **Priority**: MEDIUM
- **Current Behavior**: Previous button clears the text field
- **Expected Behavior**: Text should be saved/restored when navigating back from preview
- **Impact**: Users lose text if they need to fix spelling mistakes
- **Solution**: 
  - Store text in sessionStorage or component state
  - Restore text when returning from preview step

### 9. **Jingle Service Error: Unexpected Keyword Argument**
- **Issue**: `JingleService.create_jingle() got an unexpected keyword argument 'task_callback'`
- **Location**: Backend jingle generation service
- **Priority**: HIGH
- **Error Message**: See screenshot attached
- **Context**: Error occurs during jingle generation
- **Solution**: Remove or fix the `task_callback` parameter in the jingle service call

---

## 📋 Implementation Priority

### Phase 1 - Critical Fixes (Do First)
1. ✅ Fix 10-song summary timing (play AFTER track 10, not before)
2. ✅ Fix pause button to work during background music
3. ✅ Fix jingle generator `task_callback` error

### Phase 2 - High Priority Features
4. ✅ Add three prize claim buttons (Line, Two Lines, Full House)
5. ✅ Add thank you message at game end
6. ✅ Preserve jingle text on preview navigation

### Phase 3 - Medium Priority Enhancements
7. ✅ Add interesting track info for every song
8. ✅ Increase track preview to 20 seconds
9. ✅ Expand track info variation (more templates)

---

## 📝 Technical Notes

### Summary Timing Fix
**Current Logic** (WRONG):
```javascript
// This checks BEFORE playing the track
const songsPlayed = gameState.called.length;
if (songsPlayed > 0 && songsPlayed % 10 === 0) {
    await announceTenSongSummary();
}
```

**Should Be** (CORRECT):
```javascript
// Check AFTER track is added to called list
if (gameState.called.length > 0 && gameState.called.length % 10 === 0) {
    // Now we've actually played 10, 20, 30 tracks
    await announceTenSongSummary();
}
```

### Track Info Templates
Create multiple introduction templates:
- Decade-based: "From the [groovy/electric/radical] [decade]..."
- Genre-based: "Here's a [genre] classic from..."
- Artist-based: "The legendary [artist] brings us..."
- Hit-based: "A number one hit from [year]..."
- Random facts: "Did you know this song was [fact]..."

---

## ✅ Action Items for Juan Diego

- [ ] Fix 10-song summary to trigger AFTER playing track 10, 20, 30
- [ ] Fix pause button to work during background music phase
- [ ] Add three prize claim buttons with proper UI
- [ ] Add game end thank you announcement
- [ ] Fix jingle generator text preservation on back navigation
- [ ] Fix jingle service `task_callback` error
- [ ] Extend track preview duration to 20 seconds
- [ ] Add interesting track info for each song announcement
- [ ] Create variation templates for track introductions (minimum 10-15 variations per category)

---

## 🧪 Testing Schedule

- **Next Test**: Philip will test later today (February 6, 2026)
- **Environment**: Development branch
- **Focus Areas**: 
  - Summary timing
  - Pause functionality
  - Prize claim buttons
  - Track info variety
