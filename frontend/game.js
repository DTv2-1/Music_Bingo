/**
 * game.js - Music Bingo Game Logic
 * 
 * Features:
 * - iTunes preview playback (5 seconds default)
 * - ElevenLabs TTS announcements
 * - Track remaining songs
 * - Display called songs list
 * - Custom announcements
 * 
 * Configuration loaded from config.js (reads from .env)
 */

// ============================================================================
// CONFIGURATION - Now loaded from environment variables
// ============================================================================

// For development: Use localhost
// For production: Will be same origin (backend serves frontend)
const CONFIG = {
    // Backend API endpoint
    API_URL: window.location.origin,  // Same origin as frontend
    
    // Game settings
    PREVIEW_DURATION_MS: 5000,  // 5 seconds of song
    AUTO_NEXT_DELAY_MS: 15000,  // 15 seconds between songs (optional auto-mode)
    
    // Audio settings
    BACKGROUND_MUSIC_VOLUME: 0.15,  // Background music volume (0-1, 15% = subtle)
    TTS_VOLUME: 1.0,  // TTS announcement volume (0-1, 100% = full)
    BACKGROUND_MUSIC_URL: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'  // Upbeat background music
};

// For local development, override if needed
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // If frontend is on different port, update this
    CONFIG.API_URL = 'http://localhost:5001';
}

// ============================================================================
// GLOBAL STATE
// ============================================================================

let gameState = {
    pool: [],               // All available songs
    remaining: [],          // Songs not yet called
    called: [],             // Songs already called (in order)
    currentTrack: null,     // Currently playing track
    isPlaying: false,       // Is audio currently playing
    announcementsData: null // Loaded announcements
};

// Howler instances
let musicPlayer = null;
let ttsPlayer = null;
let backgroundMusic = null;  // Background music player

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Load song pool and announcements on page load
 */
window.addEventListener('DOMContentLoaded', async () => {
    console.log('🎮 Initializing Music Bingo...');
    
    try {
        // Load song pool
        await loadSongPool();
        
        // Load announcements
        await loadAnnouncements();
        
        // Start background music
        startBackgroundMusic();
        
        // Update UI
        updateStats();
        updateStatus('✅ Ready to start! Press "NEXT SONG"', false);
        
        console.log('✓ Initialization complete');
    } catch (error) {
        console.error('✗ Initialization failed:', error);
        updateStatus(`❌ Error: ${error.message}`, false);
    }
});

/**
 * Load song pool from backend API
 */
async function loadSongPool() {
    const response = await fetch(`${CONFIG.API_URL}/api/pool`);
    if (!response.ok) {
        throw new Error(`Failed to load pool.json. Did you run generate_pool.py?`);
    }
    
    const data = await response.json();
    gameState.pool = data.songs;
    gameState.remaining = [...data.songs]; // Copy for shuffling
    
    // Shuffle remaining songs
    shuffleArray(gameState.remaining);
    
    console.log(`✓ Loaded ${gameState.pool.length} songs`);
}

/**
 * Load custom announcements from backend API
 */
async function loadAnnouncements() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/announcements`);
        if (response.ok) {
            gameState.announcementsData = await response.json();
            console.log(`✓ Loaded announcements for: ${gameState.announcementsData.venue_name}`);
        } else {
            console.log('ℹ No announcements found, using defaults');
            gameState.announcementsData = {
                venue_name: "this venue",
                custom_announcements: [
                    "Welcome to Music Bingo!",
                    "Don't forget to mark your cards!",
                    "Next round starting soon!"
                ]
            };
        }
    } catch (error) {
        console.warn('Could not load announcements:', error);
    }
}

/**
 * Utility: Shuffle array in place (Fisher-Yates)
 */
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

/**
 * Start background music loop
 */
function startBackgroundMusic() {
    if (backgroundMusic) {
        backgroundMusic.stop();
    }
    
    backgroundMusic = new Howl({
        src: [CONFIG.BACKGROUND_MUSIC_URL],
        html5: true,
        loop: true,
        volume: CONFIG.BACKGROUND_MUSIC_VOLUME,
        onload: () => {
            console.log('🎵 Background music loaded');
        },
        onloaderror: (id, error) => {
            console.warn('⚠️ Could not load background music:', error);
        }
    });
    
    // Start playing
    backgroundMusic.play();
    console.log('✓ Background music started (volume: ' + Math.round(CONFIG.BACKGROUND_MUSIC_VOLUME * 100) + '%)');
}

// ============================================================================
// CORE GAME LOGIC
// ============================================================================

/**
 * Play next track in sequence
 */
async function playNextTrack() {
    // Check if game is over
    if (gameState.remaining.length === 0) {
        updateStatus('🎉 All songs called! Game complete!', false);
        alert('All songs have been called!\n\nWould you like to reset the game?');
        return;
    }
    
    // Check if already playing
    if (gameState.isPlaying) {
        console.log('⚠ Already playing, ignoring button press');
        return;
    }
    
    // Get next track
    const track = gameState.remaining.shift();
    gameState.called.push(track);
    gameState.currentTrack = track;
    
    // Update UI immediately
    updateCurrentTrackDisplay(track);
    updateCalledList();
    updateStats();
    
    // Disable button while playing
    setButtonState('nextTrack', false);
    gameState.isPlaying = true;
    
    try {
        // Step 1: Play TTS announcement
        updateStatus('🎙️ Announcing...', true);
        await announceTrack(track);
        
        // Step 2: Play song preview
        updateStatus('🎵 Playing song preview...', true);
        await playSongPreview(track);
        
        // Done
        updateStatus(`✅ Ready for next song (${gameState.remaining.length} remaining)`, false);
        
    } catch (error) {
        console.error('Error playing track:', error);
        updateStatus(`❌ Error: ${error.message}`, false);
    } finally {
        // Re-enable button
        setButtonState('nextTrack', true);
        gameState.isPlaying = false;
    }
}

/**
 * Announce track using ElevenLabs TTS
 */
async function announceTrack(track) {
    const text = `Mark ${track.title} by ${track.artist}`;
    console.log(`🎙️ Announcing: "${text}"`);
    
    return new Promise(async (resolve, reject) => {
        try {
            // Duck background music (lower volume during announcement)
            if (backgroundMusic) {
                backgroundMusic.fade(CONFIG.BACKGROUND_MUSIC_VOLUME, CONFIG.BACKGROUND_MUSIC_VOLUME * 0.3, 500);
            }
            
            // Generate TTS audio using ElevenLabs
            const audioUrl = await generateElevenLabsTTS(text);
            
            // Play using Howler
            ttsPlayer = new Howl({
                src: [audioUrl],
                format: ['mp3'],
                html5: true,  // Required for blob URLs
                volume: CONFIG.TTS_VOLUME,
                onend: () => {
                    console.log('✓ Announcement complete');
                    // Restore background music volume
                    if (backgroundMusic) {
                        backgroundMusic.fade(CONFIG.BACKGROUND_MUSIC_VOLUME * 0.3, CONFIG.BACKGROUND_MUSIC_VOLUME, 500);
                    }
                    resolve();
                },
                onloaderror: (id, error) => {
                    console.error('TTS load error:', error);
                    reject(new Error('Failed to load TTS audio'));
                },
                onplayerror: (id, error) => {
                    console.error('TTS play error:', error);
                    reject(new Error('Failed to play TTS audio'));
                }
            });
            
            ttsPlayer.play();
            
        } catch (error) {
            console.error('TTS generation error:', error);
            reject(error);
        }
    });
}

/**
 * Generate TTS audio using backend proxy endpoint
 * This keeps the API key secure on the server
 * 
 * @param {string} text - Text to convert to speech
 * @returns {Promise<string>} Blob URL of audio
 */
async function generateElevenLabsTTS(text) {
    const response = await fetch(`${CONFIG.API_URL}/api/tts`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `TTS API error: ${response.status}`);
    }
    
    const audioBlob = await response.blob();
    const blobUrl = URL.createObjectURL(audioBlob);
    
    return blobUrl;
}

/**
 * Play 5-second preview of song
 */
async function playSongPreview(track) {
    return new Promise((resolve, reject) => {
        // Create Howler instance for this preview
        musicPlayer = new Howl({
            src: [track.preview_url],
            format: ['mp3'],
            html5: false,
            onload: () => {
                console.log('✓ Preview loaded');
            },
            onplay: () => {
                console.log('▶ Preview playing');
                
                // Stop after 5 seconds
                setTimeout(() => {
                    if (musicPlayer) {
                        musicPlayer.stop();
                        console.log('⏹ Preview stopped (5 seconds)');
                        resolve();
                    }
                }, CONFIG.PREVIEW_DURATION_MS);
            },
            onend: () => {
                console.log('✓ Preview ended naturally');
                resolve();
            },
            onloaderror: (id, error) => {
                console.error('Preview load error:', error);
                reject(new Error('Failed to load song preview'));
            },
            onplayerror: (id, error) => {
                console.error('Preview play error:', error);
                
                // Attempt to unlock audio (browser autoplay policy)
                musicPlayer.once('unlock', () => {
                    musicPlayer.play();
                });
                
                reject(new Error('Failed to play song preview'));
            }
        });
        
        // Start playback
        musicPlayer.play();
    });
}

/**
 * Play custom announcement from announcements.json
 */
async function playCustomAnnouncement() {
    if (!gameState.announcementsData || gameState.announcementsData.custom_announcements.length === 0) {
        alert('No custom announcements configured.');
        return;
    }
    
    // Show selection dialog
    const announcements = gameState.announcementsData.custom_announcements;
    let message = 'Select announcement:\n\n';
    announcements.forEach((ann, i) => {
        message += `${i + 1}. ${ann}\n`;
    });
    
    const choice = prompt(message + '\nEnter number (1-' + announcements.length + ') or custom text:');
    
    if (!choice) return;
    
    // Determine text to announce
    let text;
    const choiceNum = parseInt(choice);
    if (!isNaN(choiceNum) && choiceNum >= 1 && choiceNum <= announcements.length) {
        text = announcements[choiceNum - 1];
    } else {
        text = choice;
    }
    
    // Play announcement
    updateStatus('📢 Playing announcement...', true);
    setButtonState('playAnnouncement', false);
    
    try {
        const audioUrl = await generateElevenLabsTTS(text);
        
        await new Promise((resolve, reject) => {
            const announcementPlayer = new Howl({
                src: [audioUrl],
                format: ['mp3'],
                html5: true,
                onend: resolve,
                onerror: reject
            });
            
            announcementPlayer.play();
        });
        
        updateStatus('✅ Announcement complete', false);
    } catch (error) {
        console.error('Announcement error:', error);
        updateStatus(`❌ Error: ${error.message}`, false);
    } finally {
        setButtonState('playAnnouncement', true);
    }
}

/**
 * Reset game to start over
 */
function resetGame() {
    if (!confirm('Reset game? This will clear all called songs.')) {
        return;
    }
    
    // Stop any playing audio
    if (musicPlayer) {
        musicPlayer.stop();
        musicPlayer = null;
    }
    if (ttsPlayer) {
        ttsPlayer.stop();
        ttsPlayer = null;
    }
    
    // Reset state
    gameState.remaining = [...gameState.pool];
    shuffleArray(gameState.remaining);
    gameState.called = [];
    gameState.currentTrack = null;
    gameState.isPlaying = false;
    
    // Reset UI
    document.getElementById('currentTrack').style.display = 'none';
    document.getElementById('calledList').innerHTML = `
        <p style="opacity: 0.6; text-align: center; grid-column: 1/-1;">
            No songs called yet. Press "NEXT SONG" to begin!
        </p>
    `;
    
    updateStats();
    updateStatus('✅ Game reset! Ready to start.', false);
    
    console.log('🔄 Game reset');
}

// ============================================================================
// UI UPDATE FUNCTIONS
// ============================================================================

/**
 * Update status message
 */
function updateStatus(message, isPlaying) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    
    if (isPlaying) {
        statusEl.classList.add('playing');
    } else {
        statusEl.classList.remove('playing');
    }
}

/**
 * Update current track display
 */
function updateCurrentTrackDisplay(track) {
    const container = document.getElementById('currentTrack');
    const artwork = document.getElementById('trackArtwork');
    const title = document.getElementById('trackTitle');
    const artist = document.getElementById('trackArtist');
    
    container.style.display = 'flex';
    artwork.src = track.artwork_url || '';
    artwork.alt = `${track.title} artwork`;
    title.textContent = track.title;
    artist.textContent = track.artist;
}

/**
 * Update called songs list
 */
function updateCalledList() {
    const listEl = document.getElementById('calledList');
    
    if (gameState.called.length === 0) {
        listEl.innerHTML = `
            <p style="opacity: 0.6; text-align: center; grid-column: 1/-1;">
                No songs called yet.
            </p>
        `;
        return;
    }
    
    // Show most recent songs first
    const html = gameState.called
        .slice()
        .reverse()
        .map((track, index) => {
            const number = gameState.called.length - index;
            return `
                <div class="track-item">
                    <span class="number">#${number}</span>
                    <strong>${track.title}</strong>
                    <br>
                    <small>${track.artist}</small>
                </div>
            `;
        })
        .join('');
    
    listEl.innerHTML = html;
}

/**
 * Update statistics
 */
function updateStats() {
    document.getElementById('calledCount').textContent = gameState.called.length;
    document.getElementById('remainingCount').textContent = gameState.remaining.length;
}

/**
 * Enable/disable button
 */
function setButtonState(buttonId, enabled) {
    const button = document.getElementById(buttonId);
    button.disabled = !enabled;
}

// ============================================================================
// KEYBOARD SHORTCUTS (for convenience)
// ============================================================================

document.addEventListener('keydown', (e) => {
    // Space or Enter = Next track
    if (e.code === 'Space' || e.code === 'Enter') {
        e.preventDefault();
        if (!gameState.isPlaying) {
            playNextTrack();
        }
    }
    
    // A = Announcement
    if (e.code === 'KeyA' && !gameState.isPlaying) {
        playCustomAnnouncement();
    }
    
    // R = Reset
    if (e.code === 'KeyR' && e.ctrlKey) {
        e.preventDefault();
        resetGame();
    }
    
    // M = Toggle background music
    if (e.code === 'KeyM') {
        toggleBackgroundMusic();
    }
});

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Toggle background music on/off
 */
function toggleBackgroundMusic() {
    if (!backgroundMusic) {
        startBackgroundMusic();
        document.getElementById('toggleMusic').textContent = '🎶 Music';
        console.log('🎵 Background music started');
        return;
    }
    
    if (backgroundMusic.playing()) {
        backgroundMusic.pause();
        document.getElementById('toggleMusic').textContent = '🔇 Music';
        console.log('⏸️ Background music paused');
    } else {
        backgroundMusic.play();
        document.getElementById('toggleMusic').textContent = '🎶 Music';
        console.log('▶️ Background music resumed');
    }
}

/**
 * Format duration in ms to MM:SS
 */
function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

/**
 * Handle audio unlock for mobile browsers
 * (iOS Safari requires user interaction before playing audio)
 */
function unlockAudio() {
    const tempSound = new Howl({
        src: ['data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA'],
        onend: () => {
            console.log('✓ Audio unlocked');
        }
    });
    tempSound.play();
}

// Attempt to unlock audio on first user interaction
document.addEventListener('click', unlockAudio, { once: true });

console.log('✓ Music Bingo game script loaded');
console.log('💡 Keyboard shortcuts: Space/Enter = Next Track, A = Announcement, Ctrl+R = Reset');
