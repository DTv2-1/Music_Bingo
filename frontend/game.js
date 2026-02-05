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
    currentSound: null,     // Currently playing Howl instance
    isPlaying: false,       // Is audio currently playing
    announcementsData: null, // Loaded announcements
    announcementsAI: null,   // AI-generated announcements (optional)
    venueName: localStorage.getItem('venueName') || 'this venue', // Venue name from localStorage
    welcomeAnnounced: false, // Track if welcome was announced
    halfwayAnnounced: false, // Track if halfway announcement was made
    autoNextTimer: null      // Timer ID for auto-next playback
};

/**
 * Reset game state to initial values (for new sessions)
 */
function resetGameState() {
    console.log('🔄 Resetting game state to initial values...');
    
    // Cancel any pending auto-next timer
    if (gameState.autoNextTimer) {
        clearTimeout(gameState.autoNextTimer);
        gameState.autoNextTimer = null;
    }
    
    gameState.pool = [];
    gameState.remaining = [];
    gameState.called = [];
    gameState.currentTrack = null;
    gameState.isPlaying = false;
    gameState.announcementsData = null;
    gameState.announcementsAI = null;
    gameState.welcomeAnnounced = false;
    gameState.halfwayAnnounced = false;
    // Note: Keep venueName and sessionId as they're set by the session loader
    console.log('✅ Game state reset complete');
}

// ============================================================================
// VENUE-SPECIFIC CONFIGURATION STORAGE
// ============================================================================

/**
 * Save venue-specific configuration to localStorage
 * Each venue gets its own configuration namespace
 */
function saveVenueConfig(venueName, config) {
    const venueKey = `venue_${venueName.toLowerCase().replace(/\s+/g, '_')}`;
    const existingConfigs = JSON.parse(localStorage.getItem('venueConfigs') || '{}');
    existingConfigs[venueKey] = {
        ...config,
        lastUpdated: new Date().toISOString()
    };
    localStorage.setItem('venueConfigs', JSON.stringify(existingConfigs));
    console.log(`💾 Saved config to localStorage for venue: ${venueName}`);

    // Also save to database
    saveVenueConfigToDatabase(venueName, config);
}

/**
 * Save venue configuration to database via API
 */
async function saveVenueConfigToDatabase(venueName, config) {
    try {
        const apiUrl = CONFIG.API_URL;
        const url = `${apiUrl}/api/venue-config/${encodeURIComponent(venueName)}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                num_players: parseInt(config.numPlayers) || 25,
                voice_id: config.voiceId,
                selected_decades: JSON.parse(config.selectedDecades || '[]'),
                pub_logo: config.pubLogo,
                social_platform: config.socialPlatform,
                social_username: config.socialUsername,
                include_qr: config.includeQR === 'true',
                prize_4corners: config.prize4Corners,
                prize_first_line: config.prizeFirstLine,
                prize_full_house: config.prizeFullHouse
            })
        });

        if (response.ok) {
            console.log(`✅ Saved config to database for venue: ${venueName}`);
        } else {
            console.warn(`⚠️ Failed to save to database, using localStorage only`);
        }
    } catch (error) {
        console.warn(`⚠️ Database save failed, using localStorage only:`, error);
    }
}

/**
 * Load venue-specific configuration from localStorage
 * Returns null if no config exists for this venue
 */
async function loadVenueConfig(venueName) {
    // First try to load from database
    try {
        const apiUrl = CONFIG.API_URL;
        const url = `${apiUrl}/api/venue-config/${encodeURIComponent(venueName)}`;

        const response = await fetch(url);

        if (response.ok) {
            const data = await response.json();
            if (data.success && data.config) {
                console.log(`📂 Loaded config from database for venue: ${venueName}`);
                // Convert database format to localStorage format
                return {
                    venueName: data.config.venue_name,
                    numPlayers: data.config.num_players.toString(),
                    voiceId: data.config.voice_id,
                    selectedDecades: JSON.stringify(data.config.selected_decades),
                    pubLogo: data.config.pub_logo,
                    socialPlatform: data.config.social_platform,
                    socialUsername: data.config.social_username,
                    includeQR: data.config.include_qr.toString(),
                    prize4Corners: data.config.prize_4corners,
                    prizeFirstLine: data.config.prize_first_line,
                    prizeFullHouse: data.config.prize_full_house,
                    lastUpdated: data.config.updated_at
                };
            }
        }
    } catch (error) {
        console.warn('⚠️ Could not load from database, trying localStorage:', error);
    }

    // Fallback to localStorage
    const venueKey = `venue_${venueName.toLowerCase().replace(/\s+/g, '_')}`;
    const existingConfigs = JSON.parse(localStorage.getItem('venueConfigs') || '{}');
    const config = existingConfigs[venueKey];
    if (config) {
        console.log(`📂 Loaded config from localStorage for venue: ${venueName}`);
    }
    return config || null;
}

/**
 * Show notification to user (for feedback)
 */
function showGameNotification(message, type = 'info') {
    // Check if notification already exists
    let notification = document.getElementById('gameNotification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'gameNotification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: opacity 0.3s, transform 0.3s;
            opacity: 0;
            transform: translateY(-10px);
        `;
        document.body.appendChild(notification);
    }

    // Set colors based on type
    const colors = {
        success: 'background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white;',
        error: 'background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); color: white;',
        info: 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;'
    };

    notification.style.cssText += colors[type] || colors.info;
    notification.textContent = message;

    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateY(0)';
    }, 10);

    // Animate out after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-10px)';
    }, 3000);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

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
    console.log('🎮 Music Bingo - Initializing...');

    // Check if we're loading from a session
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');

    if (sessionId) {
        console.log(`📦 Loading session: ${sessionId}`);
        await loadSessionAndStart(sessionId);
        return;
    }

    // No session parameter - redirect to index to create a new session
    console.log('❌ No session ID found, redirecting to index.html...');
    window.location.href = 'index.html';
});

/**
 * Load session data and start the game automatically
 */
async function loadSessionAndStart(sessionId) {
    try {
        console.log(`📦 Loading session: ${sessionId}`);
        
        // Save session_id to localStorage for loading song pool
        localStorage.setItem('currentSessionId', sessionId);
        console.log(`🔑 Session ID saved to localStorage: ${sessionId}`);
        
        const API_URL = CONFIG.API_URL || '';
        const response = await fetch(`${API_URL}/api/bingo/session/${sessionId}`);
        
        if (!response.ok) {
            throw new Error('Session not found');
        }

        const session = await response.json();
        console.log('✅ Session loaded:', session);

        // 🔧 CRITICAL FIX: Clear old game state from localStorage to start fresh
        console.log('🧹 Clearing old game state for new session...');
        localStorage.removeItem('gameState');
        
        // Reset in-memory game state to initial values
        resetGameState();
        
        // Reset initialization flag so game can be re-initialized
        gameInitialized = false;
        
        // Hide setup modal
        document.getElementById('setupModal').style.display = 'none';

        // Apply session configuration to game state
        gameState.venueName = session.venue_name;
        gameState.sessionId = sessionId;

        // Save to localStorage for backwards compatibility
        localStorage.setItem('venueName', session.venue_name);

        // Store configuration
        const config = {
            numPlayers: session.num_players,
            decades: session.decades,
            voiceId: session.voice_id,
            logoUrl: session.logo_url,
            socialMedia: session.social_media,
            includeQr: session.include_qr,
            prizes: session.prizes
        };

        // Save logo and branding to localStorage for card generation
        localStorage.setItem('pubLogo', session.logo_url || '');
        localStorage.setItem('socialMedia', session.social_media || '');
        localStorage.setItem('includeQR', session.include_qr ? 'true' : 'false');
        localStorage.setItem('prize4Corners', session.prizes?.four_corners || '');
        localStorage.setItem('prizeFirstLine', session.prizes?.first_line || '');
        localStorage.setItem('prizeFullHouse', session.prizes?.full_house || '');
        
        // ⚠️ CRITICAL FIX: Save voice_id and decades for TTS announcements
        localStorage.setItem('voiceId', session.voice_id || 'JBFqnCBsd6RMkjVDRZzb');
        localStorage.setItem('selectedDecades', JSON.stringify(session.decades || []));
        localStorage.setItem('numPlayers', session.num_players || 25);
        
        console.log('💾 Saved session branding to localStorage:', {
            pubLogo: session.logo_url,
            socialMedia: session.social_media,
            includeQR: session.include_qr,
            voiceId: session.voice_id,
            decades: session.decades
        });

        await saveVenueConfig(session.venue_name, config);

        // Update UI with session data (hidden inputs and displays)
        const venueNameInput = document.getElementById('venueName');
        if (venueNameInput) {
            venueNameInput.value = session.venue_name;
        }
        const venueNameDisplay = document.getElementById('venueNameDisplay');
        if (venueNameDisplay) {
            venueNameDisplay.textContent = session.venue_name;
        }
        
        const numPlayersInput = document.getElementById('numPlayers');
        if (numPlayersInput) {
            numPlayersInput.value = session.num_players;
        }
        const numPlayersDisplay = document.getElementById('numPlayersDisplay');
        if (numPlayersDisplay) {
            numPlayersDisplay.textContent = session.num_players;
        }
        
        // Save to localStorage
        localStorage.setItem('numPlayers', session.num_players.toString());
        
        // Update song estimation
        updateSongEstimation();
        
        // Update voice display
        const voiceDisplay = document.getElementById('voiceDisplay');
        if (voiceDisplay && session.voice_id) {
            const voiceNames = {
                'XrExE9yKIg1WjnnlVkGX': 'Charlotte',
                'JBFqnCBsd6RMkjVDRZzb': 'George',
                'pFZP5JQG7iQjIQuC4Bku': 'Lily',
                'nPczCjzI2devNBz1zQrb': 'Brian'
            };
            voiceDisplay.textContent = voiceNames[session.voice_id] || 'George';
        }
        
        // Update decades display
        const decadesDisplay = document.getElementById('decadesDisplay');
        if (decadesDisplay && session.decades && session.decades.length > 0) {
            const decadeLabels = session.decades.map(d => d.replace('19', "'").replace('20', "'"));
            decadesDisplay.textContent = decadeLabels.join(', ');
        }
        
        // Update genres display
        const genresDisplayContainer = document.getElementById('genresDisplayContainer');
        const genresDisplay = document.getElementById('genresDisplay');
        if (genresDisplayContainer && genresDisplay && session.genres && session.genres.length > 0) {
            genresDisplayContainer.style.display = 'flex';
            genresDisplay.textContent = session.genres.join(', ');
        }
        
        // Update logo display
        const logoDisplayContainer = document.getElementById('logoDisplayContainer');
        if (logoDisplayContainer && session.logo_url) {
            logoDisplayContainer.style.display = 'flex';
        }
        
        // Update QR code display
        const qrDisplayContainer = document.getElementById('qrDisplayContainer');
        const qrDisplay = document.getElementById('qrDisplay');
        if (qrDisplayContainer && qrDisplay && session.include_qr && session.social_media) {
            qrDisplayContainer.style.display = 'flex';
            // Extract platform from URL or show URL
            let displayText = session.social_media;
            if (session.social_media.includes('instagram.com')) {
                displayText = 'Instagram: ' + session.social_media.split('/').pop();
            } else if (session.social_media.includes('facebook.com')) {
                displayText = 'Facebook: ' + session.social_media.split('/').pop();
            } else if (session.social_media.includes('tiktok.com')) {
                displayText = 'TikTok: ' + session.social_media.split('@').pop();
            } else if (session.social_media.includes('twitter.com')) {
                displayText = 'Twitter: ' + session.social_media.split('/').pop();
            }
            qrDisplay.textContent = displayText;
        }
        
        // Update prizes display
        const prizesDisplayContainer = document.getElementById('prizesDisplayContainer');
        if (prizesDisplayContainer && session.prizes) {
            let hasPrizes = false;
            
            if (session.prizes.four_corners) {
                const prize4CornersDisplay = document.getElementById('prize4CornersDisplay');
                if (prize4CornersDisplay) {
                    prize4CornersDisplay.style.display = 'block';
                    prize4CornersDisplay.querySelector('span:last-child').textContent = session.prizes.four_corners;
                    hasPrizes = true;
                }
            }
            
            if (session.prizes.first_line) {
                const prizeFirstLineDisplay = document.getElementById('prizeFirstLineDisplay');
                if (prizeFirstLineDisplay) {
                    prizeFirstLineDisplay.style.display = 'block';
                    prizeFirstLineDisplay.querySelector('span:last-child').textContent = session.prizes.first_line;
                    hasPrizes = true;
                }
            }
            
            if (session.prizes.full_house) {
                const prizeFullHouseDisplay = document.getElementById('prizeFullHouseDisplay');
                if (prizeFullHouseDisplay) {
                    prizeFullHouseDisplay.style.display = 'block';
                    prizeFullHouseDisplay.querySelector('span:last-child').textContent = session.prizes.full_house;
                    hasPrizes = true;
                }
            }
            
            if (hasPrizes) {
                prizesDisplayContainer.style.display = 'block';
            }
        }

        // Start the game with the session configuration
        console.log('🚀 Starting game with session configuration...');
        await startGameFromConfig(config);

    } catch (error) {
        console.error('❌ Error loading session:', error);
        alert('Failed to load session. Please try again or create a new session.');
        // Redirect to sessions page
        window.location.href = '/bingo-sessions.html';
    }
}

/**
 * Start game with provided configuration (bypassing setup modal)
 */
async function startGameFromConfig(config) {
    console.log('🎵 Starting game from config:', config);

    // Set selected decades in gameState
    gameState.selectedDecades = config.decades;
    localStorage.setItem('selectedDecades', JSON.stringify(config.decades));

    // Set voice
    if (config.voiceId) {
        gameState.voiceId = config.voiceId;
    }

    // Store prizes if any
    if (config.prizes) {
        gameState.prizes = config.prizes;
    }

    // Initialize the game (this will load pool, announcements, etc.)
    await initializeGame();
    
    // Clear UI display of called songs
    const calledList = document.getElementById('calledList');
    if (calledList) {
        calledList.innerHTML = '';
    }
    
    // Reset current track display
    const currentTrackElement = document.getElementById('currentTrack');
    if (currentTrackElement) {
        currentTrackElement.innerHTML = '<em>No song playing</em>';
    }

    console.log('✅ Game started successfully from session!');
}

/**
 * Initialize the setup modal with event listeners
 */
async function initializeSetupModal() {
    const setupVenueName = document.getElementById('setupVenueName');
    const setupNumPlayers = document.getElementById('setupNumPlayers');
    const setupEstimation = document.getElementById('setupEstimation');

    console.log('🔧 Initializing setup modal...');

    // Load last used venue name
    const savedVenue = localStorage.getItem('venueName');
    if (savedVenue) {
        console.log(`📂 Found saved venue: ${savedVenue}`);
        setupVenueName.value = savedVenue;

        // Try to load venue-specific config
        const venueConfig = await loadVenueConfig(savedVenue);
        console.log('📋 Loaded config:', venueConfig);

        if (venueConfig) {
            // Restore all venue-specific settings
            console.log('🔄 Restoring venue configuration...');

            if (venueConfig.numPlayers) {
                console.log('  - Players:', venueConfig.numPlayers);
                setupNumPlayers.value = venueConfig.numPlayers;
            }
            if (venueConfig.voiceId) {
                console.log('  - Voice:', venueConfig.voiceId);
                document.getElementById('setupVoice').value = venueConfig.voiceId;
            }
            if (venueConfig.selectedDecades) {
                console.log('  - Decades:', venueConfig.selectedDecades);
                try {
                    const decades = JSON.parse(venueConfig.selectedDecades);
                    document.querySelectorAll('input[name="decades"]').forEach(checkbox => {
                        checkbox.checked = decades.includes(checkbox.value);
                    });
                } catch (e) {
                    console.warn('Could not restore decade selection:', e);
                }
            }
            if (venueConfig.pubLogo) {
                console.log('  - Logo:', venueConfig.pubLogo);
                const logoInput = document.getElementById('setupPubLogo');
                logoInput.value = venueConfig.pubLogo;
                console.log('  - Logo input set:', logoInput.value);
                showLogoPreview(venueConfig.pubLogo);
            }
            if (venueConfig.socialPlatform) {
                console.log('  - Social platform:', venueConfig.socialPlatform);
                document.getElementById('socialPlatform').value = venueConfig.socialPlatform;
            }
            if (venueConfig.socialUsername) {
                console.log('  - Social username:', venueConfig.socialUsername);
                document.getElementById('setupSocialMedia').value = venueConfig.socialUsername;
            }
            if (venueConfig.includeQR === 'true') {
                console.log('  - Include QR: true');
                document.getElementById('setupIncludeQR').checked = true;
                toggleSocialMediaField();
            }
            if (venueConfig.prize4Corners) {
                console.log('  - 4 Corners prize:', venueConfig.prize4Corners);
                document.getElementById('prize4Corners').value = venueConfig.prize4Corners;
            }
            if (venueConfig.prizeFirstLine) {
                console.log('  - First Line prize:', venueConfig.prizeFirstLine);
                document.getElementById('prizeFirstLine').value = venueConfig.prizeFirstLine;
            }
            if (venueConfig.prizeFullHouse) {
                console.log('  - Full House prize:', venueConfig.prizeFullHouse);
                document.getElementById('prizeFullHouse').value = venueConfig.prizeFullHouse;
            }

            console.log('✅ Restored venue-specific configuration');
        }
    }

    // Fallback: load global settings (for backward compatibility) - only if no venue config loaded
    if (!savedVenue || !loadVenueConfig(savedVenue)) {
        const savedPlayers = localStorage.getItem('numPlayers');
        const savedVoice = localStorage.getItem('voiceId');
        const savedDecades = localStorage.getItem('selectedDecades');
        const savedPubLogo = localStorage.getItem('pubLogo');
        const savedSocialMedia = localStorage.getItem('socialMedia');
        const savedIncludeQR = localStorage.getItem('includeQR');
        const savedPrize4Corners = localStorage.getItem('prize4Corners');
        const savedPrizeFirstLine = localStorage.getItem('prizeFirstLine');
        const savedPrizeFullHouse = localStorage.getItem('prizeFullHouse');

        if (savedPlayers) setupNumPlayers.value = savedPlayers;
        if (savedVoice) document.getElementById('setupVoice').value = savedVoice;
        if (savedPubLogo) {
            document.getElementById('setupPubLogo').value = savedPubLogo;
            showLogoPreview(savedPubLogo);
        }
        if (savedSocialMedia) document.getElementById('setupSocialMedia').value = savedSocialMedia;
        if (savedIncludeQR === 'true') {
            document.getElementById('setupIncludeQR').checked = true;
            toggleSocialMediaField();
        }
        if (savedPrize4Corners) document.getElementById('prize4Corners').value = savedPrize4Corners;
        if (savedPrizeFirstLine) document.getElementById('prizeFirstLine').value = savedPrizeFirstLine;
        if (savedPrizeFullHouse) document.getElementById('prizeFullHouse').value = savedPrizeFullHouse;

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

    // Load venue config when venue name changes (on blur/tab out)
    setupVenueName.addEventListener('blur', async () => {
        const venueName = setupVenueName.value.trim();
        if (venueName && venueName !== 'this venue') {
            const venueConfig = await loadVenueConfig(venueName);
            if (venueConfig) {
                // Auto-fill form with saved config
                if (venueConfig.numPlayers) setupNumPlayers.value = venueConfig.numPlayers;
                if (venueConfig.voiceId) document.getElementById('setupVoice').value = venueConfig.voiceId;
                if (venueConfig.selectedDecades) {
                    try {
                        const decades = JSON.parse(venueConfig.selectedDecades);
                        document.querySelectorAll('input[name="decades"]').forEach(checkbox => {
                            checkbox.checked = decades.includes(checkbox.value);
                        });
                    } catch (e) { }
                }
                if (venueConfig.pubLogo) {
                    document.getElementById('setupPubLogo').value = venueConfig.pubLogo;
                    showLogoPreview(venueConfig.pubLogo);
                }
                if (venueConfig.socialPlatform) document.getElementById('socialPlatform').value = venueConfig.socialPlatform;
                if (venueConfig.socialUsername) document.getElementById('setupSocialMedia').value = venueConfig.socialUsername;
                if (venueConfig.includeQR === 'true') {
                    document.getElementById('setupIncludeQR').checked = true;
                    toggleSocialMediaField();
                }
                if (venueConfig.prize4Corners) document.getElementById('prize4Corners').value = venueConfig.prize4Corners;
                if (venueConfig.prizeFirstLine) document.getElementById('prizeFirstLine').value = venueConfig.prizeFirstLine;
                if (venueConfig.prizeFullHouse) document.getElementById('prizeFullHouse').value = venueConfig.prizeFullHouse;

                console.log(`✅ Auto-loaded saved config for: ${venueName}`);
                showNotification(`📂 Loaded saved settings for ${venueName}`, 'success');
            }
        }
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

        // Get social media info (platform + username)
        const socialPlatform = document.getElementById('socialPlatform').value;
        const socialUsername = document.getElementById('setupSocialMedia').value.trim();
        const socialMediaURL = includeQR ? getSocialMediaURL() : '';

        // Get prizes (optional)
        const prize4Corners = document.getElementById('prize4Corners')?.value.trim() || '';
        const prizeFirstLine = document.getElementById('prizeFirstLine')?.value.trim() || '';
        const prizeFullHouse = document.getElementById('prizeFullHouse')?.value.trim() || '';

        // Save settings globally (for current session)
        gameState.venueName = venueName;
        gameState.selectedDecades = selectedDecades;
        localStorage.setItem('venueName', venueName);
        localStorage.setItem('currentVenue', venueName); // For jingle-manager
        localStorage.setItem('setupCompleted', 'true');

        // Save venue-specific configuration
        saveVenueConfig(venueName, {
            venueName: venueName,
            numPlayers: numPlayers.toString(),
            voiceId: selectedVoice,
            selectedDecades: JSON.stringify(selectedDecades),
            pubLogo: pubLogo,
            socialPlatform: socialPlatform,
            socialUsername: socialUsername,
            socialMedia: socialMediaURL,
            includeQR: includeQR.toString(),
            prize4Corners: prize4Corners,
            prizeFirstLine: prizeFirstLine,
            prizeFullHouse: prizeFullHouse
        });

        // Also save to global keys for backward compatibility
        localStorage.setItem('numPlayers', numPlayers.toString());
        localStorage.setItem('voiceId', selectedVoice);
        localStorage.setItem('selectedDecades', JSON.stringify(selectedDecades));
        localStorage.setItem('pubLogo', pubLogo);
        localStorage.setItem('socialMedia', socialMediaURL);
        localStorage.setItem('includeQR', includeQR.toString());
        localStorage.setItem('prize4Corners', prize4Corners);
        localStorage.setItem('prizeFirstLine', prizeFirstLine);
        localStorage.setItem('prizeFullHouse', prizeFullHouse);

        // Update jingle manager link with venue
        const jingleManagerLink = document.getElementById('jingleManagerLink');
        if (jingleManagerLink && venueName !== 'this venue') {
            jingleManagerLink.href = `/jingle-manager?venue=${encodeURIComponent(venueName)}`;
        } else {
            jingleManagerLink.href = '/jingle-manager';
        }

        // Update main UI inputs (hidden) and display elements
        document.getElementById('venueName').value = venueName;
        document.getElementById('numPlayers').value = numPlayers;
        document.getElementById('venueNameDisplay').textContent = venueName;
        document.getElementById('numPlayersDisplay').textContent = numPlayers;
        
        // Update song estimation display
        updateSongEstimation();

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
 * Close setup modal without saving
 */
function closeSetupModal() {
    const modal = document.getElementById('setupModal');
    if (confirm('⚠️ Are you sure you want to close the setup? The game will not be initialized.')) {
        modal.classList.add('hidden');
        console.log('Setup modal closed by user');
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
        const venueDisplay = document.getElementById('venueNameDisplay');
        if (venueDisplay) venueDisplay.textContent = savedName;
        console.log(`✓ Loaded venue: ${savedName}`);
    }
    
    // Load number of players
    const savedPlayers = localStorage.getItem('numPlayers');
    if (savedPlayers) {
        const numPlayersInput = document.getElementById('numPlayers');
        if (numPlayersInput) {
            numPlayersInput.value = savedPlayers;
        }
        const numPlayersDisplay = document.getElementById('numPlayersDisplay');
        if (numPlayersDisplay) {
            numPlayersDisplay.textContent = savedPlayers;
        }
        console.log(`✓ Loaded players: ${savedPlayers}`);
        // Update song estimation
        updateSongEstimation();
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
    // *** CRITICAL CHANGE: Load session file instead of pool ***
    // The session file contains EXACTLY the songs printed on the cards
    // This ensures songs played match what's on the physical cards
    
    try {
        // First, check if we have a session_id (from card generation)
        const sessionId = localStorage.getItem('currentSessionId');
        
        if (sessionId) {
            console.log(`🔑 Found session ID in localStorage: ${sessionId}`);
            console.log(`📡 Fetching session from: ${CONFIG.API_URL}/api/session?session_id=${sessionId}`);
            
            // Fetch session from database using session_id
            const sessionResponse = await fetch(`${CONFIG.API_URL}/api/session?session_id=${sessionId}`);
            
            console.log(`📨 Response status: ${sessionResponse.status}`);
            
            if (sessionResponse.ok) {
                const sessionData = await sessionResponse.json();
                console.log('✅ Loaded session from database (session_id)');
                console.log(`   Source: ${sessionData.source}`);
                console.log(`   Session ID: ${sessionData.session_id}`);
                console.log(`   Generated: ${sessionData.generated_at}`);
                console.log(`   Venue: ${sessionData.venue_name}`);
                console.log(`   Num Players: ${sessionData.num_players}`);
                console.log(`   Songs count: ${sessionData.songs?.length || 0}`);
                console.log(`   PDF URL: ${sessionData.pdf_url || 'none'}`);
                
                if (!sessionData.songs || sessionData.songs.length === 0) {
                    console.warn('⚠️  Session loaded but song_pool is EMPTY!');
                    console.warn('   This means cards have NOT been generated yet.');
                    console.warn('   Will fall back to pool.json...');
                } else {
                    console.log(`   First 3 songs:`, sessionData.songs.slice(0, 3).map(s => s.title));
                }
                
                // Use EXACT songs from session (no filtering, no shuffling)
                gameState.pool = sessionData.songs || [];
                gameState.remaining = [...(sessionData.songs || [])];
                
                // Update venue name if provided in session
                if (sessionData.venue_name) {
                    gameState.venueName = sessionData.venue_name;
                    document.getElementById('venueName').value = sessionData.venue_name;
                }
                
                console.log(`✅ Game will use ${gameState.remaining.length} songs from database`);
                console.log('⚠️  These songs MATCH the printed cards!');
                
                return; // Exit early with database session
            } else {
                console.warn(`⚠️  Session ${sessionId} not found in database, trying fallbacks...`);
            }
        }
        
        // Second, try to load session data from localStorage (saved after card generation)
        const storedSessionData = localStorage.getItem('currentSessionData');
        
        if (storedSessionData) {
            const sessionData = JSON.parse(storedSessionData);
            console.log('✅ Loaded session data from localStorage');
            console.log(`   Generated: ${sessionData.generated_at}`);
            console.log(`   Venue: ${sessionData.venue_name}`);
            console.log(`   Songs: ${sessionData.songs.length}`);
            
            // Use EXACT songs from session (no filtering, no shuffling)
            gameState.pool = sessionData.songs;
            gameState.remaining = [...sessionData.songs]; // Use all session songs in order
            
            // Update venue name if provided in session
            if (sessionData.venue_name) {
                gameState.venueName = sessionData.venue_name;
                document.getElementById('venueName').value = sessionData.venue_name;
            }
            
            console.log(`✅ Game will use ${gameState.remaining.length} songs from localStorage`);
            console.log('⚠️  These songs MATCH the printed cards!');
            
            return; // Exit early with session data
        }
        
        // Third, try to load the session file from server (legacy fallback)
        const sessionResponse = await fetch(`${CONFIG.API_URL}/api/session`);
        
        if (sessionResponse.ok) {
            const sessionData = await sessionResponse.json();
            console.log('✅ Loaded session file from server (legacy)');
            console.log(`   Source: ${sessionData.source}`);
            console.log(`   Generated: ${sessionData.generated_at}`);
            console.log(`   Venue: ${sessionData.venue_name}`);
            console.log(`   Songs: ${sessionData.songs.length}`);
            
            // Save to localStorage for future use
            localStorage.setItem('currentSessionData', JSON.stringify(sessionData));
            
            // Use EXACT songs from session (no filtering, no shuffling)
            gameState.pool = sessionData.songs;
            gameState.remaining = [...sessionData.songs]; // Use all session songs in order
            
            // Update venue name if provided in session
            if (sessionData.venue_name) {
                gameState.venueName = sessionData.venue_name;
                document.getElementById('venueName').value = sessionData.venue_name;
            }
            
            console.log(`✅ Game will use ${gameState.remaining.length} songs from session file`);
            console.log('⚠️  These songs MATCH the printed cards!');
            
        } else {
            // Fallback: Use old pool.json method if no session file exists
            console.warn('⚠️  No session data found - falling back to pool.json');
            console.warn('⚠️  WARNING: Songs may NOT match printed cards!');
            console.warn('⚠️  Please generate cards first to create session file.');
            
            const poolResponse = await fetch(`${CONFIG.API_URL}/api/pool`);
            if (!poolResponse.ok) {
                throw new Error(`Failed to load pool.json`);
            }
            
            const poolData = await poolResponse.json();
            gameState.pool = poolData.songs;
            
            // Get selected decades from localStorage or gameState
            let selectedDecades = gameState.selectedDecades;
            if (!selectedDecades) {
                const savedDecades = localStorage.getItem('selectedDecades');
                selectedDecades = savedDecades ? JSON.parse(savedDecades) : ['1960s', '1970s', '1980s', '1990s'];
                gameState.selectedDecades = selectedDecades;
            }
            
            // Filter songs by selected decades
            const filteredSongs = poolData.songs.filter(song => {
                const year = parseInt(song.release_year);
                return selectedDecades.some(decade => {
                    const startYear = parseInt(decade.substring(0, 4));
                    const endYear = startYear + 9;
                    return year >= startYear && year <= endYear;
                });
            });
            
            if (filteredSongs.length === 0) {
                console.warn('⚠️ No songs found for selected decades, using all songs');
                gameState.pool = poolData.songs;
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
        }
        
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
        
        console.log(`✓ Loaded ${gameState.pool.length} songs`);
        
    } catch (error) {
        console.error('❌ Failed to load songs:', error);
        throw error;
    }
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
        // Get session_id from localStorage to fetch voice-specific announcements
        const sessionId = localStorage.getItem('sessionId');
        
        let url = `${CONFIG.API_URL}/api/announcements-ai`;
        
        // If we have a session_id, use the session-specific endpoint
        if (sessionId) {
            url = `${CONFIG.API_URL}/api/session-announcements?session_id=${sessionId}`;
            console.log(`🎤 Loading announcements for session ${sessionId} with correct voice`);
        }
        
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            
            // Remove metadata if present
            if (data._metadata) {
                console.log(`📢 Voice ID for announcements: ${data._metadata.voice_id}`);
                delete data._metadata;
            }
            
            gameState.announcementsAI = data;
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
                
                // If songs have been called, welcome announcement was already done
                gameState.welcomeAnnounced = state.welcomeAnnounced || (validCalled.length > 0);
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
    // Cancel auto-next timer if button was pressed manually
    if (gameState.autoNextTimer) {
        clearTimeout(gameState.autoNextTimer);
        gameState.autoNextTimer = null;
        console.log('⏹️ Auto-next timer cancelled (manual button press)');
    }

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

    // Update session status to 'active' on first song
    if (gameState.called.length === 1) {
        await updateSessionStatus('active');
    }

    // Update UI immediately
    updateCurrentTrackDisplay(track);
    updateCalledList();
    updateStats();

    // Change button to PAUSE while playing
    const nextButton = document.getElementById('nextTrack');
    nextButton.textContent = '⏸️ PAUSE';
    nextButton.onclick = pauseCurrentTrack;
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

        // Step 2: Check for jingle playback
        await checkAndPlayJingle();

        // Step 3: Check for 10-song summary announcement
        const songsPlayed = gameState.called.length;
        if (songsPlayed > 0 && songsPlayed % 10 === 0) {
            updateStatus('📋 10-song summary...', true);
            await announceTenSongSummary();
            // Short pause after summary
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Step 4: Check for halfway announcement
        const totalSongs = gameState.pool.length;
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

        // Done - wait for auto-next delay
        const delaySeconds = CONFIG.AUTO_NEXT_DELAY_MS / 1000;
        updateStatus(`⏱️ Next song in ${delaySeconds} seconds... (or press button to skip wait)`, false);

        // Schedule auto-play next track after delay
        const autoNextTimer = setTimeout(() => {
            console.log('⏰ Auto-playing next track...');
            playNextTrack();
        }, CONFIG.AUTO_NEXT_DELAY_MS);

        // Store timer ID so it can be cancelled if button is pressed
        gameState.autoNextTimer = autoNextTimer;

    } catch (error) {
        console.error('Error playing track:', error);
        updateStatus(`❌ Error: ${error.message}`, false);
    } finally {
        // Change button back to NEXT SONG
        const nextButton = document.getElementById('nextTrack');
        nextButton.textContent = '▶️ NEXT SONG';
        nextButton.onclick = playNextTrack;
        setButtonState('nextTrack', true);
        gameState.isPlaying = false;
    }
}

/**
 * Pause current playback
 */
function pauseCurrentTrack() {
    console.log('⏸️ Pausing playback...');
    
    // Stop current audio
    if (gameState.currentSound) {
        gameState.currentSound.pause();
        gameState.currentSound = null;
    }
    
    // Cancel auto-next timer
    if (gameState.autoNextTimer) {
        clearTimeout(gameState.autoNextTimer);
        gameState.autoNextTimer = null;
    }
    
    // Change button back to NEXT SONG
    const nextButton = document.getElementById('nextTrack');
    nextButton.textContent = '▶️ NEXT SONG';
    nextButton.onclick = playNextTrack;
    setButtonState('nextTrack', true);
    
    gameState.isPlaying = false;
    updateStatus('⏸️ Paused - Press NEXT SONG to continue', false);
}

/**
 * Generate welcome announcement text
 */
function generateWelcomeText() {
    const welcomeScripts = [
        `Ladies and gentlemen, welcome to Music Bingo at ${gameState.venueName}! Tonight, we're dropping beats instead of balls. Grab your cards, your markers, and get ready to mark off those songs as we play short clips. No titles or artists will be announced—just listen closely, sing along if you know it, and shout 'Bingo!' when you get a line, all 4 corners, or full house. We've got great prizes up for grabs, so let's kick things off with some classic tunes!`,

        `Hello everyone and welcome to the ultimate Music Bingo night at ${gameState.venueName}! Get those dabbers ready because we're about to play hits from across the decades. I'll spin the tracks, you identify them on your card—without any hints on the name or who sings it. First to a full line, all 4 corners, or full house wins! Are you ready to test your music knowledge? Let's get this party started!`,

        `Good evening, music lovers! It's time for Music Bingo extravaganza at ${gameState.venueName}. Rules are simple: We play a snippet, you spot the song on your card and mark it off. No song titles or artists given—just pure ear power. Shout 'Bingo!' when you get a line, all 4 corners, or full house. Prizes for the quickest bingos, so stay sharp. Here comes the first track—good luck!`
    ];

    return welcomeScripts[Math.floor(Math.random() * welcomeScripts.length)];
}

/**
 * Announce last 10 songs summary
 */
async function announceTenSongSummary() {
    const last10 = gameState.called.slice(-10);
    const summaryText = generate10SongSummaryText(last10);
    
    console.log('📋 Announcing 10-song summary...');
    
    try {
        const audioData = await generateTTS(summaryText);
        await playTTSAudio(audioData);
        console.log('✅ 10-song summary complete');
    } catch (error) {
        console.error('Error playing 10-song summary:', error);
        throw error;
    }
}

/**
 * Generate 10-song summary text
 */
function generate10SongSummaryText(last10Songs) {
    const summaryScripts = [
        `Alright everyone, let's run through the last 10 songs for anyone who might have missed them. Listen carefully and mark them off if you haven't already!`,
        
        `Time for a quick recap! Here are the last 10 tracks we've played. Make sure you've got them all marked on your cards!`,
        
        `Let's do a summary of the last 10 songs. If you missed any, here's your chance to catch up!`
    ];
    
    const intro = summaryScripts[Math.floor(Math.random() * summaryScripts.length)];
    const songList = last10Songs.map((song, i) => 
        `Number ${i + 1}: ${song.title} by ${song.artist}`
    ).join('. ');
    
    return `${intro} ${songList}. Alright, let's continue with the next track!`;
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

        // Always use trivia (interesting facts) - 100%
        const randomType = 'trivia';

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

                // Store reference in gameState for pause functionality
                gameState.currentSound = musicPlayer;

                // PHILIP'S FEEDBACK #9: Fade in at start
                musicPlayer.fade(0, 0.6, 1500);  // Fade from 0 to 60% over 1.5 seconds (balanced with TTS)

                // Calculate when to start fade out (3 seconds before end)
                const fadeOutTime = CONFIG.PREVIEW_DURATION_MS - 3000;

                // Start fade out before stopping
                setTimeout(() => {
                    if (musicPlayer) {
                        // PHILIP'S FEEDBACK #9: Fade out at end
                        musicPlayer.fade(0.6, 0, 3000);  // Fade from 60% to 0 over 3 seconds
                    }
                }, fadeOutTime);

                // Stop after full duration
                setTimeout(() => {
                    if (musicPlayer) {
                        musicPlayer.stop();
                        console.log(`⏹ Preview stopped (${CONFIG.PREVIEW_DURATION_MS / 1000} seconds)`);

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
    // Clear setup flag to show modal again
    localStorage.removeItem('setupCompleted');

    // Show modal with current settings loaded
    const modal = document.getElementById('setupModal');
    if (modal) {
        modal.classList.remove('hidden');
        initializeSetupModal();
    }
}

/**
 * Reset game to start over
 */
function resetGame() {
    if (!confirm('⚠️ Reset game? This will clear all called songs and restart from the beginning.')) {
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

/**
 * Toggle the full song list visibility
 */
function toggleSongList() {
    const songListSection = document.getElementById('fullSongListSection');
    const isVisible = songListSection.style.display !== 'none';
    
    if (isVisible) {
        // Hide the list
        songListSection.style.display = 'none';
    } else {
        // Show the list and populate it
        songListSection.style.display = 'block';
        displayFullSongList();
        
        // Scroll to the list
        songListSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Display all songs that will be played tonight
 */
function displayFullSongList() {
    const fullSongList = document.getElementById('fullSongList');
    const totalSongsCount = document.getElementById('totalSongsCount');
    
    if (!gameState.pool || gameState.pool.length === 0) {
        fullSongList.innerHTML = '<p style="opacity: 0.6; text-align: center;">No songs loaded yet. Start a session first.</p>';
        return;
    }
    
    // Update total count
    totalSongsCount.textContent = gameState.pool.length;
    
    // Sort songs alphabetically by title for easy searching
    const sortedSongs = [...gameState.pool].sort((a, b) => 
        a.title.localeCompare(b.title)
    );
    
    // Generate HTML for all songs in list format
    fullSongList.innerHTML = sortedSongs.map((track, index) => {
        // Check if this song has been called already
        const isCalled = gameState.called.some(calledTrack => calledTrack.id === track.id);
        const calledClass = isCalled ? 'called' : '';
        
        return `
            <div class="song-list-item ${calledClass}" onclick="showSongDetails('${track.id}')">
                <div class="song-number">${index + 1}</div>
                <div class="song-info">
                    <div class="song-title">${track.title}</div>
                    <div class="song-artist">${track.artist}</div>
                </div>
                <div class="song-meta">
                    ${track.release_year ? `<span class="meta-badge">${track.release_year}</span>` : ''}
                    ${track.genre ? `<span class="meta-badge">${track.genre}</span>` : ''}
                </div>
                ${isCalled ? '<div class="called-badge">✓ Called</div>' : ''}
            </div>
        `;
    }).join('');
    
    console.log(`📜 Displayed ${sortedSongs.length} songs in full list`);
}

/**
 * Show detailed information about a song in a modal
 */
function showSongDetails(songId) {
    const song = gameState.pool.find(s => s.id === songId);
    if (!song) return;
    
    const isCalled = gameState.called.some(calledTrack => calledTrack.id === song.id);
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'song-detail-modal';
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
    
    modal.innerHTML = `
        <div class="song-detail-content">
            <button class="modal-close" onclick="this.closest('.song-detail-modal').remove()">✕</button>
            
            <div class="song-detail-header">
                <img src="${song.artwork_url || 'https://via.placeholder.com/200?text=🎵'}" 
                     alt="${song.title}"
                     class="song-detail-artwork"
                     onerror="this.src='https://via.placeholder.com/200?text=🎵'">
                
                <div class="song-detail-info">
                    <h2>${song.title}</h2>
                    <h3>${song.artist}</h3>
                    
                    <div class="song-detail-meta">
                        ${song.release_year ? `<div class="detail-item"><strong>Year:</strong> ${song.release_year}</div>` : ''}
                        ${song.genre ? `<div class="detail-item"><strong>Genre:</strong> ${song.genre}</div>` : ''}
                        ${song.duration_ms ? `<div class="detail-item"><strong>Duration:</strong> ${Math.floor(song.duration_ms / 60000)}:${String(Math.floor((song.duration_ms % 60000) / 1000)).padStart(2, '0')}</div>` : ''}
                        <div class="detail-item"><strong>Status:</strong> <span style="color: ${isCalled ? '#10b981' : '#6b7280'}">${isCalled ? '✓ Called' : 'Not called yet'}</span></div>
                    </div>
                    
                    ${song.preview_url ? `
                        <audio controls style="width: 100%; margin-top: 15px;">
                            <source src="${song.preview_url}" type="audio/mpeg">
                            Your browser does not support audio playback.
                        </audio>
                    ` : '<p style="color: #9ca3af; font-size: 14px; margin-top: 10px;">No preview available</p>'}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
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
    console.log('🎵 updateCurrentTrackDisplay called with track:', track);
    
    const container = document.getElementById('currentTrack');
    const artwork = document.getElementById('trackArtwork');
    const title = document.getElementById('trackTitle');
    const artist = document.getElementById('trackArtist');

    // Validate all required elements exist before updating
    if (!container || !artwork || !title || !artist) {
        console.warn('⚠️  Track display elements not yet loaded in DOM, skipping update');
        if (!container) console.log('   Missing: currentTrack container');
        if (!artwork) console.log('   Missing: trackArtwork element');
        if (!title) console.log('   Missing: trackTitle element');
        if (!artist) console.log('   Missing: trackArtist element');
        return;
    }

    console.log('✅ All DOM elements found, updating display...');
    container.style.display = 'flex';
    
    if (artwork) {
        artwork.src = track.artwork_url || '';
        artwork.alt = `${track.title} artwork`;
        console.log(`   Artwork: ${track.artwork_url ? 'Set' : 'None'}`);
    }
    
    if (title) {
        title.textContent = track.title;
        console.log(`   Title: ${track.title}`);
    }
    
    if (artist) {
        artist.textContent = track.artist;
        console.log(`   Artist: ${track.artist}`);
    }
    
    console.log('✅ Display updated successfully');
}

/**
 * Update called songs list
 */
function updateCalledList() {
    const listEl = document.getElementById('calledList');

    if (!listEl) {
        console.warn('⚠️ calledList element not found in DOM');
        return;
    }

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
    // If game hasn't started and we're loading old session data, use calculated optimal value
    const numPlayers = parseInt(localStorage.getItem('numPlayers')) || 25;
    let totalSongs;
    
    if (gameState.called.length === 0 && gameState.pool.length > 0) {
        // Game not started yet - show optimal calculated songs instead of old pool size
        totalSongs = calculateOptimalSongs(numPlayers);
    } else {
        // Game in progress - show actual pool size
        totalSongs = gameState.called.length + gameState.remaining.length;
    }
    
    const estimatedMinutes = estimateGameDuration(totalSongs);

    // Update the stats counters
    const calledCount = document.getElementById('calledCount');
    const remainingCount = document.getElementById('remainingCount');
    const estimatedSongsEl = document.getElementById('estimatedSongs');

    if (calledCount) {
        calledCount.textContent = gameState.called.length;
    }
    
    if (remainingCount) {
        // Show calculated optimal songs if game hasn't started
        if (gameState.called.length === 0) {
            remainingCount.textContent = totalSongs;
        } else {
            remainingCount.textContent = gameState.remaining.length;
        }
    }

    // Update the top estimation text to show actual game total
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
document.addEventListener('DOMContentLoaded', function () {
    const numPlayersInput = document.getElementById('numPlayers');
    if (numPlayersInput) {
        numPlayersInput.addEventListener('input', async function () {
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
    // Get values from localStorage (set during setup)
    const venueName = localStorage.getItem('venueName') || document.getElementById('venueName').value.trim();
    const numPlayers = parseInt(localStorage.getItem('numPlayers')) || parseInt(document.getElementById('numPlayers').value) || 25;

    if (!venueName) {
        alert('Please complete setup first!');
        return;
    }
    
    console.log('📋 Generating cards with:', { venueName, numPlayers });

    // Calculate optimal songs
    const optimalSongs = calculateOptimalSongs(numPlayers);
    const estimatedMinutes = estimateGameDuration(optimalSongs);

    // Show loading state
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '⏳ Starting generation...';
    btn.disabled = true;

    // Open new window immediately (before async request) to avoid popup blocker
    // This window will be updated with the PDF URL when ready
    const pdfWindow = window.open('', '_blank');
    if (pdfWindow) {
        pdfWindow.document.write(`
            <html>
                <head>
                    <title>Generating Bingo Cards...</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }
                        .container {
                            text-align: center;
                        }
                        .spinner {
                            border: 8px solid rgba(255,255,255,0.3);
                            border-top: 8px solid white;
                            border-radius: 50%;
                            width: 60px;
                            height: 60px;
                            animation: spin 1s linear infinite;
                            margin: 0 auto 20px;
                        }
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                        h1 { font-size: 24px; margin-bottom: 10px; }
                        p { font-size: 16px; opacity: 0.9; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="spinner"></div>
                        <h1>🎵 Generating Your Bingo Cards...</h1>
                        <p>Please wait, this will take about 30-40 seconds</p>
                    </div>
                </body>
            </html>
        `);
    }

    try {
        // Get branding data from localStorage
        let pubLogo = localStorage.getItem('pubLogo') || '';

        console.log('📋 Preparing to generate cards (ASYNC MODE)...');
        console.log('   Venue:', venueName);
        console.log('🔍 [DEBUG] Players from localStorage:', localStorage.getItem('numPlayers'));
        console.log('🔍 [DEBUG] numPlayers variable type:', typeof numPlayers);
        console.log('🔍 [DEBUG] numPlayers variable value:', numPlayers);
        console.log('   Players (final):', numPlayers);
        console.log('   Pub Logo (stored):', pubLogo ? `${pubLogo.substring(0, 100)}...` : 'None');

        // If pubLogo is a relative path, convert to full URL
        // Skip conversion for data URIs and full URLs
        if (pubLogo && !pubLogo.startsWith('http') && !pubLogo.startsWith('data:')) {
            pubLogo = `${CONFIG.API_URL}${pubLogo}`;
            console.log('   Pub Logo (converted):', pubLogo);
        } else if (pubLogo) {
            console.log('   Pub Logo: Using as-is (data URI or full URL)');
        }

        const socialMedia = localStorage.getItem('socialMedia') || '';
        const includeQR = localStorage.getItem('includeQR') === 'true';

        // Get prizes
        const prize4Corners = localStorage.getItem('prize4Corners') || '';
        const prizeFirstLine = localStorage.getItem('prizeFirstLine') || '';
        const prizeFullHouse = localStorage.getItem('prizeFullHouse') || '';

        console.log('   Social Media:', socialMedia);
        console.log('   Include QR:', includeQR);
        console.log('   Prizes:', { prize4Corners, prizeFirstLine, prizeFullHouse });
        console.log('📤 Sending async request to backend...');

        // Get voice_id and decades from localStorage
        const voiceId = localStorage.getItem('voiceId') || '21m00Tcm4TlvDq8ikWAM';
        const selectedDecades = JSON.parse(localStorage.getItem('selectedDecades') || '[]');
        console.log('   Voice ID:', voiceId);
        console.log('   Selected Decades:', selectedDecades);

        // Check if we have an existing session_id (from URL param when session was loaded)
        const existingSessionId = localStorage.getItem('currentSessionId');
        if (existingSessionId) {
            console.log('🔗 Using existing session_id:', existingSessionId);
            console.log('   This will update the existing BingoSession in database');
        } else {
            console.log('ℹ️  No existing session_id - backend will create new BingoSession');
        }

        // Use new async endpoint
        const requestBody = {
            venue_name: venueName,
            num_players: numPlayers,
            optimal_songs: optimalSongs,
            pub_logo: pubLogo,
            social_media: socialMedia,
            include_qr: includeQR,
            prize_4corners: prize4Corners,
            prize_first_line: prizeFirstLine,
            prize_full_house: prizeFullHouse,
            voice_id: voiceId,
            decades: selectedDecades,
            session_id: existingSessionId
        };
        
        console.log('📦 [DEBUG] Request body BEFORE stringify:', requestBody);
        console.log('📦 [DEBUG] num_players in body:', requestBody.num_players, 'type:', typeof requestBody.num_players);
        
        const jsonString = JSON.stringify(requestBody);
        console.log('📦 [DEBUG] JSON string being sent:', jsonString);
        
        const response = await fetch(`${CONFIG.API_URL}/api/generate-cards-async`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: jsonString
        });


        console.log('📨 Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Backend error:', errorText);
            throw new Error('Failed to start card generation');
        }

        const result = await response.json();
        console.log('✅ Task result:', result);

        // *** HANDLE CACHED RESPONSE (immediate completion) ***
        if (result.status === 'completed' && result.cached) {
            console.log('⚡ CACHED PDF - Instant download!');
            
            // Save session_id if provided
            if (result.session_id) {
                localStorage.setItem('currentSessionId', result.session_id);
                console.log('🔑 Session ID saved (cached):', result.session_id);
            }
            
            // 🔄 Reload song pool (in case session was created without cards before)
            console.log('🔄 Reloading song pool (cached PDF)...');
            loadSongPool().then(() => {
                console.log('✅ Song pool reloaded from cache!');
                updateStats();
            }).catch(err => {
                console.error('⚠️  Failed to reload song pool:', err);
            });
            
            // Show success immediately
            btn.textContent = '⚡ Downloaded (cached)!';
            btn.style.background = 'linear-gradient(135deg, #38ef7d 0%, #11998e 100%)';
            
            // Redirect opened window to PDF
            const downloadUrl = result.pdf_url || result.download_url;
            if (pdfWindow && downloadUrl) {
                if (downloadUrl.startsWith('http://') || downloadUrl.startsWith('https://')) {
                    pdfWindow.location.href = downloadUrl;
                } else {
                    const timestamp = new Date().getTime();
                    pdfWindow.location.href = `${CONFIG.API_URL}${downloadUrl}?t=${timestamp}`;
                }
            } else if (!downloadUrl) {
                if (pdfWindow) pdfWindow.close();
                console.error('❌ No PDF URL in cached result:', result);
                throw new Error('No PDF URL in cached response');
            }
            
            // Reset button after 3 seconds
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.disabled = false;
            }, 3000);
            
            return; // Exit early, no need to poll
        }

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

                    // Save session data to localStorage if provided
                    if (status.result.session_data) {
                        localStorage.setItem('currentSessionData', JSON.stringify(status.result.session_data));
                        console.log('💾 Session data saved to localStorage');
                    }
                    
                    // Save session_id to localStorage for loading song pool later
                    if (status.result.session_id) {
                        localStorage.setItem('currentSessionId', status.result.session_id);
                        console.log('🔑 Session ID saved to localStorage:', status.result.session_id);
                    }

                    // 🔄 Reload song pool from database now that cards are generated
                    console.log('🔄 Reloading song pool after card generation...');
                    console.log(`   Session ID for reload: ${status.result.session_id}`);
                    loadSongPool().then(() => {
                        console.log('✅ Song pool reloaded - game ready to play!');
                        console.log(`   Songs loaded: ${gameState.remaining.length}`);
                        console.log(`   Pool size: ${gameState.pool.length}`);
                        updateStats();
                    }).catch(err => {
                        console.error('⚠️  Failed to reload song pool:', err);
                        console.error('   Error details:', err.message);
                    });

                    // Show brief success message in button (no alert modal)
                    btn.textContent = '✅ Downloaded!';
                    btn.style.background = 'linear-gradient(135deg, #38ef7d 0%, #11998e 100%)';
                    
                    // Reset button after 3 seconds
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.background = '';
                        btn.disabled = false;
                    }, 3000);

                    // Check if it's a cached result
                    const isCached = status.result.cached || false;
                    
                    // Log details to console for debugging
                    console.log(`📄 Cards: ${status.result.num_cards || 'N/A'}`);
                    console.log(`💾 File size: ${status.result.file_size_mb || 'N/A'} MB`);
                    console.log(`⏱️  Generation time: ${status.result.generation_time || status.elapsed_time} s`);
                    console.log(`📦 Cached: ${isCached ? 'Yes (instant)' : 'No (fresh generation)'}`);

                    // Redirect opened window to PDF
                    const downloadUrl = status.result.pdf_url || status.result.download_url;
                    console.log('🔗 Download URL:', downloadUrl);
                    
                    if (pdfWindow && downloadUrl) {
                        if (downloadUrl.startsWith('http://') || downloadUrl.startsWith('https://')) {
                            console.log('✅ Using full URL from GCS');
                            pdfWindow.location.href = downloadUrl;
                        } else {
                            console.log('✅ Using relative path');
                            const timestamp = new Date().getTime();
                            pdfWindow.location.href = `${CONFIG.API_URL}${downloadUrl}?t=${timestamp}`;
                        }
                        console.log('✅ PDF window redirected to:', downloadUrl);
                    } else if (!downloadUrl) {
                        if (pdfWindow) pdfWindow.close();
                        console.error('❌ No PDF URL found in result:', status.result);
                        throw new Error('No PDF URL in response');
                    }
                    
                    // Show optional notification (non-blocking)
                    if (isCached) {
                        console.log('⚡ Using cached PDF - instant download!');
                    }
                } else if (status.status === 'failed') {
                    // Failed
                    console.error('❌ Generation failed:', status.error);

                    btn.textContent = originalText;
                    btn.disabled = false;

                    // Close the PDF window
                    if (pdfWindow) pdfWindow.close();

                    alert(`❌ Card generation failed:\n\n${status.error}\n\nPlease try again or contact support.`);

                } else if (attempts >= maxAttempts) {
                    // Timeout
                    console.error('⏱️ Polling timeout');

                    btn.textContent = originalText;
                    btn.disabled = false;

                    // Close the PDF window
                    if (pdfWindow) pdfWindow.close();

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
                    if (pdfWindow) pdfWindow.close();
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
        if (pdfWindow) pdfWindow.close();
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

    switch (platform) {
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

    switch (platform) {
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

// ============================================================================
// JINGLE PLAYLIST FUNCTIONALITY
// ============================================================================

let jinglePlaylist = {
    jingles: [],
    enabled: false,
    interval: 3,
    currentIndex: 0
};

/**
 * Load jingle playlist settings from backend
 */
async function loadJinglePlaylist() {
    try {
        const apiUrl = CONFIG.API_URL;
        const url = apiUrl.endsWith('/api') ? `${apiUrl}/playlist` : `${apiUrl}/api/playlist`;

        const response = await fetch(url);
        const playlist = await response.json();

        jinglePlaylist = { ...playlist, currentIndex: 0 };

        if (playlist.enabled && playlist.jingles.length > 0) {
            console.log(`🎵 Jingle playlist loaded: ${playlist.jingles.length} jingles, play every ${playlist.interval} rounds`);
        }
    } catch (error) {
        console.error('Error loading jingle playlist:', error);
    }
}

/**
 * Fetch currently active jingle schedules from backend
 * Backend evaluates: date range, time period, day of week, enabled status
 * Returns schedules sorted by priority (highest first)
 */
async function fetchActiveJingles() {
    try {
        const apiUrl = CONFIG.API_URL;
        let url = apiUrl.endsWith('/api')
            ? `${apiUrl}/jingle-schedules/active`
            : `${apiUrl}/api/jingle-schedules/active`;

        // Add venue filter
        const venueName = gameState.venueName;
        if (venueName && venueName !== 'this venue') {
            url += `?venue_name=${encodeURIComponent(venueName)}`;
        }

        const response = await fetch(url);

        if (!response.ok) {
            console.error('Error fetching active jingles:', response.status);
            return [];
        }

        const data = await response.json();
        return data.active_jingles || [];
    } catch (error) {
        console.error('Error fetching active jingles:', error);
        return [];
    }
}

/**
 * Track jingle play for analytics (optional)
 */
async function trackJinglePlay(scheduleId, roundNumber) {
    try {
        const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL;
        const url = apiUrl.endsWith('/api')
            ? `${apiUrl}/jingle-schedules/${scheduleId}/play`
            : `${apiUrl}/api/jingle-schedules/${scheduleId}/play`;

        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ round_number: roundNumber })
        });
    } catch (error) {
        console.error('Error tracking jingle play:', error);
    }
}

/**
 * Check if a jingle should play and play it
 */
async function checkAndPlayJingle() {
    // Fetch active schedules from backend
    const activeSchedules = await fetchActiveJingles();

    if (activeSchedules.length === 0) {
        console.log('No active jingle schedules');
        return;
    }

    const songsPlayed = gameState.called.length;

    // Check each schedule to see if it should play
    for (const schedule of activeSchedules) {
        const shouldPlay = (songsPlayed > 0 && songsPlayed % schedule.interval === 0);

        if (shouldPlay) {
            console.log(`🎵 Playing scheduled jingle: ${schedule.jingle_name}`);

            updateStatus('🎵 Playing promotional jingle...', true);

            try {
                await playJingleAudio(schedule.jingle_filename);

                // Track play event (optional)
                await trackJinglePlay(schedule.id, songsPlayed);

                await new Promise(resolve => setTimeout(resolve, 500));

                // Only play ONE jingle per round (highest priority wins)
                break;
            } catch (error) {
                console.error('Error playing jingle:', error);
            }
        }
    }
}

/**
 * Play a jingle audio file
 */
function playJingleAudio(filename) {
    return new Promise((resolve, reject) => {
        const apiUrl = CONFIG.API_URL;
        const url = apiUrl.endsWith('/api')
            ? `${apiUrl}/jingles/${filename}`
            : `${apiUrl}/api/jingles/${filename}`;

        console.log(`🎵 Playing jingle: ${filename}`);

        const audio = new Audio(url);

        audio.onended = () => {
            console.log('✅ Jingle finished');
            resolve();
        };

        audio.onerror = (error) => {
            console.error('Error playing jingle:', error);
            reject(error);
        };

        audio.play().catch(reject);
    });
}

// Load playlist on initialization
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
        loadJinglePlaylist();
    });
}

/**
 * Update bingo session status (pending -> active -> completed)
 */
async function updateSessionStatus(newStatus) {
    const sessionId = new URLSearchParams(window.location.search).get('session');
    if (!sessionId) return;
    
    try {
        console.log(`📊 Updating session status to: ${newStatus}`);
        const response = await fetch(`${CONFIG.API_URL}/api/bingo/session/${sessionId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            console.log(`✅ Session status updated to ${newStatus}`);
        } else {
            console.warn(`⚠️ Failed to update session status: ${response.status}`);
        }
    } catch (error) {
        console.error('❌ Error updating session status:', error);
    }
}
