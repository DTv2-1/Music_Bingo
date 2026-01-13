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
// CONFIGURATION - Now loaded from config.js
// ============================================================================
// CONFIG is defined in config.js which is loaded before this file

// Extend CONFIG with additional game settings if needed
if (!CONFIG.PREVIEW_DURATION_MS) CONFIG.PREVIEW_DURATION_MS = 15000;
if (!CONFIG.AUTO_NEXT_DELAY_MS) CONFIG.AUTO_NEXT_DELAY_MS = 15000;
if (!CONFIG.BACKGROUND_MUSIC_VOLUME) CONFIG.BACKGROUND_MUSIC_VOLUME = 0.15;
if (!CONFIG.TTS_VOLUME) CONFIG.TTS_VOLUME = 1.0;
if (!CONFIG.BACKGROUND_MUSIC_URL) {
    CONFIG.BACKGROUND_MUSIC_URL = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3';
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
// Global flag to prevent game initialization
let gameInitialized = false;

window.addEventListener('DOMContentLoaded', async () => {
    console.log('🎮 Music Bingo - Waiting for setup...');
    
    // Check if setup was already completed
    const setupCompleted = localStorage.getItem('setupCompleted');
    const savedVenueName = localStorage.getItem('venueName');
    
    if (setupCompleted && savedVenueName) {
        // Skip setup modal if already configured
        console.log('✓ Setup already completed, loading game...');
        document.getElementById('setupModal').classList.add('hidden');
        await initializeGame();
    } else {
        // Show setup modal
        console.log('⚙️ First time setup required');
        initializeSetupModal();
    }
});

/**
 * Initialize the setup modal with event listeners
 */
function initializeSetupModal() {
    const setupVenueName = document.getElementById('setupVenueName');
    const setupNumPlayers = document.getElementById('setupNumPlayers');
    const setupEstimation = document.getElementById('setupEstimation');
    
    // Load saved values if any
    const savedVenue = localStorage.getItem('venueName');
    const savedPlayers = localStorage.getItem('numPlayers');
    const savedVoice = localStorage.getItem('voiceId');
    const savedDecades = localStorage.getItem('selectedDecades');
    const savedPubLogo = localStorage.getItem('pubLogo');
    const savedSocialMedia = localStorage.getItem('socialMedia');
    const savedIncludeQR = localStorage.getItem('includeQR');
    
    if (savedVenue) setupVenueName.value = savedVenue;
    if (savedPlayers) setupNumPlayers.value = savedPlayers;
    if (savedVoice) document.getElementById('setupVoice').value = savedVoice;
    if (savedPubLogo) {
        document.getElementById('setupPubLogo').value = savedPubLogo;
        showLogoPreview(savedPubLogo);
    }
    if (savedSocialMedia) document.getElementById('setupSocialMedia').value = savedSocialMedia;
    if (savedIncludeQR === 'true') {
        document.getElementById('setupIncludeQR').checked = true;
        toggleSocialMediaField(); // Show the field if checkbox was saved as checked
    }
    
    // Restore decade checkbox selections
    if (savedDecades) {
        try {
            const decades = JSON.parse(savedDecades);
            document.querySelectorAll('input[name="decades"]').forEach(checkbox => {
                checkbox.checked = decades.includes(checkbox.value);
            });
        } catch (e) {
            console.warn('Could not restore decade selection:', e);
        }
    }
    
    // Update estimation on player count change
    function updateSetupEstimation() {
        const numPlayers = parseInt(setupNumPlayers.value) || 25;
        const optimalSongs = calculateOptimalSongs(numPlayers);
        const estimatedMinutes = estimateGameDuration(optimalSongs);
        setupEstimation.textContent = `📊 Estimated: ~${optimalSongs} songs, ${estimatedMinutes} minutes`;
    }
    
    setupNumPlayers.addEventListener('input', updateSetupEstimation);
    updateSetupEstimation();
    
    // Setup voice card selection
    setupVoiceCardSelection();
    
    // Allow Enter key to submit
    setupVenueName.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') completeSetup();
    });
    setupNumPlayers.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') completeSetup();
    });
}

/**
 * Setup voice card selection functionality
 */
function setupVoiceCardSelection() {
    const voiceCards = document.querySelectorAll('.voice-card');
    const hiddenInput = document.getElementById('setupVoice');
    
    // Restore saved voice selection
    const savedVoice = localStorage.getItem('voiceId');
    if (savedVoice) {
        voiceCards.forEach(card => {
            if (card.dataset.voiceId === savedVoice) {
                card.classList.add('selected');
                hiddenInput.value = savedVoice;
            } else {
                card.classList.remove('selected');
            }
        });
    }
    
    // Add click handlers
    voiceCards.forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't trigger if clicking the preview button
            if (e.target.classList.contains('preview-btn')) return;
            
            // Deselect all cards
            voiceCards.forEach(c => c.classList.remove('selected'));
            
            // Select clicked card
            card.classList.add('selected');
            
            // Update hidden input
            hiddenInput.value = card.dataset.voiceId;
            
            console.log(`✓ Voice selected: ${card.dataset.voiceName} (${card.dataset.voiceId})`);
        });
    });
}

/**
 * Preview a voice by generating sample TTS
 */
let currentPreviewAudio = null;

async function previewVoice(voiceId, voiceName) {
    const btn = event.target;
    
    // Stop any currently playing preview
    if (currentPreviewAudio) {
        currentPreviewAudio.pause();
        currentPreviewAudio = null;
    }
    
    // Disable button
    btn.disabled = true;
    btn.textContent = '⏳ Loading...';
    
    try {
        // Sample text for preview
        const sampleText = `Hello! I'm ${voiceName}, your Music Bingo DJ. Get ready for an amazing night of music and fun!`;
        
        // Generate TTS
        const response = await fetch(`${CONFIG.API_URL}/api/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                text: sampleText,
                voice_id: voiceId
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate voice preview');
        }
        
        const audioBlob = await response.blob();
        const blobUrl = URL.createObjectURL(audioBlob);
        
        // Play preview
        currentPreviewAudio = new Audio(blobUrl);
        currentPreviewAudio.volume = 0.8;
        
        currentPreviewAudio.onended = () => {
            btn.disabled = false;
            btn.textContent = '🔊 Preview';
            URL.revokeObjectURL(blobUrl);
        };
        
        currentPreviewAudio.onerror = () => {
            btn.disabled = false;
            btn.textContent = '🔊 Preview';
            alert('Failed to play audio preview');
        };
        
        await currentPreviewAudio.play();
        btn.textContent = '▶️ Playing...';
        
        console.log(`✓ Playing voice preview: ${voiceName}`);
        
    } catch (error) {
        console.error('Voice preview error:', error);
        alert(`Failed to preview voice: ${error.message}`);
        btn.disabled = false;
        btn.textContent = '🔊 Preview';
    }
}

/**
 * Complete setup and initialize the game
 */
async function completeSetup() {
    const setupVenueName = document.getElementById('setupVenueName');
    const setupNumPlayers = document.getElementById('setupNumPlayers');
    const startBtn = document.getElementById('startGameBtn');
    
    const venueName = setupVenueName.value.trim();
    const numPlayers = parseInt(setupNumPlayers.value) || 25;
    
    // Validate venue name
    if (!venueName) {
        setupVenueName.style.borderColor = '#e74c3c';
        setupVenueName.focus();
        alert('⚠️ Please enter a venue name');
        return;
    }
    
    // Validate number of players
    if (numPlayers < 5 || numPlayers > 100) {
        setupNumPlayers.style.borderColor = '#e74c3c';
        setupNumPlayers.focus();
        alert('⚠️ Number of players must be between 5 and 100');
        return;
    }
    
    // Disable button and show loading
    startBtn.disabled = true;
    startBtn.textContent = '⏳ Loading...';
    
    try {
        // Get selected voice
        const setupVoice = document.getElementById('setupVoice');
        const selectedVoice = setupVoice.value;
        
        // Get selected decades from checkboxes
        const decadeCheckboxes = document.querySelectorAll('input[name="decades"]:checked');
        const selectedDecades = Array.from(decadeCheckboxes).map(cb => cb.value);
        
        if (selectedDecades.length === 0) {
            alert('⚠️ Please select at least one music era/decade');
            startBtn.disabled = false;
            startBtn.textContent = '🎮 Start Music Bingo';
            return;
        }
        
        // Get marketing/branding fields (optional)
        const pubLogo = document.getElementById('setupPubLogo').value.trim();
        const includeQR = document.getElementById('setupIncludeQR').checked;
        
        // Get complete social media URL (platform + username)
        const socialMediaURL = includeQR ? getSocialMediaURL() : '';
        
        // Save settings
        gameState.venueName = venueName;
        gameState.selectedDecades = selectedDecades;
        localStorage.setItem('venueName', venueName);
        localStorage.setItem('numPlayers', numPlayers.toString());
        localStorage.setItem('voiceId', selectedVoice);
        localStorage.setItem('selectedDecades', JSON.stringify(selectedDecades));
        localStorage.setItem('pubLogo', pubLogo);
        localStorage.setItem('socialMedia', socialMediaURL);
        localStorage.setItem('includeQR', includeQR.toString());
        localStorage.setItem('setupCompleted', 'true');
        
        // Update main UI inputs
        document.getElementById('venueName').value = venueName;
        document.getElementById('numPlayers').value = numPlayers;
        
        // Hide modal
        document.getElementById('setupModal').classList.add('hidden');
        
        // Initialize game
        await initializeGame();
        
        console.log(`✓ Setup complete: ${venueName}, ${numPlayers} players`);
    } catch (error) {
        console.error('✗ Setup failed:', error);
        alert(`❌ Setup failed: ${error.message}`);
        startBtn.disabled = false;
        startBtn.textContent = '🎮 Start Music Bingo';
    }
}

/**
 * Initialize the game (called after setup is complete)
 */
async function initializeGame() {
    if (gameInitialized) {
        console.log('⚠️ Game already initialized');
        return;
    }
    
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
        
        gameInitialized = true;
        console.log('✓ Initialization complete');
    } catch (error) {
        console.error('✗ Initialization failed:', error);
        updateStatus(`❌ Error: ${error.message}`, false);
    }
}

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
 * Reset setup - shows the setup modal again and clears game state
 */
function resetSetup() {
    const confirmReset = confirm('⚠️ This will restart the game and clear all progress. Continue?');
    
    if (!confirmReset) return;
    
    // Clear setup flag
    localStorage.removeItem('setupCompleted');
    
    // Show modal
    const modal = document.getElementById('setupModal');
    if (modal) {
        modal.classList.remove('hidden');
        initializeSetupModal();
    }
    
    // Optionally reload page for clean slate
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

/**
 * Save venue name to localStorage
 */
async function saveVenueName(event) {
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
    
    // Update announcements list
    updateAnnouncementsList();
    
    // Show confirmation
    if (event && event.target) {
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✅ Saved!';
        button.style.background = 'linear-gradient(135deg, #38ef7d 0%, #11998e 100%)';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)';
        }, 2000);
    }
    
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
    
    // Get selected decades from localStorage or gameState
    let selectedDecades = gameState.selectedDecades;
    if (!selectedDecades) {
        const savedDecades = localStorage.getItem('selectedDecades');
        selectedDecades = savedDecades ? JSON.parse(savedDecades) : ['1960s', '1970s', '1980s', '1990s'];
        gameState.selectedDecades = selectedDecades;
    }
    
    // Filter songs by selected decades
    const filteredSongs = data.songs.filter(song => {
        const year = parseInt(song.release_year);
        return selectedDecades.some(decade => {
            const startYear = parseInt(decade.substring(0, 4));
            const endYear = startYear + 9;
            return year >= startYear && year <= endYear;
        });
    });
    
    console.log(`✓ Filtered ${filteredSongs.length}/${data.songs.length} songs for decades: ${selectedDecades.join(', ')}`);
    
    if (filteredSongs.length === 0) {
        console.warn('⚠️ No songs found for selected decades, using all songs');
        gameState.pool = data.songs;
    } else {
        gameState.pool = filteredSongs;
    }
    
    // Limit songs based on player count
    const numPlayers = parseInt(document.getElementById('numPlayers')?.value) || 25;
    const optimalSongs = calculateOptimalSongs(numPlayers);
    
    // Shuffle all songs first
    const shuffled = [...gameState.pool];
    shuffleArray(shuffled);
    
    // Take only the optimal number of songs for this game
    gameState.remaining = shuffled.slice(0, optimalSongs);
    
    // Try to restore saved game state ONLY if songs were already called
    const savedState = localStorage.getItem('gameState');
    if (savedState) {
        try {
            const state = JSON.parse(savedState);
            // Only restore if there were songs already played (not a fresh start)
            if (state.called && state.called.length > 0) {
                restoreGameState();
            } else {
                console.log('ℹ️ No songs called yet, starting fresh game');
                localStorage.removeItem('gameState');
            }
        } catch (e) {
            console.warn('Could not parse saved state:', e);
            localStorage.removeItem('gameState');
        }
    }
    
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
        
        // Update the announcements list display
        updateAnnouncementsList();
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
// GAME STATE PERSISTENCE
// ============================================================================

/**
 * Save current game state to localStorage
 */
function saveGameState() {
    try {
        const stateToSave = {
            remaining: gameState.remaining,
            called: gameState.called,
            currentTrack: gameState.currentTrack,
            welcomeAnnounced: gameState.welcomeAnnounced,
            halfwayAnnounced: gameState.halfwayAnnounced,
            timestamp: Date.now()
        };
        localStorage.setItem('gameState', JSON.stringify(stateToSave));
        console.log('💾 Game state saved');
    } catch (e) {
        console.warn('Could not save game state:', e);
    }
}

/**
 * Restore game state from localStorage if available
 */
function restoreGameState() {
    try {
        const savedState = localStorage.getItem('gameState');
        if (!savedState) return;
        
        const state = JSON.parse(savedState);
        
        // Check if saved state is from the same session (within last 24 hours)
        const hoursSinceLastSave = (Date.now() - state.timestamp) / (1000 * 60 * 60);
        if (hoursSinceLastSave > 24) {
            console.log('ℹ️ Saved game state is too old, starting fresh');
            localStorage.removeItem('gameState');
            return;
        }
        
        // Restore the game state, but validate songs exist in current pool
        if (state.remaining && state.remaining.length > 0) {
            // Create a Set of valid IDs from current pool
            const validIds = new Set(gameState.pool.map(song => song.id));
            
            // Filter out songs that no longer exist in the pool
            const validRemaining = state.remaining.filter(song => validIds.has(song.id));
            const validCalled = (state.called || []).filter(song => validIds.has(song.id));
            
            // Only restore if we still have valid songs
            if (validRemaining.length > 0) {
                gameState.remaining = validRemaining;
                gameState.called = validCalled;
                gameState.currentTrack = state.currentTrack && validIds.has(state.currentTrack.id) ? state.currentTrack : null;
                gameState.welcomeAnnounced = state.welcomeAnnounced || false;
                gameState.halfwayAnnounced = state.halfwayAnnounced || false;
                
                const invalidCount = (state.remaining.length - validRemaining.length) + ((state.called?.length || 0) - validCalled.length);
                if (invalidCount > 0) {
                    console.log(`ℹ️ Filtered out ${invalidCount} songs no longer in pool`);
                }
                console.log(`✓ Restored game state: ${gameState.called.length} songs called, ${gameState.remaining.length} remaining`);
                
                // Update UI to reflect restored state
                if (gameState.currentTrack) {
                    updateCurrentTrackDisplay(gameState.currentTrack);
                }
                if (gameState.called.length > 0) {
                    updateCalledList();
                }
                updateStats();
            } else {
                console.log('ℹ️ No valid songs in saved state, starting fresh');
                localStorage.removeItem('gameState');
            }
        }
    } catch (e) {
        console.warn('Could not restore game state:', e);
        localStorage.removeItem('gameState');
    }
}

/**
 * Clear saved game state (for reset)
 */
function clearGameState() {
    localStorage.removeItem('gameState');
    console.log('🗑️ Game state cleared');
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
    
    // Save game state to localStorage
    saveGameState();
    
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
        
        console.log(`✓ Using AI announcement (${randomType}) for track ${track.id}`);
        return aiAnnouncements[randomType];
    }
    
    // Debug: Log why AI announcement wasn't found
    console.warn(`⚠️ No AI announcement for track ${track.id} (type: ${typeof track.id})`);
    if (gameState.announcementsAI) {
        const keys = Object.keys(gameState.announcementsAI);
        console.log(`Available AI keys sample:`, keys.slice(0, 5));
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
    // Get selected voice from localStorage (British voice)
    const voiceId = localStorage.getItem('voiceId') || 'JBFqnCBsd6RMkjVDRZzb'; // Default: George (Male British)
    
    const response = await fetch(`${CONFIG.API_URL}/api/tts`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            text,
            voice_id: voiceId
        })
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
 * Play song preview with fade in/out and background music control
 * Philip's feedback #7, #9: Silence background completely, add fades
 */
async function playSongPreview(track) {
    return new Promise((resolve, reject) => {
        // PHILIP'S FEEDBACK #7: Silence background music completely during track
        if (backgroundMusic) {
            backgroundMusic.fade(backgroundMusic.volume(), 0, 1000);  // Fade to 0 over 1 second
            console.log('🔇 Background music silenced for track preview');
        }
        
        // Create Howler instance for this preview
        musicPlayer = new Howl({
            src: [track.preview_url],
            format: ['mp3'],
            html5: false,
            volume: 0,  // Start at 0 for fade in (Philip's feedback #9)
            onload: () => {
                console.log('✓ Preview loaded');
            },
            onplay: () => {
                console.log('▶ Preview playing with fade in/out');
                
                // PHILIP'S FEEDBACK #9: Fade in at start
                musicPlayer.fade(0, 0.9, 1500);  // Fade from 0 to 90% over 1.5 seconds
                
                // Calculate when to start fade out (3 seconds before end)
                const fadeOutTime = CONFIG.PREVIEW_DURATION_MS - 3000;
                
                // Start fade out before stopping
                setTimeout(() => {
                    if (musicPlayer) {
                        // PHILIP'S FEEDBACK #9: Fade out at end
                        musicPlayer.fade(0.9, 0, 3000);  // Fade from 90% to 0 over 3 seconds
                    }
                }, fadeOutTime);
                
                // Stop after full duration
                setTimeout(() => {
                    if (musicPlayer) {
                        musicPlayer.stop();
                        console.log(`⏹ Preview stopped (${CONFIG.PREVIEW_DURATION_MS/1000} seconds)`);
                        
                        // Restore background music
                        if (backgroundMusic) {
                            backgroundMusic.fade(0, CONFIG.BACKGROUND_MUSIC_VOLUME, 1500);
                            console.log('🔊 Background music restored');
                        }
                        
                        resolve();
                    }
                }, CONFIG.PREVIEW_DURATION_MS);
            },
            onend: () => {
                console.log('✓ Preview ended naturally');
                
                // Restore background music
                if (backgroundMusic) {
                    backgroundMusic.fade(0, CONFIG.BACKGROUND_MUSIC_VOLUME, 1500);
                    console.log('🔊 Background music restored');
                }
                
                resolve();
            },
            onloaderror: (id, error) => {
                console.error('Preview load error:', error);
                
                // Restore background music on error
                if (backgroundMusic) {
                    backgroundMusic.fade(0, CONFIG.BACKGROUND_MUSIC_VOLUME, 1000);
                }
                
                reject(new Error('Failed to load song preview'));
            },
            onplayerror: (id, error) => {
                console.error('Preview play error:', error);
                
                // Restore background music on error
                if (backgroundMusic) {
                    backgroundMusic.fade(0, CONFIG.BACKGROUND_MUSIC_VOLUME, 1000);
                }
                
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
 * Now redirects to Quick Announcements list below
 */
async function playCustomAnnouncement() {
    if (!gameState.announcementsData || gameState.announcementsData.custom_announcements.length === 0) {
        console.log('ℹ️ No custom announcements configured.');
        return;
    }
    
    // Scroll to announcements list
    const announcementsList = document.getElementById('announcementsList');
    if (announcementsList) {
        announcementsList.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Highlight the section briefly
        announcementsList.style.boxShadow = '0 0 20px rgba(102,126,234,0.6)';
        setTimeout(() => {
            announcementsList.style.boxShadow = 'none';
        }, 2000);
        
        updateStatus('👇 Use the Quick Announcements buttons below', false);
    }
}

/**
 * Reset setup and show configuration modal
 */
function resetSetup() {
    if (!confirm('Reconfigure setup? This will clear all game progress and show the setup modal again.')) {
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
    if (backgroundMusic) {
        backgroundMusic.stop();
        backgroundMusic = null;
    }
    
    // Clear all saved data
    localStorage.removeItem('setupCompleted');
    localStorage.removeItem('venueName');
    localStorage.removeItem('numPlayers');
    localStorage.removeItem('voiceId');
    localStorage.removeItem('selectedDecades');
    localStorage.removeItem('pubLogo');
    localStorage.removeItem('socialMedia');
    localStorage.removeItem('includeQR');
    clearGameState();
    
    // Reset game state
    gameState.remaining = [];
    gameState.called = [];
    gameState.currentTrack = null;
    gameState.isPlaying = false;
    gameState.welcomeAnnounced = false;
    gameState.halfwayAnnounced = false;
    gameInitialized = false;
    
    // Show setup modal and reload page
    console.log('🔄 Resetting setup...');
    location.reload();
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
    
    // Clear saved game state
    clearGameState();
    
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
    const totalSongs = gameState.called.length + gameState.remaining.length;
    const estimatedMinutes = estimateGameDuration(totalSongs);
    
    // Update the stats counters
    document.getElementById('calledCount').textContent = gameState.called.length;
    document.getElementById('remainingCount').textContent = gameState.remaining.length;
    
    // Update the top estimation text to show actual game total
    const estimatedSongsEl = document.getElementById('estimatedSongs');
    if (estimatedSongsEl) {
        estimatedSongsEl.textContent = `~${totalSongs} songs, ${estimatedMinutes} min`;
    }
}

/**
 * Update announcements list display
 */
function updateAnnouncementsList() {
    const container = document.getElementById('announcementsList');
    if (!container) return;
    
    if (!gameState.announcementsData || !gameState.announcementsData.custom_announcements) {
        container.innerHTML = '<p style="opacity: 0.6;">No announcements loaded</p>';
        return;
    }
    
    const announcements = gameState.announcementsData.custom_announcements;
    
    let html = '<div style="display: grid; gap: 8px;">';
    announcements.forEach((ann, i) => {
        html += `
            <button 
                onclick="playSpecificAnnouncement(${i})" 
                style="
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    cursor: pointer;
                    text-align: left;
                    font-size: 0.9em;
                    transition: transform 0.2s, box-shadow 0.2s;
                "
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(102,126,234,0.4)'"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none'"
            >
                ${i + 1}. ${ann}
            </button>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

/**
 * Play specific announcement by index
 */
async function playSpecificAnnouncement(index) {
    if (!gameState.announcementsData || !gameState.announcementsData.custom_announcements) {
        alert('No announcements available');
        return;
    }
    
    const text = gameState.announcementsData.custom_announcements[index];
    
    updateStatus('📢 Playing announcement...', true);
    
    try {
        const audioUrl = await generateElevenLabsTTS(text);
        
        await new Promise((resolve, reject) => {
            const announcementPlayer = new Howl({
                src: [audioUrl],
                html5: true,
                volume: CONFIG.TTS_VOLUME,
                onend: resolve,
                onloaderror: reject,
                onplayerror: reject
            });
            
            announcementPlayer.play();
        });
        
        updateStatus('✅ Announcement complete', false);
    } catch (error) {
        console.error('Error playing announcement:', error);
        updateStatus('❌ Announcement failed', false);
    }
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
    // Ignore keyboard shortcuts when user is typing in an input/textarea
    const activeElement = document.activeElement;
    const isTyping = activeElement && (
        activeElement.tagName === 'INPUT' || 
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
    );
    
    if (isTyping) {
        return; // Don't intercept keys when typing
    }
    
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
    // FIXED: Use ~3x players formula (more players = more songs needed)
    // This ensures enough variety so players don't get the same songs
    const MULTIPLIER = 3;
    let baseSongs = Math.floor(numPlayers * MULTIPLIER);
    
    // Ensure reasonable minimum and maximum
    baseSongs = Math.max(baseSongs, 30);  // Minimum 30 songs
    baseSongs = Math.min(baseSongs, 150); // Maximum 150 songs (reasonable for 50 players)
    
    // Adjust based on duration (30 seconds per song average including announcements)
    const songsPerMinute = 2;
    const maxSongsForDuration = targetDurationMinutes * songsPerMinute;
    
    // Use the smaller of the two (don't exceed time limit)
    let optimalSongs = Math.min(baseSongs, maxSongsForDuration);
    
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
    btn.textContent = '⏳ Starting generation...';
    btn.disabled = true;
    
    try {
        // Get branding data from localStorage
        let pubLogo = localStorage.getItem('pubLogo') || '';
        
        console.log('📋 Preparing to generate cards (ASYNC MODE)...');
        console.log('   Venue:', venueName);
        console.log('   Players:', numPlayers);
        console.log('   Pub Logo (stored):', pubLogo);
        
        // If pubLogo is a relative path, convert to full URL
        if (pubLogo && !pubLogo.startsWith('http')) {
            pubLogo = `${CONFIG.API_URL}${pubLogo}`;
            console.log('   Pub Logo (converted):', pubLogo);
        }
        
        const socialMedia = localStorage.getItem('socialMedia') || '';
        const includeQR = localStorage.getItem('includeQR') === 'true';
        
        console.log('   Social Media:', socialMedia);
        console.log('   Include QR:', includeQR);
        console.log('📤 Sending async request to backend...');
        
        // Use new async endpoint
        const response = await fetch(`${CONFIG.API_URL}/api/generate-cards-async`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                venue_name: venueName,
                num_players: numPlayers,
                optimal_songs: optimalSongs,
                pub_logo: pubLogo,
                social_media: socialMedia,
                include_qr: includeQR
            })
        });
        
        console.log('📨 Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Backend error:', errorText);
            throw new Error('Failed to start card generation');
        }
        
        const result = await response.json();
        console.log('✅ Task started:', result);
        
        const taskId = result.task_id;
        
        // Show progress message
        btn.textContent = '⏳ Generating cards...';
        
        // Poll for status
        let attempts = 0;
        const maxAttempts = 120; // 4 minutes max (2 seconds per poll)
        
        const checkStatus = async () => {
            attempts++;
            
            try {
                const statusResponse = await fetch(`${CONFIG.API_URL}/api/tasks/${taskId}`);
                
                if (!statusResponse.ok) {
                    throw new Error('Failed to check status');
                }
                
                const status = await statusResponse.json();
                console.log(`📊 Status check #${attempts}:`, status.status, `(${status.elapsed_time}s), Progress: ${status.progress || 0}%`);
                
                // Update button with progress
                if (status.status === 'processing' && status.progress) {
                    btn.textContent = `⏳ Generating... ${status.progress}%`;
                }
                
                if (status.status === 'completed') {
                    // Success!
                    console.log('✅ Generation completed:', status.result);
                    
                    btn.textContent = originalText;
                    btn.disabled = false;
                    
                    // Show success message
                    alert(`✅ Cards generated successfully!\n\nVenue: ${venueName}\nPlayers: ${numPlayers}\nOptimal songs: ${optimalSongs}\nEstimated duration: ${estimatedMinutes} minutes\n\nCards: ${status.result.num_cards}\nFile size: ${status.result.file_size_mb}MB\nGeneration time: ${status.result.generation_time}s\n\nDownloading now...`);
                    
                    // Download the PDF automatically
                    const timestamp = new Date().getTime();
                    const link = document.createElement('a');
                    link.href = `${CONFIG.API_URL}${status.result.download_url}?t=${timestamp}`;
                    link.download = `music_bingo_${venueName.replace(/\s+/g, '_')}_${numPlayers}players.pdf`;
                    link.target = '_blank';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                } else if (status.status === 'failed') {
                    // Failed
                    console.error('❌ Generation failed:', status.error);
                    
                    btn.textContent = originalText;
                    btn.disabled = false;
                    
                    alert(`❌ Card generation failed:\n\n${status.error}\n\nPlease try again or contact support.`);
                    
                } else if (attempts >= maxAttempts) {
                    // Timeout
                    console.error('⏱️ Polling timeout');
                    
                    btn.textContent = originalText;
                    btn.disabled = false;
                    
                    alert('⏱️ Card generation is taking longer than expected.\n\nThe task may still complete in the background.\nPlease check back in a few minutes.');
                    
                } else {
                    // Still processing, check again
                    btn.textContent = `⏳ Generating... (${Math.round(status.elapsed_time)}s)`;
                    setTimeout(checkStatus, 2000); // Poll every 2 seconds
                }
                
            } catch (error) {
                console.error('Error checking status:', error);
                
                if (attempts >= maxAttempts) {
                    btn.textContent = originalText;
                    btn.disabled = false;
                    alert('Failed to check generation status. Please try again.');
                } else {
                    // Retry
                    setTimeout(checkStatus, 2000);
                }
            }
        };
        
        // Start polling
        setTimeout(checkStatus, 2000); // First check after 2 seconds
        
    } catch (error) {
        console.error('❌ Error generating cards:', error);
        alert('❌ Error generating cards. Please try again.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

/**
 * Handle logo file upload
 */
async function handleLogoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('⚠️ Please select an image file (PNG, JPG, or SVG)');
        return;
    }
    
    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('⚠️ Image is too large. Please use a file smaller than 10MB.\n\nTip: You can compress your image at tinypng.com');
        return;
    }
    
    // Show loading state
    const uploadBtn = event.target.parentElement.querySelector('.upload-btn');
    const originalText = uploadBtn.textContent;
    uploadBtn.textContent = '⏳ Uploading...';
    uploadBtn.disabled = true;
    
    try {
        // Create FormData
        const formData = new FormData();
        formData.append('logo', file);
        
        // Upload to server
        const response = await fetch(`${CONFIG.API_URL}/api/upload-logo`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        const result = await response.json();
        
        // Set the URL in the input field
        document.getElementById('setupPubLogo').value = result.url;
        
        // Show preview
        showLogoPreview(result.url);
        
        console.log('✓ Logo uploaded successfully:', result.url);
        
    } catch (error) {
        console.error('Error uploading logo:', error);
        alert('❌ Error uploading logo. Please try again or use a URL instead.');
    } finally {
        uploadBtn.textContent = originalText;
        uploadBtn.disabled = false;
        // Clear the file input
        event.target.value = '';
    }
}

/**
 * Show logo preview
 */
function showLogoPreview(url) {
    const preview = document.getElementById('logoPreview');
    const img = document.getElementById('logoPreviewImg');
    
    img.src = url;
    preview.style.display = 'flex';
}

/**
 * Remove uploaded logo
 */
function removeLogo() {
    document.getElementById('setupPubLogo').value = '';
    document.getElementById('logoPreview').style.display = 'none';
    document.getElementById('logoPreviewImg').src = '';
}

/**
 * Toggle social media field when QR checkbox is checked
 */
function toggleSocialMediaField() {
    const checkbox = document.getElementById('setupIncludeQR');
    const field = document.getElementById('socialMediaField');
    
    if (checkbox.checked) {
        field.style.display = 'block';
        updateSocialPreview(); // Update preview when field appears
    } else {
        field.style.display = 'none';
    }
}

/**
 * Update social media URL preview based on platform and username
 */
function updateSocialPreview() {
    const platform = document.getElementById('socialPlatform').value;
    const username = document.getElementById('setupSocialMedia').value.trim();
    const preview = document.getElementById('socialPreview');
    
    if (!username) {
        preview.textContent = 'QR will link to: (enter username above)';
        preview.style.opacity = '0.6';
        return;
    }
    
    preview.style.opacity = '1';
    
    // Build URL based on platform
    let url = '';
    let cleanUsername = username.replace(/^@/, ''); // Remove @ if present
    
    switch(platform) {
        case 'instagram':
            url = `https://instagram.com/${cleanUsername}`;
            break;
        case 'facebook':
            url = `https://facebook.com/${cleanUsername}`;
            break;
        case 'tiktok':
            url = `https://tiktok.com/@${cleanUsername}`;
            break;
        case 'twitter':
            url = `https://twitter.com/${cleanUsername}`;
            break;
        case 'custom':
            // For custom, expect full URL
            url = username.startsWith('http') ? username : `https://${username}`;
            preview.textContent = `QR will link to: ${url}`;
            return;
    }
    
    preview.textContent = `QR will link to: ${url}`;
}

/**
 * Get the complete social media URL
 */
function getSocialMediaURL() {
    const platform = document.getElementById('socialPlatform').value;
    const username = document.getElementById('setupSocialMedia').value.trim();
    
    if (!username) return '';
    
    let cleanUsername = username.replace(/^@/, '');
    
    switch(platform) {
        case 'instagram':
            return `https://instagram.com/${cleanUsername}`;
        case 'facebook':
            return `https://facebook.com/${cleanUsername}`;
        case 'tiktok':
            return `https://tiktok.com/@${cleanUsername}`;
        case 'twitter':
            return `https://twitter.com/${cleanUsername}`;
        case 'custom':
            return username.startsWith('http') ? username : `https://${username}`;
        default:
            return username;
    }
}
