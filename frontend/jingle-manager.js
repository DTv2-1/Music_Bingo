// Jingle Manager JavaScript
// Manages the UI for creating, editing, and deleting jingle schedules

let schedules = [];
let editingScheduleId = null;
let availableJingles = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔍 Jingle Manager loaded');
    console.log('📍 Current URL:', window.location.href);
    console.log('⚙️ CONFIG.API_URL:', CONFIG.API_URL);
    console.log('⚙️ CONFIG.BACKEND_URL:', CONFIG.BACKEND_URL);
    
    loadJingles();
    loadSchedules();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('createScheduleBtn').addEventListener('click', openCreateModal);
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.getElementById('cancelBtn').addEventListener('click', closeModal);
    document.getElementById('scheduleForm').addEventListener('submit', handleSubmit);
    
    // Priority slider
    const prioritySlider = document.getElementById('priority');
    const priorityValue = document.getElementById('priorityValue');
    prioritySlider.addEventListener('input', (e) => {
        priorityValue.textContent = e.target.value;
    });
    
    // No end date checkbox
    const noEndDateCheck = document.getElementById('noEndDate');
    const endDateInput = document.getElementById('endDate');
    noEndDateCheck.addEventListener('change', (e) => {
        endDateInput.disabled = e.target.checked;
        if (e.target.checked) {
            endDateInput.value = '';
        }
    });
    
    // All day checkbox
    const allDayCheck = document.getElementById('allDayCheck');
    const timeStart = document.getElementById('timeStart');
    const timeEnd = document.getElementById('timeEnd');
    allDayCheck.addEventListener('change', (e) => {
        timeStart.disabled = e.target.checked;
        timeEnd.disabled = e.target.checked;
        if (e.target.checked) {
            timeStart.value = '';
            timeEnd.value = '';
        }
    });
    
    // Pattern selection visual feedback
    const patternRadios = document.querySelectorAll('input[name="repeatPattern"]');
    patternRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const patterns = {
                'occasional': '8-10 rounds between jingles - Less intrusive',
                'regular': '5-7 rounds between jingles - Balanced approach',
                'often': '3-4 rounds between jingles - Maximum visibility'
            };
            console.log(`Selected pattern: ${e.target.value} - ${patterns[e.target.value]}`);
        });
    });
    
    // Close modal when clicking outside
    document.getElementById('scheduleModal').addEventListener('click', (e) => {
        if (e.target.id === 'scheduleModal') {
            closeModal();
        }
    });
}

// Load available jingles from backend
async function loadJingles() {
    try {
        const url = `${CONFIG.API_URL}/api/jingles`;
        console.log('📥 Loading jingles from:', url);
        
        const response = await fetch(url);
        console.log('✅ Jingles response status:', response.status);
        
        if (!response.ok) {
            console.error('❌ Failed to load jingles. Status:', response.status);
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        availableJingles = data.jingles || [];
        console.log('✅ Loaded jingles:', availableJingles.length, 'items');
        
        // Populate jingle dropdown
        const select = document.getElementById('jingleFilename');
        select.innerHTML = '<option value="">-- Select a jingle file --</option>';
        
        availableJingles.forEach(jingle => {
            const option = document.createElement('option');
            option.value = jingle.filename;
            option.textContent = `${jingle.filename} (${formatDate(jingle.created)})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('❌ Error loading jingles:', error);
        showNotification('Failed to load jingles', 'error');
    }
}

// Load all schedules
async function loadSchedules() {
    try {
        const url = `${CONFIG.API_URL}/api/jingle-schedules`;
        console.log('📥 Loading schedules from:', url);
        
        const response = await fetch(url);
        console.log('✅ Schedules response status:', response.status);
        
        if (!response.ok) {
            console.error('❌ Failed to load schedules. Status:', response.status);
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        schedules = data.schedules || [];
        console.log('✅ Loaded schedules:', schedules.length, 'items');
        renderSchedules();
    } catch (error) {
        console.error('❌ Error loading schedules:', error);
        showNotification('Failed to load schedules', 'error');
        document.getElementById('schedulesList').innerHTML = 
            '<div class="error">Failed to load schedules. Please refresh the page.</div>';
    }
}

// Render schedules list
function renderSchedules() {
    const container = document.getElementById('schedulesList');
    
    if (schedules.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>📅 No schedules yet</p>
                <p>Click "Create New Schedule" to get started</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = schedules.map(schedule => `
        <div class="schedule-card ${schedule.enabled ? '' : 'disabled'}">
            <div class="schedule-header">
                <h3>
                    ${schedule.jingle_name}
                    ${schedule.is_active_now ? '<span class="badge badge-active">Active Now</span>' : ''}
                    ${!schedule.enabled ? '<span class="badge badge-disabled">Disabled</span>' : ''}
                </h3>
                <div class="schedule-actions">
                    <button class="btn-icon" onclick="previewJingle('${schedule.jingle_filename}')" title="Preview">
                        ▶️
                    </button>
                    <button class="btn-icon" onclick="editSchedule(${schedule.id})" title="Edit">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="toggleSchedule(${schedule.id}, ${schedule.enabled})" title="${schedule.enabled ? 'Disable' : 'Enable'}">
                        ${schedule.enabled ? '⏸️' : '▶️'}
                    </button>
                    <button class="btn-icon btn-danger" onclick="deleteSchedule(${schedule.id})" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
            
            <div class="schedule-details">
                <div class="detail-row">
                    <span class="label">📁 File:</span>
                    <span>${schedule.jingle_filename}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">📅 Dates:</span>
                    <span>${schedule.start_date} ${schedule.end_date ? '→ ' + schedule.end_date : '(no end)'}</span>
                </div>
                
                ${schedule.time_start || schedule.time_end ? `
                <div class="detail-row">
                    <span class="label">🕐 Time:</span>
                    <span>${schedule.time_start || 'any'} → ${schedule.time_end || 'any'}</span>
                </div>
                ` : '<div class="detail-row"><span class="label">🕐 Time:</span><span>All day</span></div>'}
                
                <div class="detail-row">
                    <span class="label">📆 Days:</span>
                    <span class="days-list">
                        ${formatDaysOfWeek(schedule.days_of_week)}
                    </span>
                </div>
                
                <div class="detail-row">
                    <span class="label">🔁 Pattern:</span>
                    <span class="pattern-badge pattern-${schedule.repeat_pattern}">
                        ${schedule.repeat_pattern.toUpperCase()} (every ~${schedule.interval} rounds)
                    </span>
                </div>
                
                <div class="detail-row">
                    <span class="label">⭐ Priority:</span>
                    <span>${schedule.priority}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Format days of week for display
function formatDaysOfWeek(days) {
    const dayNames = {
        monday: 'Mon',
        tuesday: 'Tue',
        wednesday: 'Wed',
        thursday: 'Thu',
        friday: 'Fri',
        saturday: 'Sat',
        sunday: 'Sun'
    };
    
    const activeDays = Object.entries(days)
        .filter(([_, isActive]) => isActive)
        .map(([day, _]) => dayNames[day]);
    
    return activeDays.length > 0 ? activeDays.join(', ') : 'None';
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// Open create modal
function openCreateModal() {
    editingScheduleId = null;
    document.getElementById('modalTitle').textContent = 'Create New Schedule';
    document.getElementById('scheduleForm').reset();
    clearValidationErrors();
    document.getElementById('enabled').checked = true;
    document.getElementById('priority').value = 0;
    document.getElementById('priorityValue').textContent = '0';
    document.getElementById('patternRegular').checked = true;
    
    // Reset checkboxes
    document.getElementById('noEndDate').checked = false;
    document.getElementById('allDayCheck').checked = false;
    document.getElementById('endDate').disabled = false;
    document.getElementById('timeStart').disabled = false;
    document.getElementById('timeEnd').disabled = false;
    
    // Set today as default start date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').value = today;
    
    document.getElementById('scheduleModal').classList.remove('hidden');
}

// Open edit modal
async function editSchedule(scheduleId) {
    editingScheduleId = scheduleId;
    const schedule = schedules.find(s => s.id === scheduleId);
    
    if (!schedule) {
        showNotification('Schedule not found', 'error');
        return;
    }
    
    clearValidationErrors();
    document.getElementById('modalTitle').textContent = 'Edit Schedule';
    
    // Populate form
    document.getElementById('jingleName').value = schedule.jingle_name;
    document.getElementById('jingleFilename').value = schedule.jingle_filename;
    document.getElementById('startDate').value = schedule.start_date;
    document.getElementById('endDate').value = schedule.end_date || '';
    document.getElementById('timeStart').value = schedule.time_start || '';
    document.getElementById('timeEnd').value = schedule.time_end || '';
    document.getElementById('priority').value = schedule.priority;
    document.getElementById('priorityValue').textContent = schedule.priority;
    document.getElementById('enabled').checked = schedule.enabled;
    
    // Set repeat pattern radio button
    document.getElementById(`pattern${schedule.repeat_pattern.charAt(0).toUpperCase() + schedule.repeat_pattern.slice(1)}`).checked = true;
    
    // Set checkboxes
    document.getElementById('noEndDate').checked = !schedule.end_date;
    document.getElementById('endDate').disabled = !schedule.end_date;
    
    const hasTime = schedule.time_start || schedule.time_end;
    document.getElementById('allDayCheck').checked = !hasTime;
    document.getElementById('timeStart').disabled = !hasTime;
    document.getElementById('timeEnd').disabled = !hasTime;
    
    // Set days checkboxes
    Object.entries(schedule.days_of_week).forEach(([day, isActive]) => {
        const checkbox = document.getElementById(`day${day.charAt(0).toUpperCase() + day.slice(1)}`);
        if (checkbox) checkbox.checked = isActive;
    });
    
    document.getElementById('scheduleModal').classList.remove('hidden');
}

// Close modal
function closeModal() {
    document.getElementById('scheduleModal').classList.add('hidden');
    editingScheduleId = null;
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    // Get repeat pattern from radio buttons
    const repeatPattern = document.querySelector('input[name="repeatPattern"]:checked').value;
    
    // Collect form data
    const formData = {
        jingle_name: document.getElementById('jingleName').value.trim(),
        jingle_filename: document.getElementById('jingleFilename').value,
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value || null,
        time_start: document.getElementById('timeStart').value || null,
        time_end: document.getElementById('timeEnd').value || null,
        days_of_week: {
            monday: document.getElementById('dayMonday').checked,
            tuesday: document.getElementById('dayTuesday').checked,
            wednesday: document.getElementById('dayWednesday').checked,
            thursday: document.getElementById('dayThursday').checked,
            friday: document.getElementById('dayFriday').checked,
            saturday: document.getElementById('daySaturday').checked,
            sunday: document.getElementById('daySunday').checked
        },
        repeat_pattern: repeatPattern,
        priority: parseInt(document.getElementById('priority').value),
        enabled: document.getElementById('enabled').checked
    };
    
    // ========== VALIDATIONS ==========
    
    // Validate jingle filename is selected
    if (!formData.jingle_filename) {
        showNotification('Please select a jingle file', 'error');
        return;
    }
    
    // Validate at least one day is selected
    const hasDay = Object.values(formData.days_of_week).some(v => v);
    if (!hasDay) {
        showNotification('Please select at least one day of the week', 'error');
        return;
    }
    
    // Validate start date is not after end date
    if (formData.end_date) {
        const startDate = new Date(formData.start_date);
        const endDate = new Date(formData.end_date);
        if (startDate > endDate) {
            showNotification('Start date cannot be after end date', 'error');
            return;
        }
    }
    
    // Validate time start is not after time end
    if (formData.time_start && formData.time_end) {
        const timeStart = formData.time_start.split(':').map(Number);
        const timeEnd = formData.time_end.split(':').map(Number);
        const startMinutes = timeStart[0] * 60 + timeStart[1];
        const endMinutes = timeEnd[0] * 60 + timeEnd[1];
        
        if (startMinutes >= endMinutes) {
            showNotification('Start time must be before end time', 'error');
            return;
        }
    }
    
    // Validate jingle name is not empty
    if (!formData.jingle_name || formData.jingle_name.length < 3) {
        showNotification('Jingle name must be at least 3 characters long', 'error');
        return;
    }
    
    // ========== END VALIDATIONS ==========
    
    try {
        let response;
        if (editingScheduleId) {
            // Update existing schedule
            response = await fetch(`${CONFIG.API_URL}/api/jingle-schedules/${editingScheduleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        } else {
            // Create new schedule
            response = await fetch(`${CONFIG.API_URL}/api/jingle-schedules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message || 'Schedule saved successfully', 'success');
            closeModal();
            loadSchedules();
        } else {
            showNotification(data.error || 'Failed to save schedule', 'error');
        }
    } catch (error) {
        console.error('Error saving schedule:', error);
        showNotification('Failed to save schedule', 'error');
    }
}

// Toggle schedule enabled/disabled
async function toggleSchedule(scheduleId, currentEnabled) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/jingle-schedules/${scheduleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !currentEnabled })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(`Schedule ${!currentEnabled ? 'enabled' : 'disabled'}`, 'success');
            loadSchedules();
        } else {
            showNotification(data.error || 'Failed to toggle schedule', 'error');
        }
    } catch (error) {
        console.error('Error toggling schedule:', error);
        showNotification('Failed to toggle schedule', 'error');
    }
}

// Delete schedule
async function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) {
        return;
    }
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/api/jingle-schedules/${scheduleId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Schedule deleted successfully', 'success');
            loadSchedules();
        } else {
            showNotification(data.error || 'Failed to delete schedule', 'error');
        }
    } catch (error) {
        console.error('Error deleting schedule:', error);
        showNotification('Failed to delete schedule', 'error');
    }
}

// Preview jingle
function previewJingle(filename) {
    const audio = new Audio(`${CONFIG.API_URL}/api/jingles/${filename}`);
    audio.play().catch(error => {
        console.error('Error playing jingle:', error);
        showNotification('Failed to play jingle', 'error');
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Helper function to validate form field
function validateField(fieldId, condition, errorMessage) {
    const field = document.getElementById(fieldId);
    const existingError = field.parentElement.querySelector('.error-message');
    
    if (!condition) {
        field.classList.add('error');
        if (!existingError) {
            const errorSpan = document.createElement('span');
            errorSpan.className = 'error-message';
            errorSpan.textContent = errorMessage;
            field.parentElement.appendChild(errorSpan);
        }
        return false;
    } else {
        field.classList.remove('error');
        if (existingError) {
            existingError.remove();
        }
        return true;
    }
}

// Clear all validation errors
function clearValidationErrors() {
    document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    document.querySelectorAll('.error-message').forEach(el => el.remove());
}
