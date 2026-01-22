/**
 * config.js - Frontend Configuration
 * Loads environment variables for the game
 */

// Detect backend URL
const BACKEND_URL = (() => {
    // Check if already set by server-side injection
    if (window.BACKEND_URL) {
        const frontendUrl = `${window.location.protocol}//${window.location.host}`;
        // If BACKEND_URL is equal to the URL of the frontend, use relative paths
        if (window.BACKEND_URL === frontendUrl || window.BACKEND_URL === window.location.origin) {
            return '';
        }
        return window.BACKEND_URL;
    }

    // Local development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8001';
    }

    // Production default fallback - use empty string for relative paths
    return '';
})();

// Set window.BACKEND_URL for use across the app
window.BACKEND_URL = BACKEND_URL;

// Load configuration from .env file
// In production, these would be set by your build system or server
const CONFIG = {
    // Backend API URL
    API_URL: BACKEND_URL,
    BACKEND_URL: BACKEND_URL,

    // ElevenLabs API (not used in frontend, kept for compatibility)
    ELEVENLABS_API_KEY: '',
    VOICE_ID: '21m00Tcm4TlvDq8ikWAM',

    // Game settings
    PREVIEW_DURATION_MS: 15000,  // 15 seconds of song preview
    AUTO_NEXT_DELAY_MS: 15000,   // 15 seconds between songs

    // Audio settings
    BACKGROUND_MUSIC_VOLUME: 0.15,  // Background music volume (15%)
    TTS_VOLUME: 1.0,  // TTS announcement volume (100%)
    BACKGROUND_MUSIC_URL: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',

    // Data files
    POOL_FILE: '../data/pool.json',
    ANNOUNCEMENTS_FILE: '../data/announcements.json',

    // Debug
    DEBUG_MODE: false
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
