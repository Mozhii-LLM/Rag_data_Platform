/**
 * =============================================================================
 * Mozhii RAG Data Platform - Raw Data Tab JavaScript
 * =============================================================================
 * Handles all functionality for the RAW DATA tab where collectors
 * submit raw Tamil content for processing.
 * 
 * Features:
 *   - Form validation
 *   - Character counting
 *   - Content submission
 *   - Form clearing
 * =============================================================================
 */

// =============================================================================
// DOM ELEMENTS
// =============================================================================

/**
 * Cache DOM elements for the raw data tab
 * This improves performance by avoiding repeated DOM queries
 */
const RawDataElements = {
    // Form inputs
    filename: null,
    language: null,
    source: null,
    content: null,
    
    // Buttons
    submitBtn: null,
    clearBtn: null,
    
    // Display elements
    charCount: null,
    
    // Initialize element references
    init() {
        this.filename = document.getElementById('raw-filename');
        this.language = document.getElementById('raw-language');
        this.source = document.getElementById('raw-source');
        this.content = document.getElementById('raw-content');
        this.submitBtn = document.getElementById('raw-submit');
        this.clearBtn = document.getElementById('raw-clear');
        this.charCount = document.getElementById('raw-char-count');
    }
};

// =============================================================================
// VALIDATION
// =============================================================================

/**
 * Validate the filename input
 * Only allows letters, numbers, underscores, and hyphens
 * 
 * @param {string} filename - The filename to validate
 * @returns {Object} - Validation result {valid: boolean, error: string}
 */
function validateFilename(filename) {
    // Check if empty
    if (!filename || filename.trim() === '') {
        return { valid: false, error: 'Filename is required' };
    }
    
    // Check format (alphanumeric with underscores and hyphens)
    const pattern = /^[a-zA-Z0-9_-]+$/;
    if (!pattern.test(filename)) {
        return { 
            valid: false, 
            error: 'Filename can only contain letters, numbers, underscores, and hyphens' 
        };
    }
    
    // Check length
    if (filename.length < 3) {
        return { valid: false, error: 'Filename must be at least 3 characters' };
    }
    
    if (filename.length > 50) {
        return { valid: false, error: 'Filename cannot exceed 50 characters' };
    }
    
    return { valid: true };
}

/**
 * Validate the content textarea
 * 
 * @param {string} content - The content to validate
 * @returns {Object} - Validation result {valid: boolean, error: string}
 */
function validateContent(content) {
    // Check if empty
    if (!content || content.trim() === '') {
        return { valid: false, error: 'Content is required' };
    }
    
    // Check minimum length (at least 50 characters for meaningful content)
    if (content.trim().length < 50) {
        return { 
            valid: false, 
            error: 'Content must be at least 50 characters' 
        };
    }
    
    return { valid: true };
}

/**
 * Validate the entire form
 * 
 * @returns {Object} - Validation result {valid: boolean, errors: Array}
 */
function validateRawDataForm() {
    const errors = [];
    
    // Validate filename
    const filenameResult = validateFilename(RawDataElements.filename.value);
    if (!filenameResult.valid) {
        errors.push(filenameResult.error);
    }
    
    // Validate content
    const contentResult = validateContent(RawDataElements.content.value);
    if (!contentResult.valid) {
        errors.push(contentResult.error);
    }
    
    return {
        valid: errors.length === 0,
        errors
    };
}

// =============================================================================
// FORM HANDLERS
// =============================================================================

/**
 * Handle character count update
 * Called whenever the content textarea changes
 */
function updateCharCount() {
    const content = RawDataElements.content.value;
    const count = content.length;
    
    // Update the character count display
    RawDataElements.charCount.textContent = `${count.toLocaleString()} characters`;
    
    // Add warning color if content is too short
    if (count > 0 && count < 50) {
        RawDataElements.charCount.style.color = 'var(--warning)';
    } else {
        RawDataElements.charCount.style.color = 'var(--text-muted)';
    }
}

/**
 * Handle form submission
 * Validates the form and sends data to the API
 */
async function handleRawDataSubmit() {
    // Validate form
    const validation = validateRawDataForm();
    
    if (!validation.valid) {
        // Show first error as toast
        showToast('Validation Error', validation.errors[0], 'error');
        return;
    }
    
    // Disable submit button to prevent double submission
    RawDataElements.submitBtn.disabled = true;
    RawDataElements.submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';
    
    try {
        // Prepare data
        const formData = {
            filename: RawDataElements.filename.value.trim(),
            language: RawDataElements.language.value,
            source: RawDataElements.source.value,
            content: RawDataElements.content.value
        };
        
        // Submit to API
        const response = await api('/api/raw/submit', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        if (response.success) {
            // Show success message
            showToast(
                'Submitted Successfully!', 
                `"${formData.filename}" is now pending admin approval.`,
                'success'
            );
            
            // Clear the form
            clearRawDataForm();
            
            // Refresh admin badge
            refreshAdminData();
            
        } else {
            throw new Error(response.error || 'Submission failed');
        }
        
    } catch (error) {
        // Show error message
        showToast('Submission Failed', error.message, 'error');
        
    } finally {
        // Re-enable submit button
        RawDataElements.submitBtn.disabled = false;
        RawDataElements.submitBtn.innerHTML = '<span class="btn-icon">📤</span> Submit for Review';
    }
}

/**
 * Clear the raw data form
 * Resets all fields to their default values
 */
function clearRawDataForm() {
    RawDataElements.filename.value = '';
    RawDataElements.language.value = 'ta';
    RawDataElements.source.value = 'gov_textbook';
    RawDataElements.content.value = '';
    
    // Reset character count
    updateCharCount();
    
    // Focus on filename field
    RawDataElements.filename.focus();
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

/**
 * Initialize event listeners for the raw data tab
 */
function initRawDataEventListeners() {
    // Content textarea - update character count on input
    RawDataElements.content.addEventListener('input', updateCharCount);
    
    // Submit button click
    RawDataElements.submitBtn.addEventListener('click', handleRawDataSubmit);
    
    // Clear button click
    RawDataElements.clearBtn.addEventListener('click', () => {
        // Confirm before clearing if there's content
        if (RawDataElements.content.value.trim().length > 0) {
            showModal('Clear Form?', 
                '<p>Are you sure you want to clear all fields?</p>',
                [
                    { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
                    { text: 'Clear', class: 'btn-primary', onClick: () => {
                        clearRawDataForm();
                        hideModal();
                    }}
                ]
            );
        } else {
            clearRawDataForm();
        }
    });
    
    // Filename validation on blur
    RawDataElements.filename.addEventListener('blur', () => {
        const result = validateFilename(RawDataElements.filename.value);
        if (!result.valid && RawDataElements.filename.value.length > 0) {
            // Visual feedback - could add error border
            RawDataElements.filename.style.borderColor = 'var(--error)';
        } else {
            RawDataElements.filename.style.borderColor = '';
        }
    });
    
    // Clear error style on focus
    RawDataElements.filename.addEventListener('focus', () => {
        RawDataElements.filename.style.borderColor = '';
    });
    
    // Submit on Ctrl+Enter
    RawDataElements.content.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            handleRawDataSubmit();
        }
    });
}

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize the raw data tab
 * Called when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize element references
    RawDataElements.init();
    
    // Set up event listeners
    initRawDataEventListeners();
    
    // Initialize character count
    updateCharCount();
    
    console.log('📥 Raw Data tab initialized');
});
