/**
 * =============================================================================
 * Mozhii RAG Data Platform - Chunking Tab JavaScript
 * =============================================================================
 * Handles all functionality for the CHUNKING tab where the QA team
 * creates RAG-ready chunks from cleaned content.
 * 
 * This is the MOST IMPORTANT stage as it produces data ready for embedding!
 * 
 * Features:
 *   - List cleaned files available for chunking
 *   - Display source content for reference
 *   - Create chunks with metadata
 *   - Track chunk indices automatically
 *   - Preview chunks before submission
 *   - View existing chunks
 * =============================================================================
 */

// =============================================================================
// DOM ELEMENTS
// =============================================================================

/**
 * Cache DOM elements for the chunking tab
 */
const ChunkingElements = {
    // Panels
    fileList: null,
    sourceContent: null,
    sourceInfo: null,
    chunksList: null,
    
    // Form elements
    chunkText: null,
    chunkHeading: null,
    chunkCategory: null,
    chunkSource: null,
    chunkOverlap: null,
    charCount: null,
    indexDisplay: null,
    selectedFile: null,
    
    // Buttons
    refreshBtn: null,
    previewBtn: null,
    submitBtn: null,
    
    // Initialize element references
    init() {
        this.fileList = document.getElementById('chunking-file-list');
        this.sourceContent = document.getElementById('chunking-source-content');
        this.sourceInfo = document.getElementById('chunking-source-info');
        this.chunksList = document.getElementById('chunks-list');
        this.chunkText = document.getElementById('chunk-text');
        this.chunkHeading = document.getElementById('chunk-heading');
        this.chunkCategory = document.getElementById('chunk-category');
        this.chunkSource = document.getElementById('chunk-source');
        this.chunkOverlap = document.getElementById('chunk-overlap');
        this.charCount = document.getElementById('chunk-char-count');
        this.indexDisplay = document.getElementById('chunk-index-display');
        this.selectedFile = document.getElementById('chunking-selected-file');
        this.refreshBtn = document.getElementById('chunking-refresh');
        this.previewBtn = document.getElementById('chunk-preview');
        this.submitBtn = document.getElementById('chunk-submit');
    }
};

// =============================================================================
// STATE
// =============================================================================

/**
 * Local state for the chunking tab
 */
const ChunkingState = {
    files: [],              // List of available cleaned files
    selectedFile: null,     // Currently selected file object
    selectedFilename: null, // Name of selected file
    chunks: [],             // Existing chunks for selected file
    nextIndex: 1            // Next chunk index
};

// =============================================================================
// FILE LIST FUNCTIONS
// =============================================================================

/**
 * Refresh the list of cleaned files available for chunking
 */
async function refreshChunkingFiles() {
    try {
        // Show loading state
        ChunkingElements.fileList.innerHTML = `
            <div class="empty-state">
                <p>Loading files...</p>
            </div>
        `;
        
        // Fetch files from API
        const response = await api('/api/chunking/cleaned-files');
        
        if (response.success) {
            ChunkingState.files = response.files;
            renderChunkingFileList();
        } else {
            throw new Error(response.error || 'Failed to load files');
        }
        
    } catch (error) {
        console.error('Error loading chunking files:', error);
        ChunkingElements.fileList.innerHTML = `
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
function renderChunkingFileList() {
    const files = ChunkingState.files;
    
    if (files.length === 0) {
        ChunkingElements.fileList.innerHTML = `
            <div class="empty-state">
                <p>No cleaned files available</p>
                <span>Complete cleaning in the CLEANING tab first</span>
            </div>
        `;
        return;
    }
    
    // Create file list HTML
    ChunkingElements.fileList.innerHTML = files.map(file => `
        <div class="file-item ${ChunkingState.selectedFilename === file.filename ? 'selected' : ''}" 
             data-filename="${file.filename}"
             onclick="selectChunkingFile('${file.filename}')">
            <span class="file-icon">📋</span>
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">
                    ${file.total_chunks} chunks 
                    ${file.pending_chunks > 0 ? `(${file.pending_chunks} pending)` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// =============================================================================
// FILE SELECTION
// =============================================================================

/**
 * Handle file selection for chunking
 * 
 * @param {string} filename - Name of the file to select
 */
async function selectChunkingFile(filename) {
    // Find the file in our state
    const file = ChunkingState.files.find(f => f.filename === filename);
    
    if (!file) {
        console.error('File not found:', filename);
        return;
    }
    
    // Update state
    ChunkingState.selectedFile = file;
    ChunkingState.selectedFilename = filename;
    
    // Update hidden field
    ChunkingElements.selectedFile.value = filename;
    
    // Update file list selection
    document.querySelectorAll('#chunking-file-list .file-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.filename === filename);
    });
    
    // Update source content display
    ChunkingElements.sourceContent.innerHTML = `
        <div class="tamil-text">${escapeHtml(file.content)}</div>
    `;
    
    // Update source info
    ChunkingElements.sourceInfo.textContent = `${file.content_length.toLocaleString()} chars | ${file.language.toUpperCase()}`;
    
    // Fetch existing chunks
    await loadChunksForFile(filename);
    
    // Enable form elements
    enableChunkingForm();
    
    // Set source from file
    ChunkingElements.chunkSource.value = file.source || '';
    
    // Show info toast
    showToast('File Selected', `Selected "${filename}" for chunking`, 'info', 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load existing chunks for a file
 * 
 * @param {string} filename - Name of the file
 */
async function loadChunksForFile(filename) {
    try {
        const response = await api(`/api/chunking/chunks/${filename}`);
        
        if (response.success) {
            ChunkingState.chunks = response.chunks;
            ChunkingState.nextIndex = response.count + 1;
            
            // Update index display
            ChunkingElements.indexDisplay.textContent = `Chunk #${ChunkingState.nextIndex}`;
            
            // Render chunks list
            renderChunksList();
        }
        
    } catch (error) {
        console.error('Error loading chunks:', error);
        ChunkingState.chunks = [];
        ChunkingState.nextIndex = 1;
    }
}

/**
 * Render the list of existing chunks
 */
function renderChunksList() {
    const chunks = ChunkingState.chunks;
    
    if (chunks.length === 0) {
        ChunkingElements.chunksList.innerHTML = `
            <div class="empty-state small">
                <p>No chunks yet</p>
            </div>
        `;
        return;
    }
    
    ChunkingElements.chunksList.innerHTML = chunks.map(chunk => `
        <div class="chunk-item">
            <div class="chunk-item-main">
                <span class="chunk-id">#${chunk.chunk_index}</span>
                <span class="chunk-preview">${chunk.text.substring(0, 50)}...</span>
                <span class="file-status ${chunk.status || 'pending'}">${chunk.status || 'pending'}</span>
                ${(chunk.status || 'pending') === 'pending' ? `<button class="btn btn-error btn-sm chunk-remove-btn" data-index="${chunk.chunk_index}" title="Remove chunk">✕</button>` : ''}
            </div>
            <div class="chunk-item-meta">
                ${chunk.heading ? `<span class="chunk-meta-tag">📝 ${chunk.heading}</span>` : ''}
                <span class="chunk-meta-tag">📂 ${chunk.category || 'N/A'}</span>
                <span class="chunk-meta-tag">🔗 ${chunk.source || 'N/A'}</span>
            </div>
        </div>
    `).join('');

    // Attach remove handlers
    ChunkingElements.chunksList.querySelectorAll('.chunk-remove-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const chunkIndex = parseInt(btn.dataset.index);
            confirmRemoveChunk(chunkIndex);
        });
    });
}

/**
 * Confirm and remove a pending chunk
 */
function confirmRemoveChunk(chunkIndex) {
    showModal('Remove Chunk', `<p>Are you sure you want to remove Chunk #${chunkIndex}?</p>`, [
        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
        { text: 'Remove', class: 'btn-error', onClick: () => {
            hideModal();
            removeChunk(chunkIndex);
        }}
    ]);
}

/**
 * Delete a pending chunk via API
 */
async function removeChunk(chunkIndex) {
    try {
        const response = await api(`/api/chunking/chunk/${ChunkingState.selectedFilename}/${chunkIndex}`, {
            method: 'DELETE'
        });

        if (response.success) {
            showToast('Chunk Removed', `Chunk #${chunkIndex} has been removed.`, 'success');
            await loadChunksForFile(ChunkingState.selectedFilename);
            await refreshChunkingFiles();
            refreshAdminData();
        } else {
            throw new Error(response.error || 'Failed to remove chunk');
        }
    } catch (error) {
        showToast('Remove Failed', error.message, 'error');
    }
}

// =============================================================================
// FORM HANDLING
// =============================================================================

/**
 * Enable the chunking form elements
 */
function enableChunkingForm() {
    ChunkingElements.chunkText.disabled = false;
    ChunkingElements.chunkHeading.disabled = false;
    ChunkingElements.chunkCategory.disabled = false;
    ChunkingElements.chunkSource.disabled = false;
    ChunkingElements.chunkOverlap.disabled = false;
    ChunkingElements.previewBtn.disabled = false;
    ChunkingElements.submitBtn.disabled = false;
}

/**
 * Disable the chunking form elements
 */
function disableChunkingForm() {
    ChunkingElements.chunkText.disabled = true;
    ChunkingElements.chunkHeading.disabled = true;
    ChunkingElements.chunkCategory.disabled = true;
    ChunkingElements.chunkSource.disabled = true;
    ChunkingElements.chunkOverlap.disabled = true;
    ChunkingElements.previewBtn.disabled = true;
    ChunkingElements.submitBtn.disabled = true;
}

/**
 * Update character count for chunk text
 */
function updateChunkCharCount() {
    const content = ChunkingElements.chunkText.value;
    const count = content.length;
    ChunkingElements.charCount.textContent = `${count.toLocaleString()} characters`;
}

/**
 * Clear the chunk form
 */
function clearChunkForm() {
    ChunkingElements.chunkText.value = '';
    ChunkingElements.chunkHeading.value = '';
    ChunkingElements.chunkOverlap.value = '';
    updateChunkCharCount();
}

/**
 * Generate chunk ID based on metadata
 * 
 * @returns {string} - Generated chunk ID
 */
function generateChunkId() {
    const lang = ChunkingState.selectedFile?.language || 'ta';
    const cat = ChunkingElements.chunkCategory.value.substring(0, 3);
    const file = ChunkingState.selectedFilename?.replace(/_/g, '').substring(0, 10) || 'file';
    const index = ChunkingState.nextIndex;
    
    return `${lang}_${cat}_${file}_${String(index).padStart(2, '0')}`;
}

// =============================================================================
// PREVIEW FUNCTIONALITY
// =============================================================================

/**
 * Preview the chunk before submission
 */
function previewChunk() {
    // Validate
    if (!ChunkingElements.chunkText.value.trim()) {
        showToast('No Content', 'Please enter chunk text first', 'warning');
        return;
    }
    
    const chunkId = generateChunkId();
    
    // Build preview object
    const preview = {
        chunk_id: chunkId,
        heading: ChunkingElements.chunkHeading.value.trim() || undefined,
        text: ChunkingElements.chunkText.value.trim(),
        language: ChunkingState.selectedFile?.language || 'ta',
        category: ChunkingElements.chunkCategory.value,
        source: ChunkingElements.chunkSource.value || ChunkingState.selectedFile?.source || 'unknown',
        chunk_index: ChunkingState.nextIndex,
        source_file: ChunkingState.selectedFilename,
        overlap_reference: ChunkingElements.chunkOverlap.value.trim()
    };
    
    // Show preview modal
    showModal('Chunk Preview', `
        <div style="background: var(--bg-elevated); padding: 1rem; border-radius: 0.5rem; font-family: monospace; font-size: 0.875rem; white-space: pre-wrap; overflow-x: auto;">
${JSON.stringify(preview, null, 2)}
        </div>
    `, [
        { text: 'Close', class: 'btn-secondary', onClick: hideModal },
        { text: 'Submit Chunk', class: 'btn-primary', onClick: () => {
            hideModal();
            handleChunkSubmit();
        }}
    ]);
}

// =============================================================================
// SUBMISSION
// =============================================================================

/**
 * Submit a new chunk
 */
async function handleChunkSubmit() {
    // Validate file selection
    if (!ChunkingState.selectedFilename) {
        showToast('No File Selected', 'Please select a file first', 'warning');
        return;
    }
    
    // Validate chunk text
    const text = ChunkingElements.chunkText.value.trim();
    if (!text) {
        showToast('No Content', 'Please enter chunk text', 'warning');
        return;
    }
    
    if (text.length < 20) {
        showToast('Content Too Short', 'Chunk text must be at least 20 characters', 'warning');
        return;
    }
    
    // Disable submit button
    ChunkingElements.submitBtn.disabled = true;
    ChunkingElements.submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Adding...';
    
    try {
        // Prepare chunk data
        const chunkData = {
            filename: ChunkingState.selectedFilename,
            text: text,
            heading: ChunkingElements.chunkHeading.value.trim() || undefined,
            category: ChunkingElements.chunkCategory.value,
            source: ChunkingElements.chunkSource.value || undefined,
            overlap_reference: ChunkingElements.chunkOverlap.value.trim() || undefined
        };
        
        // Submit to API
        const response = await api('/api/chunking/submit', {
            method: 'POST',
            body: JSON.stringify(chunkData)
        });
        
        if (response.success) {
            showToast(
                'Chunk Created!',
                `Chunk #${response.chunk_index} added. Pending admin approval.`,
                'success'
            );
            
            // Store last chunk text as overlap reference for next chunk
            const lastChunkEnd = text.slice(-100);
            
            // Clear form
            clearChunkForm();
            
            // Set overlap reference for next chunk
            ChunkingElements.chunkOverlap.value = lastChunkEnd;
            
            // Reload chunks
            await loadChunksForFile(ChunkingState.selectedFilename);
            
            // Refresh file list to update counts
            await refreshChunkingFiles();
            
            // Refresh admin badge
            refreshAdminData();
            
        } else {
            throw new Error(response.error || 'Submission failed');
        }
        
    } catch (error) {
        showToast('Submission Failed', error.message, 'error');
        
    } finally {
        // Re-enable submit button
        ChunkingElements.submitBtn.disabled = false;
        ChunkingElements.submitBtn.innerHTML = '<span class="btn-icon">➕</span> Add Chunk';
    }
}

// =============================================================================
// TEXT SELECTION HELPER
// =============================================================================

/**
 * Handle text selection from source content
 * Automatically copies selected text to chunk textarea
 */
function setupTextSelection() {
    ChunkingElements.sourceContent.addEventListener('mouseup', () => {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        
        if (selectedText && selectedText.length > 10) {
            // Ask user if they want to use this selection
            const existingText = ChunkingElements.chunkText.value;
            
            if (existingText && existingText.length > 0) {
                // Append or replace?
                showModal('Add Selected Text', 
                    '<p>Do you want to append or replace the current chunk text?</p>',
                    [
                        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
                        { text: 'Append', class: 'btn-primary', onClick: () => {
                            ChunkingElements.chunkText.value = existingText + '\n\n' + selectedText;
                            updateChunkCharCount();
                            hideModal();
                        }},
                        { text: 'Replace', class: 'btn-error', onClick: () => {
                            ChunkingElements.chunkText.value = selectedText;
                            updateChunkCharCount();
                            hideModal();
                        }}
                    ]
                );
            } else {
                // Just set it
                ChunkingElements.chunkText.value = selectedText;
                updateChunkCharCount();
                showToast('Text Added', 'Selected text added to chunk', 'success', 2000);
            }
        }
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

/**
 * Initialize event listeners for the chunking tab
 */
function initChunkingEventListeners() {
    // Refresh button
    ChunkingElements.refreshBtn.addEventListener('click', refreshChunkingFiles);
    
    // Preview button
    ChunkingElements.previewBtn.addEventListener('click', previewChunk);
    
    // Submit button
    ChunkingElements.submitBtn.addEventListener('click', handleChunkSubmit);
    
    // Character count on input
    ChunkingElements.chunkText.addEventListener('input', updateChunkCharCount);
    
    // Text selection helper
    setupTextSelection();
    
    // Submit on Ctrl+Enter
    ChunkingElements.chunkText.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            handleChunkSubmit();
        }
    });
}

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize the chunking tab
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize element references
    ChunkingElements.init();
    
    // Set up event listeners
    initChunkingEventListeners();
    
    console.log('🧩 Chunking tab initialized');
});
