/**
 * =============================================================================
 * Mozhii RAG Data Platform - Cleaning Tab JavaScript
 * =============================================================================
 * Handles all functionality for the CLEANING tab where the NLP team
 * cleans and processes raw Tamil content.
 * 
 * Features:
 *   - List raw files available for cleaning
 *   - Display raw content for reference
 *   - Copy raw content to clipboard
 *   - Submit cleaned content
 *   - Track cleaning status
 * =============================================================================
 */

// =============================================================================
// DOM ELEMENTS
// =============================================================================

/**
 * Cache DOM elements for the cleaning tab
 */
const CleaningElements = {
    // Panels
    fileList: null,
    rawPreview: null,
    
    // Form elements
    content: null,
    charCount: null,
    selectedFile: null,
    
    // Buttons
    refreshBtn: null,
    copyBtn: null,
    clearBtn: null,
    submitBtn: null,
    
    // Initialize element references
    init() {
        this.fileList = document.getElementById('cleaning-file-list');
        this.rawPreview = document.getElementById('cleaning-raw-preview');
        this.content = document.getElementById('cleaning-content');
        this.charCount = document.getElementById('cleaning-char-count');
        this.selectedFile = document.getElementById('cleaning-selected-file');
        this.refreshBtn = document.getElementById('cleaning-refresh');
        this.copyBtn = document.getElementById('cleaning-copy');
        this.clearBtn = document.getElementById('cleaning-clear');
        this.submitBtn = document.getElementById('cleaning-submit');
    }
};

// =============================================================================
// STATE
// =============================================================================

/**
 * Local state for the cleaning tab
 */
const CleaningState = {
    files: [],              // List of available raw files
    selectedFile: null,     // Currently selected file
    selectedContent: ''     // Raw content of selected file
};

// =============================================================================
// FILE LIST FUNCTIONS
// =============================================================================

/**
 * Refresh the list of raw files available for cleaning
 * Fetches approved raw files from the API
 */
async function refreshCleaningFiles() {
    try {
        // Show loading state
        CleaningElements.fileList.innerHTML = `
            <div class="empty-state">
                <p>Loading files...</p>
            </div>
        `;
        
        // Fetch files from API
        const response = await api('/api/cleaning/raw-files');
        
        if (response.success) {
            CleaningState.files = response.files;
            renderCleaningFileList();
        } else {
            throw new Error(response.error || 'Failed to load files');
        }
        
    } catch (error) {
        console.error('Error loading cleaning files:', error);
        CleaningElements.fileList.innerHTML = `
            <div class="empty-state">
                <p>Error loading files</p>
                <span>${error.message}</span>
            </div>
        `;
    }
}

/**
 * Render the file list in the UI
 */
function renderCleaningFileList() {
    const files = CleaningState.files;
    
    if (files.length === 0) {
        CleaningElements.fileList.innerHTML = `
            <div class="empty-state">
                <p>No raw files available</p>
                <span>Submit content in the RAW DATA tab first</span>
            </div>
        `;
        return;
    }
    
    // Create file list HTML
    CleaningElements.fileList.innerHTML = files.map(file => `
        <div class="file-item ${CleaningState.selectedFile === file.filename ? 'selected' : ''}" 
             data-filename="${file.filename}"
             onclick="selectCleaningFile('${file.filename}')">
            <span class="file-icon">📄</span>
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">${file.language.toUpperCase()} • ${file.content_length.toLocaleString()} chars</div>
            </div>
            <span class="file-status ${file.cleaning_status}">${formatStatus(file.cleaning_status)}</span>
        </div>
    `).join('');
}

/**
 * Format status for display
 * 
 * @param {string} status - Status value
 * @returns {string} - Formatted status text
 */
function formatStatus(status) {
    const statusMap = {
        'not_started': 'Not Cleaned',
        'pending': 'Pending',
        'approved': 'Cleaned'
    };
    return statusMap[status] || status;
}

// =============================================================================
// FILE SELECTION
// =============================================================================

/**
 * Handle file selection
 * Updates the UI to show the selected file's content
 * 
 * @param {string} filename - Name of the file to select
 */
async function selectCleaningFile(filename) {
    // Find the file in our state
    const file = CleaningState.files.find(f => f.filename === filename);
    
    if (!file) {
        console.error('File not found:', filename);
        return;
    }
    
    // Update state
    CleaningState.selectedFile = filename;
    CleaningState.selectedContent = file.content;
    
    // Update hidden field
    CleaningElements.selectedFile.value = filename;
    
    // Update file list selection
    document.querySelectorAll('#cleaning-file-list .file-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.filename === filename);
    });
    
    // Update raw preview
    CleaningElements.rawPreview.innerHTML = `
        <div class="tamil-text">${escapeHtml(file.content)}</div>
    `;
    
    // Enable form elements
    CleaningElements.content.disabled = false;
    CleaningElements.copyBtn.disabled = false;
    CleaningElements.clearBtn.disabled = false;
    CleaningElements.submitBtn.disabled = false;
    
    // Clear previous cleaned content
    CleaningElements.content.value = '';
    updateCleaningCharCount();
    
    // Show info toast
    showToast('File Selected', `Selected "${filename}" for cleaning`, 'info', 3000);
}

/**
 * Escape HTML to prevent XSS
 * 
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// COPY FUNCTIONALITY
// =============================================================================

/**
 * Copy raw content to clipboard
 * Makes it easy for cleaners to work with the content
 */
async function copyRawContent() {
    if (!CleaningState.selectedContent) {
        showToast('No Content', 'Please select a file first', 'warning');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(CleaningState.selectedContent);
        showToast('Copied!', 'Raw content copied to clipboard', 'success', 3000);
        
        // Visual feedback on button
        const originalText = CleaningElements.copyBtn.textContent;
        CleaningElements.copyBtn.textContent = '✓ Copied!';
        setTimeout(() => {
            CleaningElements.copyBtn.textContent = originalText;
        }, 2000);
        
    } catch (error) {
        showToast('Copy Failed', 'Could not copy to clipboard', 'error');
    }
}

// =============================================================================
// FORM HANDLERS
// =============================================================================

/**
 * Update character count for cleaned content
 */
function updateCleaningCharCount() {
    const content = CleaningElements.content.value;
    const count = content.length;
    CleaningElements.charCount.textContent = `${count.toLocaleString()} characters`;
}

/**
 * Clear the cleaning form
 */
function clearCleaningForm() {
    CleaningElements.content.value = '';
    updateCleaningCharCount();
}

/**
 * Submit cleaned content
 */
async function handleCleaningSubmit() {
    // Check if file is selected
    if (!CleaningState.selectedFile) {
        showToast('No File Selected', 'Please select a file to clean first', 'warning');
        return;
    }
    
    // Check if content is provided
    const content = CleaningElements.content.value.trim();
    if (!content) {
        showToast('No Content', 'Please enter the cleaned content', 'warning');
        return;
    }
    
    // Check minimum length
    if (content.length < 50) {
        showToast('Content Too Short', 'Cleaned content must be at least 50 characters', 'warning');
        return;
    }
    
    // Disable submit button
    CleaningElements.submitBtn.disabled = true;
    CleaningElements.submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';
    
    try {
        // Submit to API
        const response = await api('/api/cleaning/submit', {
            method: 'POST',
            body: JSON.stringify({
                filename: CleaningState.selectedFile,
                content: content
            })
        });
        
        if (response.success) {
            showToast(
                'Submitted Successfully!',
                `Cleaned "${CleaningState.selectedFile}" has been saved.`,
                'success'
            );
            
            // Clear form
            clearCleaningForm();
            
            // Refresh file list to update status
            await refreshCleaningFiles();
            
            // Refresh submitted cleaned files list
            refreshCleanedFilesList();
            
        } else {
            throw new Error(response.error || 'Submission failed');
        }
        
    } catch (error) {
        showToast('Submission Failed', error.message, 'error');
        
    } finally {
        // Re-enable submit button
        CleaningElements.submitBtn.disabled = false;
        CleaningElements.submitBtn.innerHTML = '<span class="btn-icon">📤</span> Submit Cleaned Data';
    }
}

// =============================================================================
// SUBMITTED CLEANED FILES LIST
// =============================================================================

/**
 * Refresh the list of submitted (approved) cleaned files
 */
async function refreshCleanedFilesList() {
    const listEl = document.getElementById('cleaned-files-list');
    if (!listEl) return;
    
    try {
        const response = await api('/api/cleaning/approved');
        
        if (response.success && response.files.length > 0) {
            listEl.innerHTML = response.files.map(file => `
                <div class="submitted-file-item">
                    <div class="submitted-file-info">
                        <span class="submitted-file-name">${file.filename}</span>
                        <span class="submitted-file-meta">${(file.language || 'ta').toUpperCase()} • ${(file.content_length || 0).toLocaleString()} chars • ${file.source || 'unknown'}</span>
                    </div>
                    <div class="submitted-file-actions">
                        <button class="btn btn-sm btn-secondary" onclick="editCleanedFile('${file.filename}')" title="Edit">✏️</button>
                        <button class="btn btn-sm btn-error" onclick="deleteCleanedFile('${file.filename}')" title="Remove">✕</button>
                    </div>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<div class="empty-state small"><p>No cleaned files submitted yet</p></div>';
        }
    } catch (error) {
        console.error('Error loading cleaned files list:', error);
    }
}

/**
 * Delete a cleaned file
 */
async function deleteCleanedFile(filename) {
    showModal('Delete Cleaned File', `<p>Are you sure you want to delete "<strong>${filename}</strong>"?</p>`, [
        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
        { text: 'Delete', class: 'btn-error', onClick: async () => {
            hideModal();
            try {
                const response = await api(`/api/cleaning/file/${filename}`, { method: 'DELETE' });
                if (response.success) {
                    showToast('Deleted', `"${filename}" has been deleted.`, 'success');
                    refreshCleanedFilesList();
                    refreshCleaningFiles();
                } else {
                    showToast('Error', response.error || 'Failed to delete', 'error');
                }
            } catch (error) {
                showToast('Error', error.message, 'error');
            }
        }}
    ]);
}

/**
 * Edit a cleaned file
 */
async function editCleanedFile(filename) {
    try {
        const data = await api(`/api/cleaning/file/${filename}`);
        if (!data.success) {
            showToast('Error', 'Failed to load file', 'error');
            return;
        }
        
        showModal(`Edit Cleaned - ${filename}`, `
            <div class="edit-form">
                <div class="form-group">
                    <label>Content <span class="char-count" id="clean-edit-char-count">${data.content.length} characters</span></label>
                    <textarea id="clean-edit-content" rows="15" class="tamil-text">${data.content}</textarea>
                </div>
            </div>
        `, [
            { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
            { text: 'Save', class: 'btn-primary', onClick: async () => {
                const newContent = document.getElementById('clean-edit-content').value;
                if (!newContent.trim()) {
                    showToast('Error', 'Content cannot be empty', 'error');
                    return;
                }
                try {
                    const result = await api(`/api/cleaning/file/${filename}`, {
                        method: 'PUT',
                        body: JSON.stringify({ content: newContent })
                    });
                    if (result.success) {
                        showToast('Saved', `"${filename}" updated.`, 'success');
                        hideModal();
                        refreshCleanedFilesList();
                    } else {
                        showToast('Error', result.error || 'Failed to save', 'error');
                    }
                } catch (error) {
                    showToast('Error', error.message, 'error');
                }
            }}
        ]);
        
        const contentArea = document.getElementById('clean-edit-content');
        const charCount = document.getElementById('clean-edit-char-count');
        contentArea.addEventListener('input', () => {
            charCount.textContent = `${contentArea.value.length} characters`;
        });
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

/**
 * Initialize event listeners for the cleaning tab
 */
function initCleaningEventListeners() {
    // Refresh button
    CleaningElements.refreshBtn.addEventListener('click', refreshCleaningFiles);
    
    // Copy button
    CleaningElements.copyBtn.addEventListener('click', copyRawContent);
    
    // Clear button
    CleaningElements.clearBtn.addEventListener('click', () => {
        if (CleaningElements.content.value.trim()) {
            showModal('Clear Cleaned Content?',
                '<p>Are you sure you want to clear the cleaned content?</p>',
                [
                    { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
                    { text: 'Clear', class: 'btn-primary', onClick: () => {
                        clearCleaningForm();
                        hideModal();
                    }}
                ]
            );
        }
    });
    
    // Submit button
    CleaningElements.submitBtn.addEventListener('click', handleCleaningSubmit);
    
    // Character count on input
    CleaningElements.content.addEventListener('input', updateCleaningCharCount);
    
    // Submit on Ctrl+Enter
    CleaningElements.content.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            handleCleaningSubmit();
        }
    });
}

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize the cleaning tab
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize element references
    CleaningElements.init();
    
    // Set up event listeners
    initCleaningEventListeners();
    
    // Load submitted cleaned files list
    refreshCleanedFilesList();
    
    // Refresh list button
    const refreshListBtn = document.getElementById('cleaning-refresh-list');
    if (refreshListBtn) {
        refreshListBtn.addEventListener('click', refreshCleanedFilesList);
    }
    
    console.log('🧹 Cleaning tab initialized');
});
