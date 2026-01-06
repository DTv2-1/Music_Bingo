/**
 * config.js - Frontend Configuration
 * Loads environment variables for the game
 */

// Load configuration from .env file
// In production, these would be set by your build system or server
const CONFIG = {
    // ElevenLabs API (read from environment or .env file)
    ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY || '',
    VOICE_ID: process.env.ELEVENLABS_VOICE_ID || '21m00Tcm4TlvDq8ikWAM',
    
    // Game settings
    PREVIEW_DURATION_MS: parseInt(process.env.PREVIEW_DURATION_MS || '5000'),
    AUTO_NEXT_DELAY_MS: parseInt(process.env.AUTO_NEXT_DELAY_MS || '15000'),
    
    // Data files
    POOL_FILE: '../data/pool.json',
    ANNOUNCEMENTS_FILE: '../data/announcements.json',
    
    // Debug
    DEBUG_MODE: process.env.DEBUG_MODE === 'true'
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
