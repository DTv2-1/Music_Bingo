/**
 * env-loader.js - Simple .env file loader for frontend
 * Loads .env file and makes variables available to the app
 */

async function loadEnv() {
    try {
        const response = await fetch('.env');
        if (!response.ok) {
            console.warn('⚠️ .env file not found. Using default configuration.');
            return;
        }
        
        const text = await response.text();
        const lines = text.split('\n');
        
        lines.forEach(line => {
            // Skip comments and empty lines
            if (line.trim().startsWith('#') || !line.trim()) return;
            
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
                const value = valueParts.join('=').trim();
                
                // Store in CONFIG object
                if (window.CONFIG && key.trim() in window.CONFIG) {
                    const cleanValue = value.replace(/^["']|["']$/g, ''); // Remove quotes
                    
                    // Parse numbers
                    if (!isNaN(cleanValue) && cleanValue !== '') {
                        window.CONFIG[key.trim()] = parseInt(cleanValue);
                    } else if (cleanValue === 'true' || cleanValue === 'false') {
                        window.CONFIG[key.trim()] = cleanValue === 'true';
                    } else {
                        window.CONFIG[key.trim()] = cleanValue;
                    }
                    
                    console.log(`✓ Loaded ${key.trim()} from .env`);
                }
            }
        });
        
        console.log('✓ Environment variables loaded');
    } catch (error) {
        console.warn('⚠️ Could not load .env file:', error.message);
        console.log('Using default configuration');
    }
}

// Auto-load on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadEnv);
} else {
    loadEnv();
}
