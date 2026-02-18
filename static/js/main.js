/**
 * =============================================================================
 * Mozhii RAG Data Platform - Main JavaScript
 * =============================================================================
 * This is the main JavaScript file that initializes the application and
 * provides shared utilities used across all tabs.
 * 
 * Responsibilities:
 *   - Tab switching functionality
 *   - Admin sidebar toggle
 *   - Toast notifications
 *   - Modal dialogs
 *   - API helper functions
 *   - Global state management
 * =============================================================================
 */

// =============================================================================
// GLOBAL STATE
// =============================================================================

/**
 * Application state object
 * Stores global data that needs to be shared across modules
 */
const AppState = {
    currentTab: 'raw',           // Current active tab
    config: null,                // Configuration from server
    pendingCounts: {             // Pending items counts for badge
        raw: 0,
        cleaned: 0,
        chunked: 0
    }
};

// =============================================================================
// API HELPER FUNCTIONS
// =============================================================================

/**
 * Make an API request to the backend
 * 
 * @param {string} endpoint - API endpoint (e.g., '/api/raw/submit')
 * @param {Object} options - Fetch options (method, body, etc.)
 * @returns {Promise<Object>} - JSON response from the API
 * 
 * @example
 * const data = await api('/api/raw/submit', {
 *     method: 'POST',
 *     body: JSON.stringify({ filename: 'test', content: '...' })
 * });
 */
async function api(endpoint, options = {}) {
    // Set default headers
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    // Merge options
    const fetchOptions = { ...defaultOptions, ...options };
    
    try {
        // Make the request
        const response = await fetch(endpoint, fetchOptions);
        
        // Parse JSON response
        const data = await response.json();
        
        // Check for HTTP errors
        if (!response.ok) {
            throw new Error(data.error || `HTTP error ${response.status}`);
        }
        
        return data;
        
    } catch (error) {
        // Re-throw with more context
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// =============================================================================
// TOAST NOTIFICATIONS
// =============================================================================

/**
 * Show a toast notification
 * 
 * @param {string} title - Toast title
 * @param {string} message - Toast message
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in milliseconds (default: 5000)
 * 
 * @example
 * showToast('Success!', 'Data saved successfully', 'success');
 */
function showToast(title, message, type = 'info', duration = 5000) {
    // Get or create toast container
    const container = document.getElementById('toastContainer');
    
    // Define icons for each type
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    
    // Add to container
    container.appendChild(toast);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideIn 0.2s ease reverse';
            setTimeout(() => toast.remove(), 200);
        }
    }, duration);
}

// =============================================================================
// MODAL DIALOGS
// =============================================================================

/**
 * Show a modal dialog
 * 
 * @param {string} title - Modal title
 * @param {string} content - HTML content for the modal body
 * @param {Array} buttons - Array of button objects {text, class, onClick}
 * 
 * @example
 * showModal('Confirm Delete', 'Are you sure?', [
 *     { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
 *     { text: 'Delete', class: 'btn-error', onClick: doDelete }
 * ]);
 */
function showModal(title, content, buttons = []) {
    const overlay = document.getElementById('modalOverlay');
    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');
    const footerEl = document.getElementById('modal-footer');
    
    // Set content
    titleEl.textContent = title;
    bodyEl.innerHTML = content;
    
    // Create buttons
    footerEl.innerHTML = '';
    buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = `btn ${btn.class || 'btn-secondary'}`;
        button.textContent = btn.text;
        button.onclick = btn.onClick;
        footerEl.appendChild(button);
    });
    
    // Show modal
    overlay.classList.add('visible');
}

/**
 * Hide the modal dialog
 */
function hideModal() {
    const overlay = document.getElementById('modalOverlay');
    overlay.classList.remove('visible');
}

// =============================================================================
// TAB SWITCHING
// =============================================================================

/**
 * Initialize tab switching functionality
 * 
 * Tabs are controlled by data-tab attribute on buttons
 * and corresponding panel IDs (e.g., #raw-panel)
 */
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // Update active button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update active panel
            tabPanels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === `${targetTab}-panel`) {
                    panel.classList.add('active');
                }
            });
            
            // Update state
            AppState.currentTab = targetTab;
            
            // Trigger tab-specific refresh
            if (targetTab === 'cleaning') {
                refreshCleaningFiles();
            } else if (targetTab === 'chunking') {
                refreshChunkingFiles();
            }
        });
    });
}

// =============================================================================
// ADMIN SIDEBAR
// =============================================================================

/**
 * Initialize admin sidebar toggle functionality
 */
function initAdminSidebar() {
    const toggleBtn = document.getElementById('adminToggle');
    const sidebar = document.getElementById('adminSidebar');
    const closeBtn = document.getElementById('adminClose');
    const overlay = document.getElementById('sidebarOverlay');
    
    // Open sidebar
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.add('open');
        overlay.classList.add('visible');
        refreshAdminData();
    });
    
    // Close sidebar
    closeBtn.addEventListener('click', closeSidebar);
    overlay.addEventListener('click', closeSidebar);
    
    function closeSidebar() {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
    }
}

/**
 * Refresh admin panel data
 * Fetches all pending items and updates the UI
 */
async function refreshAdminData() {
    try {
        // Fetch pending items from API
        const data = await api('/api/admin/pending');
        
        if (data.success) {
            // Update pending counts
            AppState.pendingCounts = {
                raw: data.totals.raw,
                cleaned: data.totals.cleaned,
                chunked: data.totals.chunked
            };
            
            // Update badge
            const totalPending = data.totals.total;
            const badge = document.getElementById('pendingBadge');
            badge.textContent = totalPending;
            badge.setAttribute('data-count', totalPending);
            
            // Update stats
            document.getElementById('stat-pending').textContent = totalPending;
            
            // Fetch approved stats
            const statsData = await api('/api/admin/stats');
            if (statsData.success) {
                document.getElementById('stat-approved').textContent = statsData.stats.totals.approved;
            }
            
            // Render pending lists
            renderPendingList('pending-raw-list', data.pending.raw, 'raw');
            renderPendingList('pending-cleaned-list', data.pending.cleaned, 'cleaned');
            renderPendingChunks('pending-chunks-list', data.pending.chunked);
        }
        
    } catch (error) {
        console.error('Failed to refresh admin data:', error);
    }
}

/**
 * Render a list of pending items with edit buttons
 * 
 * @param {string} containerId - ID of the container element
 * @param {Array} items - Array of pending item objects
 * @param {string} type - Type: 'raw' or 'cleaned'
 */
function renderPendingList(containerId, items, type) {
    const container = document.getElementById(containerId);
    
    if (!items || items.length === 0) {
        container.innerHTML = '<div class="empty-state small">No pending items</div>';
        return;
    }
    
    container.innerHTML = items.map(item => `
        <div class="pending-item" data-filename="${item.filename}">
            <span class="pending-item-name">${item.filename}</span>
            <div class="pending-item-actions">
                <button class="btn btn-sm btn-secondary" onclick="editItem('${type}', '${item.filename}')" title="Edit">✏️</button>
                <button class="btn btn-sm btn-success" onclick="approveItem('${type}', '${item.filename}')" title="Approve">✓</button>
                <button class="btn btn-sm btn-error" onclick="rejectItem('${type}', '${item.filename}')" title="Reject">✕</button>
            </div>
        </div>
    `).join('');
}

/**
 * Render pending chunks grouped by file
 * 
 * @param {string} containerId - ID of the container element
 * @param {Object} chunkedFiles - Object with filename keys and chunk arrays
 */
function renderPendingChunks(containerId, chunkedFiles) {
    const container = document.getElementById(containerId);
    
    if (!chunkedFiles || Object.keys(chunkedFiles).length === 0) {
        container.innerHTML = '<div class="empty-state small">No pending chunks</div>';
        return;
    }
    
    let html = '';
    for (const [filename, chunks] of Object.entries(chunkedFiles)) {
        html += `
            <div class="pending-item" data-filename="${filename}">
                <span class="pending-item-name">${filename} (${chunks.length} chunks)</span>
                <div class="pending-item-actions">
                    <button class="btn btn-sm btn-success" onclick="approveAllChunks('${filename}')" title="Approve All">✓</button>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

/**
 * Approve a pending item
 * 
 * @param {string} type - Type: 'raw' or 'cleaned'
 * @param {string} filename - Name of the file to approve
 */
async function approveItem(type, filename) {
    try {
        const data = await api('/api/admin/approve', {
            method: 'POST',
            body: JSON.stringify({ type, filename })
        });
        
        if (data.success) {
            showToast('Approved!', `${filename} has been approved`, 'success');
            refreshAdminData();
        }
        
    } catch (error) {
        showToast('Error', `Failed to approve: ${error.message}`, 'error');
    }
}

/**
 * Reject a pending item
 * 
 * @param {string} type - Type: 'raw' or 'cleaned'
 * @param {string} filename - Name of the file to reject
 */
async function rejectItem(type, filename) {
    showModal('Confirm Rejection', `
        <p>Are you sure you want to reject <strong>${filename}</strong>?</p>
        <p class="text-muted">This action cannot be undone.</p>
    `, [
        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
        { text: 'Reject', class: 'btn-error', onClick: async () => {
            try {
                const data = await api('/api/admin/reject', {
                    method: 'POST',
                    body: JSON.stringify({ type, filename })
                });
                
                if (data.success) {
                    showToast('Rejected', `${filename} has been rejected`, 'warning');
                    hideModal();
                    refreshAdminData();
                }
            } catch (error) {
                showToast('Error', `Failed to reject: ${error.message}`, 'error');
            }
        }}
    ]);
}

/**
 * Approve all chunks for a file
 * 
 * @param {string} filename - Name of the source file
 */
async function approveAllChunks(filename) {
    try {
        const data = await api('/api/admin/approve-all', {
            method: 'POST',
            body: JSON.stringify({ type: 'chunks', filename })
        });
        
        if (data.success) {
            showToast('Approved!', `All chunks for ${filename} approved`, 'success');
            refreshAdminData();
        }
        
    } catch (error) {
        showToast('Error', `Failed to approve chunks: ${error.message}`, 'error');
    }
}

// =============================================================================
// EDIT ITEM FUNCTIONALITY
// =============================================================================

/**
 * Open the edit modal for a pending item
 * 
 * @param {string} type - Type: 'raw' or 'cleaned'
 * @param {string} filename - Name of the file to edit
 */
async function editItem(type, filename) {
    try {
        // Show loading state
        const editModal = document.getElementById('editModalOverlay');
        const editContent = document.getElementById('edit-content');
        const editCharCount = document.getElementById('edit-char-count');
        
        editContent.value = 'Loading...';
        editContent.disabled = true;
        editModal.classList.add('visible');
        
        // Fetch the item content
        const data = await api(`/api/admin/pending/${type}/${filename}`);
        
        if (data.success) {
            // Populate the edit modal
            document.getElementById('edit-type-badge').textContent = type.charAt(0).toUpperCase() + type.slice(1);
            document.getElementById('edit-type-badge').className = `edit-type-badge ${type}`;
            document.getElementById('edit-filename').textContent = filename;
            document.getElementById('edit-item-type').value = type;
            document.getElementById('edit-item-filename').value = filename;
            
            editContent.value = data.item.content;
            editContent.disabled = false;
            editCharCount.textContent = `${data.item.content.length} characters`;
            
            // Update char count on input
            editContent.oninput = () => {
                editCharCount.textContent = `${editContent.value.length} characters`;
            };
        } else {
            showToast('Error', 'Failed to load item content', 'error');
            hideEditModal();
        }
        
    } catch (error) {
        showToast('Error', `Failed to load: ${error.message}`, 'error');
        hideEditModal();
    }
}

/**
 * Hide the edit modal
 */
function hideEditModal() {
    const editModal = document.getElementById('editModalOverlay');
    editModal.classList.remove('visible');
}

/**
 * Save edits to a pending item
 * 
 * @param {boolean} andApprove - Whether to also approve after saving
 */
async function saveEdit(andApprove = false) {
    try {
        const type = document.getElementById('edit-item-type').value;
        const filename = document.getElementById('edit-item-filename').value;
        const content = document.getElementById('edit-content').value;
        
        if (!content.trim()) {
            showToast('Error', 'Content cannot be empty', 'error');
            return;
        }
        
        // Save the edits
        const saveResult = await api('/api/admin/edit', {
            method: 'POST',
            body: JSON.stringify({ type, filename, content })
        });
        
        if (saveResult.success) {
            showToast('Saved!', `${filename} has been updated`, 'success');
            
            // If also approving
            if (andApprove) {
                const approveResult = await api('/api/admin/approve', {
                    method: 'POST',
                    body: JSON.stringify({ type, filename })
                });
                
                if (approveResult.success) {
                    showToast('Approved!', `${filename} has been approved`, 'success');
                }
            }
            
            hideEditModal();
            refreshAdminData();
        } else {
            showToast('Error', saveResult.error || 'Failed to save', 'error');
        }
        
    } catch (error) {
        showToast('Error', `Failed to save: ${error.message}`, 'error');
    }
}

/**
 * Initialize edit modal handlers
 */
function initEditModal() {
    const closeBtn = document.getElementById('editModalClose');
    const cancelBtn = document.getElementById('edit-cancel');
    const saveBtn = document.getElementById('edit-save');
    const saveApproveBtn = document.getElementById('edit-save-approve');
    const overlay = document.getElementById('editModalOverlay');
    
    if (closeBtn) closeBtn.addEventListener('click', hideEditModal);
    if (cancelBtn) cancelBtn.addEventListener('click', hideEditModal);
    if (saveBtn) saveBtn.addEventListener('click', () => saveEdit(false));
    if (saveApproveBtn) saveApproveBtn.addEventListener('click', () => saveEdit(true));
    
    // Close on overlay click
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                hideEditModal();
            }
        });
    }
}

// =============================================================================
// HUGGINGFACE CONFIGURATION (OLD - TO BE REMOVED)
// =============================================================================

/**
 * Toggle HuggingFace configuration section visibility
 */
function toggleHFConfig() {
    const content = document.getElementById('hf-config-content');
    const icon = document.getElementById('hf-toggle-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.textContent = '▲';
    } else {
        content.style.display = 'none';
        icon.textContent = '▼';
    }
}

/**
 * Load HuggingFace configuration from server
 */
async function loadHFConfig() {
    try {
        const data = await api('/api/admin/hf-config');
        
        if (data.success) {
            const config = data.config;
            const statusIndicator = document.getElementById('hf-status-indicator');
            const statusText = document.getElementById('hf-status-text');
            
            if (config.is_configured) {
                statusIndicator.className = 'status-indicator connected';
                statusText.textContent = 'Connected';
            } else if (config.has_token) {
                statusIndicator.className = 'status-indicator partial';
                statusText.textContent = 'Token set, configure repos';
            } else {
                statusIndicator.className = 'status-indicator disconnected';
                statusText.textContent = 'Not configured';
            }
            
            // Set repo values if available
            if (config.repos && config.repos.raw) {
                document.getElementById('hf-repo').value = config.repos.raw;
            }
        }
    } catch (error) {
        console.error('Failed to load HF config:', error);
    }
}

/**
 * Save HuggingFace configuration
 */
async function saveHFConfig() {
    try {
        const token = document.getElementById('hf-token').value;
        const repo = document.getElementById('hf-repo').value;
        
        if (!repo) {
            showToast('Error', 'Please enter a repository name', 'error');
            return;
        }
        
        const configData = {
            repos: {
                raw: repo,
                cleaned: repo,
                chunked: repo
            }
        };
        
        if (token) {
            configData.token = token;
        }
        
        const result = await api('/api/admin/hf-config', {
            method: 'POST',
            body: JSON.stringify(configData)
        });
        
        if (result.success) {
            showToast('Saved!', 'HuggingFace settings updated', 'success');
            document.getElementById('hf-token').value = ''; // Clear token field for security
            loadHFConfig(); // Refresh status
        } else {
            showToast('Error', result.error || 'Failed to save settings', 'error');
        }
        
    } catch (error) {
        showToast('Error', `Failed to save: ${error.message}`, 'error');
    }
}

/**
 * Push approved data to HuggingFace
 */
async function pushToHuggingFace() {
    try {
        showToast('Uploading...', 'Pushing data to HuggingFace', 'info');
        
        const result = await api('/api/admin/push-to-hf', {
            method: 'POST',
            body: JSON.stringify({ type: 'all' })
        });
        
        if (result.success) {
            const totalUploaded = result.results.raw.uploaded + 
                                  result.results.cleaned.uploaded + 
                                  result.results.chunked.uploaded;
            showToast('Success!', `Pushed ${totalUploaded} files to HuggingFace`, 'success');
        } else {
            showToast('Error', result.error || 'Push failed', 'error');
        }
        
    } catch (error) {
        showToast('Error', `Push failed: ${error.message}`, 'error');
    }
}

/**
 * Initialize HuggingFace configuration handlers
 */
function initHFConfig() {
    const sectionHeader = document.getElementById('hf-section-header');
    const saveBtn = document.getElementById('save-hf-config');
    const syncBtn = document.getElementById('sync-hf-btn');
    
    if (sectionHeader) {
        sectionHeader.addEventListener('click', toggleHFConfig);
    }
    
    if (saveBtn) {
        saveBtn.addEventListener('click', saveHFConfig);
    }
    
    if (syncBtn) {
        syncBtn.addEventListener('click', pushToHuggingFace);
    }
    
    // Load initial config
    loadHFConfig();
}

// =============================================================================
// EDIT ITEM FUNCTIONALITY
// =============================================================================

/**
 * Open edit modal for a pending item
 * 
 * @param {string} type - Type: 'raw' or 'cleaned'
 * @param {string} filename - Name of the file to edit
 */
async function editItem(type, filename) {
    try {
        // Fetch item data
        const data = await api(`/api/admin/item?type=${type}&filename=${filename}`);
        
        if (!data.success) {
            showToast('Error', 'Failed to load item', 'error');
            return;
        }
        
        // Show edit modal
        const modalContent = `
            <div class="edit-form">
                <div class="form-group">
                    <label>Filename</label>
                    <input type="text" value="${filename}" disabled class="input-disabled">
                </div>
                <div class="form-group">
                    <label>
                        Content
                        <span class="char-count">${data.content.length} characters</span>
                    </label>
                    <textarea id="edit-content" rows="15" class="tamil-text">${data.content}</textarea>
                </div>
            </div>
        `;
        
        showModal(`Edit ${type} - ${filename}`, modalContent, [
            { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
            { text: 'Save', class: 'btn-primary', onClick: async () => {
                const newContent = document.getElementById('edit-content').value;
                
                if (!newContent.trim()) {
                    showToast('Error', 'Content cannot be empty', 'error');
                    return;
                }
                
                try {
                    const updateData = await api('/api/admin/update', {
                        method: 'POST',
                        body: JSON.stringify({ type, filename, content: newContent })
                    });
                    
                    if (updateData.success) {
                        showToast('Saved!', `${filename} has been updated`, 'success');
                        hideModal();
                        refreshAdminData();
                    } else {
                        showToast('Error', updateData.error || 'Failed to save', 'error');
                    }
                } catch (error) {
                    showToast('Error', `Failed to save: ${error.message}`, 'error');
                }
            }}
        ]);
        
        // Update char count on input
        const contentArea = document.getElementById('edit-content');
        const charCount = document.querySelector('.char-count');
        contentArea.addEventListener('input', () => {
            charCount.textContent = `${contentArea.value.length} characters`;
        });
        
    } catch (error) {
        showToast('Error', `Failed to load: ${error.message}`, 'error');
    }
}

// =============================================================================
// HUGGINGFACE PUSH FUNCTIONALITY
// =============================================================================

/**
 * Push approved data to HuggingFace
 */
async function pushToHuggingFace() {
    const hfToken = document.getElementById('hf-token-input').value.trim();
    const hfRawRepo = document.getElementById('hf-raw-repo-input').value.trim();
    const hfCleanedRepo = document.getElementById('hf-cleaned-repo-input').value.trim();
    const hfChunkedRepo = document.getElementById('hf-chunked-repo-input').value.trim();
    
    if (!hfToken) {
        showToast('Error', 'Please enter your HuggingFace token', 'error');
        return;
    }
    
    if (!hfRawRepo || !hfCleanedRepo || !hfChunkedRepo) {
        showToast('Error', 'Please enter all three repository names', 'error');
        return;
    }
    
    // Confirm before pushing
    showModal('Push to HuggingFace', `
        <p>Ready to push approved data to:</p>
        <ul style="text-align:left;margin:0.5rem 0;">
            <li><strong>Raw:</strong> ${hfRawRepo}</li>
            <li><strong>Cleaned:</strong> ${hfCleanedRepo}</li>
            <li><strong>Chunked:</strong> ${hfChunkedRepo}</li>
        </ul>
    `, [
        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
        { text: 'Push', class: 'btn-primary', onClick: async () => {
            hideModal();
            
            // Show progress toast
            showToast('Uploading...', 'Pushing data to HuggingFace', 'info', 10000);
            
            try {
                const data = await api('/api/admin/push-to-hf', {
                    method: 'POST',
                    body: JSON.stringify({
                        type: 'all',
                        hf_token: hfToken,
                        raw_repo: hfRawRepo,
                        cleaned_repo: hfCleanedRepo,
                        chunked_repo: hfChunkedRepo
                    })
                });
                
                if (data.success) {
                    const totalUploaded = data.totals.uploaded;
                    const totalFailed = data.totals.failed;
                    
                    showToast(
                        'Push Complete!', 
                        `Uploaded ${totalUploaded} files${totalFailed > 0 ? `, ${totalFailed} failed` : ''}`,
                        totalFailed > 0 ? 'warning' : 'success'
                    );
                    
                    // Show detailed results
                    const resultsHtml = `
                        <div class="push-results">
                            <p><strong>Upload Results:</strong></p>
                            <ul>
                                <li>Raw: ${data.results.raw.uploaded} uploaded, ${data.results.raw.failed} failed</li>
                                <li>Cleaned: ${data.results.cleaned.uploaded} uploaded, ${data.results.cleaned.failed} failed</li>
                                <li>Chunks: ${data.results.chunked.uploaded} uploaded, ${data.results.chunked.failed} failed</li>
                            </ul>
                        </div>
                    `;
                    
                    showModal('Upload Complete', resultsHtml, [
                        { text: 'OK', class: 'btn-primary', onClick: hideModal }
                    ]);
                } else {
                    showToast('Error', data.error || 'Failed to push to HuggingFace', 'error');
                }
                
            } catch (error) {
                showToast('Error', `Failed to push: ${error.message}`, 'error');
            }
        }}
    ]);
}

/**
 * Initialize HuggingFace configuration handlers
 */
function initHFConfig() {
    const syncBtn = document.getElementById('sync-hf-btn');
    
    if (syncBtn) {
        syncBtn.addEventListener('click', pushToHuggingFace);
    }
    
    // Load saved values from localStorage
    const savedToken = localStorage.getItem('hf_token');
    const savedRawRepo = localStorage.getItem('hf_raw_repo');
    const savedCleanedRepo = localStorage.getItem('hf_cleaned_repo');
    const savedChunkedRepo = localStorage.getItem('hf_chunked_repo');
    
    if (savedToken) {
        document.getElementById('hf-token-input').value = savedToken;
    }
    if (savedRawRepo) {
        document.getElementById('hf-raw-repo-input').value = savedRawRepo;
    }
    if (savedCleanedRepo) {
        document.getElementById('hf-cleaned-repo-input').value = savedCleanedRepo;
    }
    if (savedChunkedRepo) {
        document.getElementById('hf-chunked-repo-input').value = savedChunkedRepo;
    }
    
    // Save values to localStorage on change
    document.getElementById('hf-token-input').addEventListener('change', (e) => {
        localStorage.setItem('hf_token', e.target.value);
    });
    document.getElementById('hf-raw-repo-input').addEventListener('change', (e) => {
        localStorage.setItem('hf_raw_repo', e.target.value);
    });
    document.getElementById('hf-cleaned-repo-input').addEventListener('change', (e) => {
        localStorage.setItem('hf_cleaned_repo', e.target.value);
    });
    document.getElementById('hf-chunked-repo-input').addEventListener('change', (e) => {
        localStorage.setItem('hf_chunked_repo', e.target.value);
    });
}

// =============================================================================
// MODAL CLOSE HANDLERS
// =============================================================================

/**
 * Initialize modal close handlers
 */
function initModalHandlers() {
    const overlay = document.getElementById('modalOverlay');
    const closeBtn = document.getElementById('modalClose');
    
    closeBtn.addEventListener('click', hideModal);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            hideModal();
        }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal();
        }
    });
}

// =============================================================================
// CONFIGURATION LOADING
// =============================================================================

/**
 * Load configuration from the server
 */
async function loadConfig() {
    try {
        const config = await api('/api/config');
        AppState.config = config;
        console.log('Configuration loaded:', config);
    } catch (error) {
        console.error('Failed to load configuration:', error);
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize the application when DOM is ready
 */
// =============================================================================
// LOGIN SYSTEM
// =============================================================================

const LOGIN_CREDENTIALS = [
    { username: 'Mozhii', password: '3VDRY' }
];
const MAX_SESSIONS = 6;

function initLogin() {
    const overlay = document.getElementById('loginOverlay');
    const appWrapper = document.getElementById('appWrapper');
    const loginBtn = document.getElementById('loginBtn');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const errorEl = document.getElementById('loginError');

    // Already authenticated this session
    if (sessionStorage.getItem('mozhii_authenticated') === 'true') {
        overlay.classList.add('hidden');
        appWrapper.style.display = '';
        return true;
    }

    function attemptLogin() {
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        if (!username || !password) {
            errorEl.textContent = 'Please enter both username and password';
            return;
        }

        const valid = LOGIN_CREDENTIALS.some(
            c => c.username === username && c.password === password
        );

        if (valid) {
            errorEl.textContent = '';
            sessionStorage.setItem('mozhii_authenticated', 'true');
            overlay.classList.add('hidden');
            appWrapper.style.display = '';
            bootApp();
        } else {
            errorEl.textContent = 'Invalid username or password';
            passwordInput.value = '';
            passwordInput.focus();
        }
    }

    loginBtn.addEventListener('click', attemptLogin);
    passwordInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') attemptLogin();
    });
    usernameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') passwordInput.focus();
    });

    return false;
}

async function bootApp() {
    console.log('🏗️ Mozhii RAG Data Platform initializing...');

    await loadConfig();

    initTabs();
    initAdminSidebar();
    initModalHandlers();
    initHFConfig();

    refreshAdminData();

    console.log('✅ Platform ready!');
}

document.addEventListener('DOMContentLoaded', () => {
    const alreadyAuthed = initLogin();
    if (alreadyAuthed) {
        bootApp();
    }
});
