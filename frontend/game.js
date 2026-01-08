/*
 * game.js - Music Bingo Game Logic
 * 
 * Features:
 * - iTunes preview playback (8 seconds default)
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
    PREVIEW_DURATION_MS: 8000,  // 8 seconds of song preview
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
    announcementsData: null, // Loaded announcements
    announcementsAI: null,   // AI-generated announcements (optional)
    venueName: localStorage.getItem('venueName') || 'this venue', // Venue name from localStorage
    welcomeAnnounced: false, // Track if welcome was announced
    halfwayAnnounced: false  // Track if halfway announcement was made
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
        // Load venue name from localStorage
        loadVenueNameFromStorage();
        
        // Load song pool
        await loadSongPool();
        
        // Load announcements
        await loadAnnouncements();
        
        // Load AI announcements (optional)
        await loadAIAnnouncements();
        
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
 * Load venue name from localStorage and update UI
 */
function loadVenueNameFromStorage() {
    const savedName = localStorage.getItem('venueName');
    if (savedName) {
        gameState.venueName = savedName;
        document.getElementById('venueName').value = savedName;
        console.log(`✓ Loaded venue: ${savedName}`);
    }
}

/**
 * Save venue name to localStorage
 */
async function saveVenueName() {
    const input = document.getElementById('venueName');
    const venueName = input.value.trim();
    
    if (!venueName) {
        alert('Please enter a venue name');
        return;
    }
    
    gameState.venueName = venueName;
    localStorage.setItem('venueName', venueName);
    
    // Reset welcome announcement flag so it uses new name
    gameState.welcomeAnnounced = false;
    
    // Reload announcements with new venue name
    await loadAnnouncements();
    
    // Show confirmation
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = '✅ Saved!';
    button.style.background = 'linear-gradient(135deg, #38ef7d 0%, #11998e 100%)';
    
    setTimeout(() => {
        button.textContent = originalText;
        button.style.background = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)';
    }, 2000);
    
    console.log(`✓ Venue name saved: ${venueName}`);
}

/**
 * Load venue configuration from backend (deprecated - now using localStorage)
 */
async function loadVenueConfig() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/config`);
        if (response.ok) {
            const config = await response.json();
            // Only use backend config if localStorage is empty
            if (!localStorage.getItem('venueName')) {
                gameState.venueName = config.venue_name;
                document.getElementById('venueName').value = config.venue_name;
            }
            console.log(`✓ Backend venue config available`);
        }
    } catch (error) {
        console.log('ℹ Backend config not available, using localStorage');
    }
}

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
    
    // Limit songs based on player count
    const numPlayers = parseInt(document.getElementById('numPlayers')?.value) || 25;
    const optimalSongs = calculateOptimalSongs(numPlayers);
    
    // Shuffle all songs first
    const shuffled = [...data.songs];
    shuffleArray(shuffled);
    
    // Take only the optimal number of songs for this game
    gameState.remaining = shuffled.slice(0, optimalSongs);
    
    console.log(`✓ Game will use ${gameState.remaining.length} songs for ${numPlayers} players`);
    
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
            
            // Replace [VENUE_NAME] placeholder with actual venue name
            const venueName = gameState.venueName || 'this venue';
            
            gameState.announcementsData.custom_announcements = 
                gameState.announcementsData.custom_announcements.map(ann => 
                    ann.replace(/\[VENUE_NAME\]/g, venueName)
                );
            
            console.log(`✓ Loaded announcements for: ${venueName}`);
        } else {
            console.log('ℹ No announcements found, using defaults');
            gameState.announcementsData = {
                venue_name: gameState.venueName || "this venue",
                custom_announcements: [
                    `Welcome to Music Bingo at ${gameState.venueName || 'this venue'}!`,
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
 * Load AI-generated announcements (optional)
 */
async function loadAIAnnouncements() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/announcements-ai`);
        if (response.ok) {
            gameState.announcementsAI = await response.json();
            console.log(`✓ Loaded ${Object.keys(gameState.announcementsAI).length} AI announcements`);
        } else {
            console.log('ℹ No AI announcements found, using fallback system');
        }
    } catch (error) {
        console.log('ℹ AI announcements not available, using fallback');
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
        // Step 1: Play welcome announcement on first song
        if (!gameState.welcomeAnnounced) {
            updateStatus('🎙️ Welcome announcement...', true);
            await announceWelcome();
            gameState.welcomeAnnounced = true;
            // Short pause after welcome
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Step 2: Check for halfway announcement
        const totalSongs = gameState.pool.length;
        const songsPlayed = gameState.called.length;
        const halfwayPoint = Math.floor(totalSongs / 2);
        
        if (!gameState.halfwayAnnounced && songsPlayed === halfwayPoint) {
            updateStatus('🎊 Halfway announcement...', true);
            await announceHalfway();
            gameState.halfwayAnnounced = true;
            // Short pause after halfway
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // Step 3: Play TTS announcement
        updateStatus('🎙️ Announcing...', true);
        await announceTrack(track);
        
        // Step 4: Play song preview
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
 * Generate welcome announcement text
 */
function generateWelcomeText() {
    const welcomeScripts = [
        `Ladies and gentlemen, welcome to Music Bingo at ${gameState.venueName}! Tonight, we're dropping beats instead of balls. Grab your cards, your markers, and get ready to mark off those songs as we play short clips. No titles or artists will be announced—just listen closely, sing along if you know it, and shout 'Bingo!' when you get a line or full house. We've got great prizes up for grabs, so let's kick things off with some classic tunes!`,
        
        `Hello everyone and welcome to the ultimate Music Bingo night at ${gameState.venueName}! Get those dabbers ready because we're about to play hits from across the decades. I'll spin the tracks, you identify them on your card—without any hints on the name or who sings it. First to a full line wins! Are you ready to test your music knowledge? Let's get this party started!`,
        
        `Good evening, music lovers! It's time for Music Bingo extravaganza at ${gameState.venueName}. Rules are simple: We play a snippet, you spot the song on your card and mark it off. No song titles or artists given—just pure ear power. Prizes for the quickest bingos, so stay sharp. Here comes the first track—good luck!`
    ];
    
    return welcomeScripts[Math.floor(Math.random() * welcomeScripts.length)];
}

/**
 * Generate halfway announcement text
 */
function generateHalfwayText() {
    const halfwayScripts = [
        `Alright, everyone—we're halfway through this round! How's everyone doing? A few close calls out there? Keep those ears open because the hits are just getting better. Remember, no peeking at your phones for lyrics! Next track coming up—let's see who gets closer to that bingo!`,
        
        `We're at the halfway mark, folks! Time for a quick breather. Anyone got a line yet? Shout out if you're one away! We've got some absolute bangers left, so don't give up now. Grab a drink, stretch those vocal cords for singing along, and let's dive back in!`,
        
        `Halfway there, music bingo fans! You're all doing amazing—I've heard some epic sing-alongs already. Prizes are waiting for those full cards, so stay focused. If you're stuck on a song, maybe the next one will jog your memory. Here we go with more tunes!`
    ];
    
    return halfwayScripts[Math.floor(Math.random() * halfwayScripts.length)];
}

/**
 * Announce welcome message using ElevenLabs TTS
 */
async function announceWelcome() {
    const text = generateWelcomeText();
    console.log(`🎙️ Welcome: "${text.substring(0, 100)}..."`);
    
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
                html5: true,
                volume: CONFIG.TTS_VOLUME,
                onend: () => {
                    console.log('✓ Welcome announcement complete');
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
            console.error('Welcome TTS generation error:', error);
            // Don't fail the whole game if welcome fails
            resolve();
        }
    });
}

/**
 * Announce halfway message using ElevenLabs TTS
 */
async function announceHalfway() {
    const text = generateHalfwayText();
    console.log(`🎊 Halfway: "${text.substring(0, 100)}..."`);
    
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
                format: ["mp3"],
                html5: true,
                volume: CONFIG.TTS_VOLUME,
                onend: () => {
                    console.log("✓ Halfway announcement complete");
                    // Restore background music volume
                    if (backgroundMusic) {
                        backgroundMusic.fade(CONFIG.BACKGROUND_MUSIC_VOLUME * 0.3, CONFIG.BACKGROUND_MUSIC_VOLUME, 500);
                    }
                    resolve();
                },
                onloaderror: (id, error) => {
                    console.error("TTS load error:", error);
                    reject(new Error("Failed to load TTS audio"));
                },
                onplayerror: (id, error) => {
                    console.error("TTS play error:", error);
                    reject(new Error("Failed to play TTS audio"));
                }
            });
            
            ttsPlayer.play();
            
        } catch (error) {
            console.error("Halfway TTS generation error:", error);
            // Don"t fail the whole game if halfway announcement fails
            resolve();
        }
    });
}

/**
 * Generate announcement text based on 3 rotating types
 * Prioritizes AI-generated announcements if available, falls back to template system
 */
function generateAnnouncementText(track) {
    // Try AI announcements first
    if (gameState.announcementsAI && gameState.announcementsAI[track.id]) {
        const aiAnnouncements = gameState.announcementsAI[track.id];
        
        // Randomly choose one of the 3 AI-generated types
        const types = ['decade', 'trivia', 'simple'];
        const randomType = types[Math.floor(Math.random() * types.length)];
        
        return aiAnnouncements[randomType];
    }
    
    // Fallback to template system if AI not available
    const randomType = Math.random();
    
    // Type A: Era/Decade Context (33%)
    if (randomType < 0.33) {
        const year = parseInt(track.release_year);
        let decade = '';
        let description = '';
        
        if (year >= 2020) {
            decade = '2020s';
            description = 'Get ready for this fresh hit from the 2020s';
        } else if (year >= 2010) {
            decade = '2010s';
            description = 'Get ready for this modern classic from the 2010s';
        } else if (year >= 2000) {
            decade = '2000s';
            description = 'Here\'s a chart-topper from the early 2000s';
        } else if (year >= 1990) {
            decade = '1990s';
            description = 'Listen up for this gem from the grunge and pop explosion of the 1990s';
        } else if (year >= 1980) {
            decade = '1980s';
            const options = [
                'Let\'s go straight to the 1980s for this one',
                'Here\'s an iconic banger from the hair metal 1980s',
                'Coming up: A massive hit from the 1980s'
            ];
            description = options[Math.floor(Math.random() * options.length)];
        } else if (year >= 1970) {
            decade = '1970s';
            description = 'Next track: Straight out of the disco-fueled 1970s';
        } else if (year >= 1960) {
            decade = '1960s';
            description = 'Coming up: A massive hit from the swinging 1960s';
        } else {
            description = 'Here\'s a classic for you';
        }
        
        return description;
    }
    
    // Type B: Fun Facts/Trivia (33%)
    else if (randomType < 0.66) {
        const funFacts = [
            'This one topped the charts for weeks',
            'This artist has won multiple awards',
            'This track became an instant classic',
            'This song was a massive hit worldwide',
            'You\'ll definitely recognize this one',
            'This artist is a true legend',
            'This track dominated the airwaves',
            'This one\'s a crowd favorite',
            'This song defined a generation',
            'This artist needs no introduction'
        ];
        return funFacts[Math.floor(Math.random() * funFacts.length)];
    }
    
    // Type C: Generic Simple (33%)
    else {
        const simpleAnnouncements = [
            'Next song',
            'Here we go',
            'Coming up',
            'Let\'s keep it going',
            'Another one coming your way',
            'Ready for this one',
            'Listen closely',
            'Mark your cards',
            'Here\'s another',
            'Let\'s continue'
        ];
        return simpleAnnouncements[Math.floor(Math.random() * simpleAnnouncements.length)];
    }
}

/**
 * Announce track using ElevenLabs TTS
 */
async function announceTrack(track) {
    // Generate varied announcement - NO track name or artist (per Philip's feedback)
    const text = generateAnnouncementText(track);
    console.log(`🎙️ Announcing: "${text}" (Track: ${track.title} by ${track.artist} [${track.release_year}])`);
    
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
    gameState.welcomeAnnounced = false;
    gameState.halfwayAnnounced = false;
    
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

// Calculate optimal songs based on number of players
function calculateOptimalSongs(numPlayers, targetDurationMinutes = 45) {
    const SONGS_PER_CARD = 24;
    
    let baseSongs;
    if (numPlayers <= 10) {
        baseSongs = Math.floor(SONGS_PER_CARD * 2.5); // ~60 songs
    } else if (numPlayers <= 25) {
        baseSongs = Math.floor(SONGS_PER_CARD * 2.0); // ~48 songs
    } else if (numPlayers <= 40) {
        baseSongs = Math.floor(SONGS_PER_CARD * 1.5); // ~36 songs
    } else {
        baseSongs = Math.floor(SONGS_PER_CARD * 1.3); // ~31 songs
    }
    
    // Adjust based on duration (30 seconds per song average)
    const songsPerMinute = 2;
    const maxSongsForDuration = targetDurationMinutes * songsPerMinute;
    
    let optimalSongs = Math.min(baseSongs, maxSongsForDuration);
    optimalSongs = Math.max(optimalSongs, 20); // Minimum 20 songs
    
    return optimalSongs;
}

// Estimate game duration
function estimateGameDuration(numSongs, secondsPerSong = 30) {
    return Math.floor((numSongs * secondsPerSong) / 60);
}

// Update estimation display when player count changes
function updateSongEstimation() {
    const numPlayers = parseInt(document.getElementById('numPlayers').value) || 25;
    const optimalSongs = calculateOptimalSongs(numPlayers);
    const estimatedMinutes = estimateGameDuration(optimalSongs);
    
    document.getElementById('estimatedSongs').textContent = 
        `~${optimalSongs} songs, ${estimatedMinutes} min`;
}

// Add event listener for player count changes
document.addEventListener('DOMContentLoaded', function() {
    const numPlayersInput = document.getElementById('numPlayers');
    if (numPlayersInput) {
        numPlayersInput.addEventListener('input', async function() {
            updateSongEstimation();
            
            // Reload song pool with new player count (only if game hasn't started)
            if (gameState.called.length === 0 && gameState.pool.length > 0) {
                const numPlayers = parseInt(numPlayersInput.value) || 25;
                const optimalSongs = calculateOptimalSongs(numPlayers);
                
                // Re-shuffle and limit songs
                const shuffled = [...gameState.pool];
                shuffleArray(shuffled);
                gameState.remaining = shuffled.slice(0, optimalSongs);
                
                updateStats();
                console.log(`✓ Updated to ${optimalSongs} songs for ${numPlayers} players`);
            }
        });
        updateSongEstimation(); // Initial calculation
    }
});

// Generate Cards function
async function generateCards() {
    const venueName = document.getElementById('venueName').value.trim();
    const numPlayers = parseInt(document.getElementById('numPlayers').value) || 25;
    
    if (!venueName) {
        alert('Please enter a venue name first!');
        return;
    }
    
    // Calculate optimal songs
    const optimalSongs = calculateOptimalSongs(numPlayers);
    const estimatedMinutes = estimateGameDuration(optimalSongs);
    
    // Show loading state
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '⏳ Generating...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/generate-cards`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                venue_name: venueName,
                num_players: numPlayers,
                optimal_songs: optimalSongs
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate cards');
        }
        
        const result = await response.json();
        
        // Show success message with game info
        alert(`✅ Cards generated successfully!\n\nVenue: ${venueName}\nPlayers: ${numPlayers}\nOptimal songs: ${optimalSongs}\nEstimated duration: ${estimatedMinutes} minutes\n\nCards: ${result.num_cards}\nPages: ${result.num_pages}\n\nDownloading now...`);
        
        // Download the PDF
        window.open(`${CONFIG.API_URL}/data/cards/music_bingo_cards.pdf`, '_blank');
        
    } catch (error) {
        console.error('Error generating cards:', error);
        alert('❌ Error generating cards. Please try again.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

