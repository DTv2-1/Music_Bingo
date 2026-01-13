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
    musicPrompt: 'upbeat energetic pub background music with guitar',
    duration: 10
};

let pollingInterval = null;

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
    
    updateCharCount();
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
    const count = textarea.value.length;
    
    counter.textContent = count;
    counter.parentElement.classList.remove('warning', 'error');
    
    if (count > 120) {
        counter.parentElement.classList.add('warning');
    }
    if (count > 140) {
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
    const templateButtons = document.querySelectorAll('.template-btn');
    
    templateButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const template = btn.getAttribute('data-template');
            document.getElementById('jingleText').value = template;
            jingleData.text = template;
            updateCharCount();
        });
    });
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
    event.stopPropagation(); // Prevent card selection
    
    const btn = event.target;
    
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
        // Disable all test buttons
        document.querySelectorAll('.test-voice-btn').forEach(b => b.disabled = true);
        
        btn.textContent = '⏳ Loading...';
        btn.classList.add('playing');
        
        // Generate sample text
        const sampleText = `Hello! This is the ${voiceName} voice. Perfect for your pub jingles and promotions.`;
        
        // Call TTS API
        const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL || 'http://localhost:8080';
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
    event.stopPropagation(); // Prevent style selection
    
    const btn = event.target;
    
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
        // Disable all preview buttons
        document.querySelectorAll('.preview-music-btn').forEach(b => b.disabled = true);
        
        btn.textContent = '⏳ Loading...';
        btn.classList.add('playing');
        
        console.log('Generating music preview for:', musicName);
        
        // Call Music Generation API
        const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL || 'http://localhost:8080';
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
    
    // Show progress section
    document.getElementById('progressSection').classList.add('active');
    document.getElementById('generateButtons').style.display = 'none';
    document.getElementById('errorMessage').classList.add('hidden');
    
    try {
        // Call API to start generation
        const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL || 'http://localhost:8080';
        const endpoint = apiUrl.includes('/api') ? `${apiUrl}/generate-jingle` : `${apiUrl}/api/generate-jingle`;
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jingleData)
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
    
    const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL || 'http://localhost:8080';
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
    
    // Hide progress, show player
    document.getElementById('progressSection').classList.remove('active');
    document.getElementById('audioPlayer').classList.remove('hidden');
    
    // Set audio source
    const apiUrl = CONFIG.API_URL || CONFIG.BACKEND_URL || 'http://localhost:8080';
    // result.audio_url already includes /api/jingles/filename
    const audioUrl = result.audio_url.startsWith('http') 
        ? result.audio_url 
        : `${apiUrl}${result.audio_url}`;
    
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
