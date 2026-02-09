/*
 * jingle.js - Jingle Generator Logic
 * Creates professional ad jingles with TTS + AI music
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let currentStep = 1;
let jingleData = {
    text: '',
    voiceId: '21m00Tcm4TlvDq8ikWAM', // Default British Male
    musicPrompt: 'upbeat energetic electric guitar rock instrumental, clean, no vocals, no ambient sounds',
    duration: 10,
    voiceSettings: {
        stability: 0.65,           // Higher for consistency in noisy environments
        similarity_boost: 0.90,    // Max clarity for pub settings
        style: 0.40,               // Less dramatic, more clear
        use_speaker_boost: true    // Always on for pubs
    }
};

let pollingInterval = null;
let previewAudio = null; // For voice preview

// Voice Settings Presets for Different Environments
const VOICE_PRESETS = {
    pub: {
        name: '🍻 Pub/Bar (Optimized)',
        settings: {
            stability: 0.65,
            similarity_boost: 0.90,
            style: 0.40,
            use_speaker_boost: true
        },
        description: 'Maximum clarity for noisy environments'
    },
    energetic: {
        name: '🔥 Energetic/Party',
        settings: {
            stability: 0.45,
            similarity_boost: 0.80,
            style: 0.70,
            use_speaker_boost: true
        },
        description: 'Dynamic and exciting for events'
    },
    professional: {
        name: '🎼 Professional/Clear',
        settings: {
            stability: 0.75,
            similarity_boost: 0.85,
            style: 0.30,
            use_speaker_boost: true
        },
        description: 'Crystal clear for announcements'
    },
    balanced: {
        name: '⚖️ Balanced',
        settings: {
            stability: 0.50,
            similarity_boost: 0.75,
            style: 0.50,
            use_speaker_boost: true
        },
        description: 'Good for most situations'
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎵 Jingle Generator initialized');

    initializeTemplates();
    initializeVoiceSelection();
    initializeMusicSelection();
    initializeTextInput();
});

// ============================================================================
// WIZARD NAVIGATION
// ============================================================================

function nextStep() {
    // Validate current step
    if (currentStep === 1 && !validateText()) {
        return;
    }

    if (currentStep >= 4) return;

    // Hide current step
    document.getElementById(`step${currentStep}`).classList.add('hidden');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.remove('active');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.add('completed');

    // Show next step
    currentStep++;
    document.getElementById(`step${currentStep}`).classList.remove('hidden');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.add('active');

    // Update summary if on final step
    if (currentStep === 4) {
        updateSummary();
    }
}

function previousStep() {
    if (currentStep <= 1) return;

    // Hide current step
    document.getElementById(`step${currentStep}`).classList.add('hidden');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.remove('active');

    // Show previous step
    currentStep--;
    document.getElementById(`step${currentStep}`).classList.remove('hidden');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.remove('completed');
    document.querySelector(`.step[data-step="${currentStep}"]`).classList.add('active');
}

function resetWizard() {
    // Reset state
    currentStep = 1;
    jingleData.text = '';
    document.getElementById('jingleText').value = '';

    // Hide all steps except first
    for (let i = 2; i <= 4; i++) {
        document.getElementById(`step${i}`).classList.add('hidden');
        document.querySelector(`.step[data-step="${i}"]`).classList.remove('active', 'completed');
    }

    // Show first step
    document.getElementById('step1').classList.remove('hidden');
    document.querySelector('.step[data-step="1"]').classList.add('active');

    // Reset UI elements
    document.getElementById('progressSection').classList.remove('active');
    document.getElementById('audioPlayer').classList.add('hidden');
    document.getElementById('generateButtons').style.display = 'flex';
    document.getElementById('errorMessage').classList.add('hidden');

    // Scroll wizard to top
    const wizardColumn = document.querySelector('.wizard-column');
    if (wizardColumn) wizardColumn.scrollTop = 0;

    updateCharCount();

    // Show success message
    showQuickMessage('✅ Ready to create another jingle!');
}

function showQuickMessage(message) {
    // Create temporary message
    const msgDiv = document.createElement('div');
    msgDiv.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: #4CAF50;
        color: white;
        padding: 15px 30px;
        border-radius: 10px;
        font-weight: 600;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    msgDiv.textContent = message;
    document.body.appendChild(msgDiv);

    setTimeout(() => {
        msgDiv.style.opacity = '0';
        msgDiv.style.transition = 'opacity 0.3s';
        setTimeout(() => msgDiv.remove(), 300);
    }, 2000);
}

// ============================================================================
// TEXT INPUT
// ============================================================================

function initializeTextInput() {
    const textarea = document.getElementById('jingleText');

    textarea.addEventListener('input', () => {
        jingleData.text = textarea.value;
        updateCharCount();
    });
}

function updateCharCount() {
    const textarea = document.getElementById('jingleText');
    const counter = document.getElementById('charCount');

    // Count WORDS, not characters
    const words = textarea.value.trim().split(/\s+/).filter(word => word.length > 0).length;
    const count = textarea.value.length;

    counter.textContent = `${count} chars / ${words} words`;
    counter.parentElement.classList.remove('warning', 'error');

    // Show warning at 150 words (~75% of 200)
    if (words > 150) {
        counter.parentElement.classList.add('warning');
    }
    // Show error at 200 words (max limit)
    if (words > 200) {
        counter.parentElement.classList.add('error');
    }
}

function validateText() {
    const text = jingleData.text.trim();

    if (text.length === 0) {
        alert('Please enter some text for your jingle!');
        return false;
    }

    if (text.length < 10) {
        alert('Text too short! Please enter at least 10 characters.');
        return false;
    }

    return true;
}

function initializeTemplates() {
    loadSavedTemplates();
}

function useQuickTemplate(text) {
    document.getElementById('jingleText').value = text;
    jingleData.text = text;
    updateCharCount();
}

// ============================================================================
// TEMPLATE SYSTEM
// ============================================================================

function loadSavedTemplates() {
    const templates = JSON.parse(localStorage.getItem('jingleTemplates') || '[]');
    const selector = document.getElementById('templateSelector');

    // Clear existing options except first
    selector.innerHTML = '<option value="">-- Select a template or start fresh --</option>';

    // Add saved templates
    templates.forEach((template, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${template.name} (${template.voiceName} + ${template.musicStyle})`;
        selector.appendChild(option);
    });
}

function loadTemplate() {
    const selector = document.getElementById('templateSelector');
    const index = selector.value;

    if (index === '') return;

    const templates = JSON.parse(localStorage.getItem('jingleTemplates') || '[]');
    const template = templates[index];

    if (!template) return;

    // Load template data
    document.getElementById('jingleText').value = template.text || '';
    jingleData.text = template.text || '';
    jingleData.voiceId = template.voiceId;
    jingleData.musicPrompt = template.musicPrompt;

    updateCharCount();

    showQuickMessage(`✅ Template "${template.name}" loaded!`);
}

function showSaveTemplateDialog() {
    // Validate we have data to save
    if (!jingleData.text || !jingleData.voiceId || !jingleData.musicPrompt) {
        alert('Please complete at least steps 1-3 before saving a template');
        return;
    }

    // Create dialog
    const overlay = document.createElement('div');
    overlay.className = 'template-dialog-overlay';
    overlay.innerHTML = `
        <div class="template-dialog">
            <h3>💾 Save Jingle Template</h3>
            <p style="color: #666; margin-bottom: 15px;">
                Give your template a name so you can reuse this configuration later
            </p>
            <input type="text" id="templateName" placeholder="e.g., Happy Hour - George - Upbeat" autofocus>
            <div style="font-size: 0.9em; color: #666; margin-top: 10px;">
                <strong>Saved:</strong><br>
                Text: ${jingleData.text.substring(0, 40)}...<br>
                Voice: ${getVoiceName(jingleData.voiceId)}<br>
                Music: ${getMusicStyleName(jingleData.musicPrompt)}
            </div>
            <div class="template-dialog-buttons">
                <button class="btn btn-secondary" onclick="closeSaveTemplateDialog()">Cancel</button>
                <button class="btn btn-primary" onclick="saveTemplate()">💾 Save Template</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Focus input
    setTimeout(() => {
        document.getElementById('templateName').focus();
        document.getElementById('templateName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') saveTemplate();
        });
    }, 100);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeSaveTemplateDialog();
    });
}

function closeSaveTemplateDialog() {
    const overlay = document.querySelector('.template-dialog-overlay');
    if (overlay) overlay.remove();
}

function saveTemplate() {
    const nameInput = document.getElementById('templateName');
    const name = nameInput.value.trim();

    if (!name) {
        alert('Please enter a template name');
        nameInput.focus();
        return;
    }

    // Get templates
    const templates = JSON.parse(localStorage.getItem('jingleTemplates') || '[]');

    // Create new template
    const template = {
        name: name,
        text: jingleData.text,
        voiceId: jingleData.voiceId,
        voiceName: getVoiceName(jingleData.voiceId),
        musicPrompt: jingleData.musicPrompt,
        musicStyle: getMusicStyleName(jingleData.musicPrompt),
        created: new Date().toISOString()
    };

    // Add to templates
    templates.push(template);

    // Save to localStorage
    localStorage.setItem('jingleTemplates', JSON.stringify(templates));

    // Close dialog
    closeSaveTemplateDialog();

    // Reload template selector
    loadSavedTemplates();

    // Show success
    showQuickMessage(`✅ Template "${name}" saved!`);
}

function getVoiceName(voiceId) {
    const voices = {
        '21m00Tcm4TlvDq8ikWAM': 'British Male',
        'EXAVITQu4vr4xnSDxMaL': 'British Female',
        'pNInz6obpgDQGcFmaJgB': 'Energetic',
        'JBFqnCBsd6RMkjVDRZzb': 'George',
        'XB0fDUnXU5powFXDhCwa': 'Charlotte',
        'N2lVS1w4EtoT3dr4eOWO': 'Callum',
        'IKne3meq5aSn9XLyUdCD': 'Charlie',
        'cgSgspJ2msm6clMCkdW9': 'Jessica'
    };
    return voices[voiceId] || 'Unknown';
}

function getMusicStyleName(prompt) {
    // PUB/ENTERTAINMENT STYLES
    if (prompt.includes('electric guitar rock')) return 'Pub Rock';
    if (prompt.includes('jazz piano')) return 'Jazz Piano';
    if (prompt.includes('electronic dance')) return 'Electronic';
    if (prompt.includes('irish folk')) return 'Irish Folk';
    if (prompt.includes('funky disco')) return 'Funky';

    // COMMERCIAL/ADVERTISING STYLES
    if (prompt.includes('commercial pop')) return 'Commercial Pop';
    if (prompt.includes('corporate') && prompt.includes('motivational')) return 'Corporate';
    if (prompt.includes('ukulele') && prompt.includes('whistling')) return 'Happy Whistling';
    if (prompt.includes('retro') && prompt.includes('80s')) return 'Retro 80s';

    // VERSATILE/EVENT STYLES
    if (prompt.includes('acoustic folk')) return 'Acoustic';
    if (prompt.includes('rock and roll')) return 'Rock & Roll';
    if (prompt.includes('chill lounge')) return 'Chill Lounge';

    return 'Custom';
}

// ============================================================================
// VOICE SELECTION
// ============================================================================

let currentTestAudio = null;

function initializeVoiceSelection() {
    const voiceCards = document.querySelectorAll('.voice-card');

    voiceCards.forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't select if clicking the test button
            if (e.target.classList.contains('test-voice-btn')) {
                return;
            }

            // Remove selected from all cards
            voiceCards.forEach(c => c.classList.remove('selected'));

            // Add selected to clicked card
            card.classList.add('selected');

            // Update state
            jingleData.voiceId = card.getAttribute('data-voice');
            console.log('Voice selected:', jingleData.voiceId);
        });
    });
}

async function testVoice(event, voiceId, voiceName) {
    event.stopPropagation(); // Prevent immediate card selection

    const btn = event.target;
    const voiceCard = btn.closest('.voice-card');

    // Stop any currently playing audio
    if (currentTestAudio && !currentTestAudio.paused) {
        currentTestAudio.pause();
        currentTestAudio = null;
        // Reset all buttons
        document.querySelectorAll('.test-voice-btn').forEach(b => {
            b.textContent = '🔊 Test Voice';
            b.classList.remove('playing');
            b.disabled = false;
        });
        return;
    }

    try {
        // Select this voice when test button is clicked
        document.querySelectorAll('.voice-card').forEach(c => c.classList.remove('selected'));
        voiceCard.classList.add('selected');
        jingleData.voiceId = voiceId;
        console.log('Voice selected via test:', voiceId);

        // Disable all test buttons
        document.querySelectorAll('.test-voice-btn').forEach(b => b.disabled = true);

        btn.textContent = '⏳ Loading...';
        btn.classList.add('playing');

        // Generate sample text
        const sampleText = `Hello! This is the ${voiceName} voice. Perfect for your pub jingles and promotions.`;

        // Call TTS API
        const apiUrl = CONFIG.API_URL;
        const endpoint = apiUrl.includes('/api') ? `${apiUrl}/generate-tts` : `${apiUrl}/api/generate-tts`;

        const response = await fetch(endpoint, {
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
            throw new Error('Failed to generate voice sample');
        }

        // Get audio blob
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        // Play audio
        currentTestAudio = new Audio(audioUrl);
        btn.textContent = '⏸️ Stop';

        currentTestAudio.play();

        currentTestAudio.addEventListener('ended', () => {
            btn.textContent = '🔊 Test Voice';
            btn.classList.remove('playing');
            document.querySelectorAll('.test-voice-btn').forEach(b => b.disabled = false);
            URL.revokeObjectURL(audioUrl);
            currentTestAudio = null;
        });

        currentTestAudio.addEventListener('error', () => {
            btn.textContent = '🔊 Test Voice';
            btn.classList.remove('playing');
            document.querySelectorAll('.test-voice-btn').forEach(b => b.disabled = false);
            alert('Error playing audio sample');
            currentTestAudio = null;
        });

        // Enable other buttons
        document.querySelectorAll('.test-voice-btn').forEach(b => {
            if (b !== btn) b.disabled = false;
        });

    } catch (error) {
        console.error('Error testing voice:', error);
        btn.textContent = '🔊 Test Voice';
        btn.classList.remove('playing');
        document.querySelectorAll('.test-voice-btn').forEach(b => b.disabled = false);
        alert('Failed to generate voice sample. Please check your API key.');
    }
}

// ============================================================================
// MUSIC SELECTION
// ============================================================================

let currentMusicPreview = null;

function initializeMusicSelection() {
    const musicStyles = document.querySelectorAll('.music-style');

    musicStyles.forEach(style => {
        style.addEventListener('click', (e) => {
            // Don't select if clicking the preview button
            if (e.target.classList.contains('preview-music-btn')) {
                return;
            }

            // Remove selected from all styles
            musicStyles.forEach(s => s.classList.remove('selected'));

            // Add selected to clicked style
            style.classList.add('selected');

            // Update state
            jingleData.musicPrompt = style.getAttribute('data-prompt');
            console.log('Music style selected:', jingleData.musicPrompt);
        });
    });
}

async function previewMusic(event, musicPrompt, musicName) {
    event.stopPropagation(); // Prevent immediate style selection

    const btn = event.target;
    const styleCard = btn.closest('.music-style');

    // Stop any currently playing preview
    if (currentMusicPreview && !currentMusicPreview.paused) {
        currentMusicPreview.pause();
        currentMusicPreview = null;
        // Reset all buttons
        document.querySelectorAll('.preview-music-btn').forEach(b => {
            b.textContent = '🔊 Preview';
            b.classList.remove('playing');
            b.disabled = false;
        });
        return;
    }

    try {
        // Select this music style when preview is clicked
        document.querySelectorAll('.music-style').forEach(s => s.classList.remove('selected'));
        styleCard.classList.add('selected');
        jingleData.musicPrompt = musicPrompt;
        console.log('Music style selected via preview:', musicPrompt);

        // Disable all preview buttons
        document.querySelectorAll('.preview-music-btn').forEach(b => b.disabled = true);

        btn.textContent = '⏳ Loading...';
        btn.classList.add('playing');

        console.log('Generating music preview for:', musicName);

        // Call Music Generation API
        const apiUrl = CONFIG.API_URL;
        const endpoint = apiUrl.includes('/api') ? `${apiUrl}/generate-music-preview` : `${apiUrl}/api/generate-music-preview`;

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                music_prompt: musicPrompt,
                duration: 5  // 5 second preview
            })
        });

        if (!response.ok) {
            throw new Error('Failed to generate music preview');
        }

        // Get audio blob
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        // Play audio
        currentMusicPreview = new Audio(audioUrl);
        btn.textContent = '⏸️ Stop';

        currentMusicPreview.play();

        currentMusicPreview.addEventListener('ended', () => {
            btn.textContent = '🔊 Preview';
            btn.classList.remove('playing');
            document.querySelectorAll('.preview-music-btn').forEach(b => b.disabled = false);
            URL.revokeObjectURL(audioUrl);
            currentMusicPreview = null;
        });

        currentMusicPreview.addEventListener('error', () => {
            btn.textContent = '🔊 Preview';
            btn.classList.remove('playing');
            document.querySelectorAll('.preview-music-btn').forEach(b => b.disabled = false);
            alert('Error playing music preview');
            currentMusicPreview = null;
        });

        // Enable other buttons
        document.querySelectorAll('.preview-music-btn').forEach(b => {
            if (b !== btn) b.disabled = false;
        });

    } catch (error) {
        console.error('Error previewing music:', error);
        btn.textContent = '🔊 Preview';
        btn.classList.remove('playing');
        document.querySelectorAll('.preview-music-btn').forEach(b => b.disabled = false);

        // Show user-friendly message
        alert('Music preview unavailable. This feature requires ElevenLabs Music API access. You can still select this style and generate your jingle!');
    }
}

// ============================================================================
// SUMMARY
// ============================================================================

function updateSummary() {
    const voiceName = document.querySelector('.voice-card.selected .voice-name').textContent;
    const musicName = document.querySelector('.music-style.selected').textContent.trim();

    document.getElementById('summaryText').textContent = jingleData.text;
    document.getElementById('summaryVoice').textContent = voiceName;
    document.getElementById('summaryMusic').textContent = musicName;
}

// ============================================================================
// JINGLE GENERATION
// ============================================================================

async function generateJingle() {
    console.log('🎬 Starting jingle generation...');
    console.log('Current jingleData:', jingleData);

    // Show progress section
    document.getElementById('progressSection').classList.add('active');
    document.getElementById('generateButtons').style.display = 'none';
    document.getElementById('errorMessage').classList.add('hidden');

    try {
        // Call API to start generation
        const apiUrl = CONFIG.API_URL;
        const endpoint = apiUrl.includes('/api') ? `${apiUrl}/generate-jingle` : `${apiUrl}/api/generate-jingle`;

        // Convert camelCase to snake_case for backend compatibility
        const payload = {
            text: jingleData.text,
            voice_id: jingleData.voiceId,
            music_prompt: jingleData.musicPrompt,
            voiceSettings: jingleData.voiceSettings
        };

        console.log('Sending payload:', payload);

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start jingle generation');
        }

        const result = await response.json();
        console.log('Task started:', result.task_id);

        // Start polling for status
        pollTaskStatus(result.task_id);

    } catch (error) {
        console.error('Error generating jingle:', error);
        showError(error.message);
        document.getElementById('generateButtons').style.display = 'flex';
        document.getElementById('progressSection').classList.remove('active');
    }
}

async function pollTaskStatus(taskId) {
    console.log('📊 Polling task status:', taskId);

    const apiUrl = window.BACKEND_URL || '';
    const endpoint = apiUrl.includes('/api') ? `${apiUrl}/jingle-tasks/${taskId}` : `${apiUrl}/api/jingle-tasks/${taskId}`;

    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(endpoint);

            if (!response.ok) {
                throw new Error('Failed to get task status');
            }

            const task = await response.json();
            console.log('Task status:', task.status, task.progress);

            // Update progress bar
            updateProgress(task.progress, task.current_step);

            if (task.status === 'completed') {
                clearInterval(pollingInterval);
                console.log('✅ Jingle generation completed!');
                showCompletedJingle(task.result);
            } else if (task.status === 'failed') {
                clearInterval(pollingInterval);
                throw new Error(task.error || 'Generation failed');
            }

        } catch (error) {
            clearInterval(pollingInterval);
            console.error('Polling error:', error);
            showError(error.message);
            document.getElementById('generateButtons').style.display = 'flex';
        }
    }, 2000); // Poll every 2 seconds
}

function updateProgress(percentage, step) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    progressBar.style.width = `${percentage}%`;
    progressBar.textContent = `${percentage}%`;

    const stepMessages = {
        'initializing': 'Initializing...',
        'generating_voice': 'Generating voice with AI...',
        'generating_music': 'Creating background music...',
        'mixing': 'Mixing audio tracks...',
        'finalizing': 'Finalizing your jingle...',
        'completed': 'Complete! 🎉'
    };

    progressText.textContent = stepMessages[step] || 'Processing...';
}

function showCompletedJingle(result) {
    console.log('Jingle result:', result);

    // Determine audio URL from result (supports both audio_url and filename)
    const apiUrl = window.BACKEND_URL || '';
    let audioUrl;

    if (result.audio_url) {
        audioUrl = result.audio_url.startsWith('http')
            ? result.audio_url
            : `${apiUrl}${result.audio_url}`;
    } else if (result.filename) {
        audioUrl = `${apiUrl}/api/jingles/${result.filename}`;
    } else {
        console.error('No audio_url or filename in result:', result);
        showError('No audio URL returned from server');
        return;
    }

    // Save current jingle filename for "Add to Playlist" button
    currentJingleFilename = result.filename || audioUrl.split('/').pop();

    // Hide progress, show player
    document.getElementById('progressSection').classList.remove('active');
    document.getElementById('audioPlayer').classList.remove('hidden');

    const audio = document.getElementById('jingleAudio');
    audio.src = audioUrl;

    // Setup download button
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.onclick = () => {
        window.open(audioUrl, '_blank');
    };

    // Auto-play
    audio.play().catch(err => {
        console.warn('Auto-play blocked:', err);
    });

    // Refresh jingles library
    setTimeout(() => loadJinglesLibrary(), 1000);
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');

    document.getElementById('progressSection').classList.remove('active');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

console.log('✅ Jingle.js loaded successfully');

// ============================================================================
// PLAYLIST MANAGEMENT
// ============================================================================

let playlistState = {
    jingles: [],
    enabled: false,
    interval: 3
};

let currentJingleFilename = null; // Store last generated jingle

// Load jingles library on page load
document.addEventListener('DOMContentLoaded', () => {
    loadJinglesLibrary();
    loadPlaylistSettings();
});

async function loadJinglesLibrary() {
    try {
        const apiUrl = CONFIG.API_URL;
        const url = apiUrl.endsWith('/api') ? `${apiUrl}/jingles` : `${apiUrl}/api/jingles`;

        const response = await fetch(url);
        const data = await response.json();
        const jingles = data.jingles || data; // Handle both {jingles: [...]} and [...]

        displayJingles(jingles);
    } catch (error) {
        console.error('Error loading jingles:', error);
        document.getElementById('jinglesList').innerHTML = `
            <div style="text-align: center; padding: 40px; color: #f44336;">
                Failed to load jingles
            </div>
        `;
    }
}

function displayJingles(jingles) {
    const container = document.getElementById('jinglesList');

    if (jingles.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                No jingles yet. Create your first one above! 👆
            </div>
        `;
        return;
    }

    container.innerHTML = jingles.map(jingle => {
        const inPlaylist = playlistState.jingles.includes(jingle.filename);
        const metadata = jingle.metadata || {};
        const created = new Date(jingle.created).toLocaleString();
        const sizeKB = (jingle.size / 1024).toFixed(1);

        return `
            <div class="jingle-item ${inPlaylist ? 'in-playlist' : ''}" data-filename="${jingle.filename}">
                <input type="checkbox" 
                       class="jingle-checkbox" 
                       ${inPlaylist ? 'checked' : ''}
                       onchange="toggleJingleInPlaylist('${jingle.filename}')">
                <div class="jingle-info">
                    <div class="jingle-title">
                        ${metadata.text ? metadata.text.substring(0, 50) + '...' : jingle.filename}
                    </div>
                    <div class="jingle-metadata">
                        Voice: ${metadata.voiceName || 'Unknown'} | 
                        Music: ${metadata.musicStyle || 'Unknown'} | 
                        ${sizeKB} KB | 
                        ${created}
                    </div>
                </div>
                <div class="jingle-actions">
                    <button class="icon-btn play" onclick="playJingle('${jingle.filename}')" title="Play">
                        ▶️
                    </button>
                    <button class="icon-btn download" onclick="downloadJingle('${jingle.filename}')" title="Download">
                        ⬇️
                    </button>
                    <button class="icon-btn delete" onclick="deleteJingle('${jingle.filename}')" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function loadPlaylistSettings() {
    try {
        const apiUrl = CONFIG.API_URL;
        const url = apiUrl.endsWith('/api') ? `${apiUrl}/playlist` : `${apiUrl}/api/playlist`;

        const response = await fetch(url);
        const playlist = await response.json();

        playlistState = playlist;

        document.getElementById('playlistEnabled').checked = playlist.enabled;
        document.getElementById('playlistInterval').value = playlist.interval;

        updatePlaylistStatus();
    } catch (error) {
        console.error('Error loading playlist:', error);
    }
}

async function updatePlaylistSettings() {
    const enabled = document.getElementById('playlistEnabled').checked;
    const interval = parseInt(document.getElementById('playlistInterval').value);

    playlistState.enabled = enabled;
    playlistState.interval = interval;

    try {
        const apiUrl = CONFIG.API_URL;
        const url = apiUrl.endsWith('/api') ? `${apiUrl}/playlist` : `${apiUrl}/api/playlist`;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(playlistState)
        });

        const result = await response.json();
        console.log('Playlist updated:', result);

        updatePlaylistStatus();
    } catch (error) {
        console.error('Error updating playlist:', error);
        alert('Failed to update playlist settings');
    }
}

function updatePlaylistStatus() {
    const statusDiv = document.getElementById('playlistStatus');

    if (playlistState.enabled && playlistState.jingles.length > 0) {
        statusDiv.innerHTML = `
            ✅ <strong>Active:</strong> ${playlistState.jingles.length} jingles will play every ${playlistState.interval} rounds
        `;
        statusDiv.style.color = '#4CAF50';
    } else if (playlistState.enabled) {
        statusDiv.innerHTML = `
            ⚠️ <strong>Warning:</strong> Playlist is enabled but no jingles selected
        `;
        statusDiv.style.color = '#ff9800';
    } else {
        statusDiv.innerHTML = `
            ⏸️ Playlist disabled
        `;
        statusDiv.style.color = '#999';
    }
}

async function toggleJingleInPlaylist(filename) {
    const index = playlistState.jingles.indexOf(filename);

    if (index > -1) {
        playlistState.jingles.splice(index, 1);
    } else {
        playlistState.jingles.push(filename);
    }

    await updatePlaylistSettings();
    await loadJinglesLibrary(); // Refresh display
}

function addToPlaylist() {
    if (!currentJingleFilename) {
        alert('No jingle to add. Please generate a jingle first.');
        return;
    }

    if (!playlistState.jingles.includes(currentJingleFilename)) {
        playlistState.jingles.push(currentJingleFilename);
        updatePlaylistSettings();
        loadJinglesLibrary();
        alert('✅ Jingle added to playlist!');
    } else {
        alert('This jingle is already in the playlist.');
    }
}

let audioPreview = null;

function playJingle(filename) {
    const apiUrl = window.BACKEND_URL || '';
    const url = apiUrl.endsWith('/api')
        ? `${apiUrl}/jingles/${filename}`
        : `${apiUrl}/api/jingles/${filename}`;

    if (audioPreview) {
        audioPreview.pause();
    }

    audioPreview = new Audio(url);
    audioPreview.play().catch(err => {
        console.error('Playback error:', err);
        alert('Failed to play jingle');
    });
}

function downloadJingle(filename) {
    const apiUrl = window.BACKEND_URL || '';
    const url = apiUrl.endsWith('/api')
        ? `${apiUrl}/jingles/${filename}`
        : `${apiUrl}/api/jingles/${filename}`;

    window.open(url, '_blank');
}

async function deleteJingle(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
        return;
    }

    // Note: No delete endpoint implemented yet - just remove from playlist
    const index = playlistState.jingles.indexOf(filename);
    if (index > -1) {
        playlistState.jingles.splice(index, 1);
        await updatePlaylistSettings();
    }

    alert('Note: File deletion not implemented. Removed from playlist only.');
}

function testPlaylist() {
    if (playlistState.jingles.length === 0) {
        alert('No jingles in playlist. Add some jingles first!');
        return;
    }

    // Play first jingle in playlist
    playJingle(playlistState.jingles[0]);
    alert(`Testing playlist: Playing ${playlistState.jingles[0]}\n\nPlaylist has ${playlistState.jingles.length} jingles total.`);
}

// ============================================================================
// VOICE SETTINGS CONTROLS
// ============================================================================

function updateVoiceSetting(setting, value) {
    // Convert 0-100 slider value to 0-1 range
    const normalizedValue = value / 100;

    // Update state
    jingleData.voiceSettings[setting] = normalizedValue;

    // Update display
    const displayValue = normalizedValue.toFixed(2);
    if (setting === 'stability') {
        document.getElementById('stabilityValue').textContent = displayValue;
    } else if (setting === 'similarity_boost') {
        document.getElementById('similarityValue').textContent = displayValue;
    } else if (setting === 'style') {
        document.getElementById('styleValue').textContent = displayValue;
    }

    console.log(`Voice setting updated: ${setting} = ${displayValue}`);
}

function toggleSpeakerBoost() {
    const toggle = document.getElementById('speakerBoostToggle');
    const value = document.getElementById('speakerBoostValue');

    // Toggle state
    jingleData.voiceSettings.use_speaker_boost = !jingleData.voiceSettings.use_speaker_boost;

    // Update UI
    if (jingleData.voiceSettings.use_speaker_boost) {
        toggle.classList.add('active');
        value.textContent = 'ON';
        value.style.background = '#4CAF50';
    } else {
        toggle.classList.remove('active');
        value.textContent = 'OFF';
        value.style.background = '#f44336';
    }

    console.log(`Speaker boost: ${jingleData.voiceSettings.use_speaker_boost}`);
}

function resetVoiceSettings() {
    // Reset to pub-optimized defaults
    applyVoicePreset('pub');
    showQuickMessage('✅ Voice settings reset to pub-optimized defaults');
    console.log('Voice settings reset to pub defaults');
}

function applyVoicePreset(presetName) {
    const preset = VOICE_PRESETS[presetName];
    if (!preset) {
        console.error('Unknown preset:', presetName);
        return;
    }

    console.log(`Applying preset: ${preset.name}`, preset.settings);

    // Update jingleData
    jingleData.voiceSettings = { ...preset.settings };

    // Update sliders
    document.getElementById('stabilitySlider').value = preset.settings.stability * 100;
    document.getElementById('similaritySlider').value = preset.settings.similarity_boost * 100;
    document.getElementById('styleSlider').value = preset.settings.style * 100;

    // Update displays
    document.getElementById('stabilityValue').textContent = preset.settings.stability.toFixed(2);
    document.getElementById('similarityValue').textContent = preset.settings.similarity_boost.toFixed(2);
    document.getElementById('styleValue').textContent = preset.settings.style.toFixed(2);

    // Update speaker boost
    const toggle = document.getElementById('speakerBoostToggle');
    const value = document.getElementById('speakerBoostValue');
    if (preset.settings.use_speaker_boost) {
        toggle.classList.add('active');
        value.textContent = 'ON';
        value.style.background = '#4CAF50';
    } else {
        toggle.classList.remove('active');
        value.textContent = 'OFF';
        value.style.background = '#f44336';
    }

    // Update preset selector
    const selector = document.getElementById('voicePresetSelector');
    if (selector) {
        selector.value = presetName;
    }

    showQuickMessage(`✅ Applied: ${preset.name}`);
}

async function previewVoiceWithSettings() {
    const previewBtn = document.getElementById('previewVoiceBtn');

    // Stop any current preview
    if (previewAudio) {
        previewAudio.pause();
        previewAudio = null;
        previewBtn.classList.remove('playing');
        previewBtn.innerHTML = '🎵 Preview with Current Settings';
    }

    // Get current voice
    const selectedVoice = document.querySelector('.voice-card.selected');
    if (!selectedVoice) {
        showQuickMessage('⚠️ Please select a voice first');
        return;
    }

    const voiceId = selectedVoice.dataset.voice;
    const previewText = jingleData.text || 'Welcome to Music Bingo at our venue! Join us for an amazing evening of fun and entertainment!';

    try {
        previewBtn.disabled = true;
        previewBtn.innerHTML = '⏳ Generating preview...';

        console.log('Previewing voice with settings:', jingleData.voiceSettings);

        const apiUrl = CONFIG.API_URL;
        const endpoint = apiUrl.includes('/api') ? `${apiUrl}/generate-tts-preview` : `${apiUrl}/api/generate-tts-preview`;

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: previewText,
                voice_id: voiceId,
                voice_settings: jingleData.voiceSettings
            })
        });

        if (!response.ok) {
            throw new Error('Failed to generate preview');
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        previewAudio = new Audio(audioUrl);
        previewBtn.classList.add('playing');
        previewBtn.innerHTML = '⏸️ Stop Preview';

        previewAudio.play();

        previewAudio.onended = () => {
            previewBtn.classList.remove('playing');
            previewBtn.innerHTML = '🎵 Preview with Current Settings';
            previewBtn.disabled = false;
            URL.revokeObjectURL(audioUrl);
        };

        previewAudio.onerror = () => {
            previewBtn.classList.remove('playing');
            previewBtn.innerHTML = '🎵 Preview with Current Settings';
            previewBtn.disabled = false;
            showQuickMessage('❌ Error playing preview');
        };

        previewBtn.disabled = false;

    } catch (error) {
        console.error('Error generating voice preview:', error);
        showQuickMessage('❌ Failed to generate preview');
        previewBtn.classList.remove('playing');
        previewBtn.innerHTML = '🎵 Preview with Current Settings';
        previewBtn.disabled = false;
    }
}
