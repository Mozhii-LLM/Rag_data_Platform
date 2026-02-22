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
        loadApprovedFiles();   // refresh per-file push status
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
 * Push approved data to HuggingFace (legacy stub — real function is below)
 */
async function pushToHuggingFace() {
    // Delegated to the full implementation below.
    _pushToHuggingFace_full();
}

/**
 * Initialize HuggingFace configuration handlers (first pass — overridden below)
 */
function initHFConfig() {
    // The second definition below is the active one — kept for hoisting safety.
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
 * Collect HF credentials from the input fields.
 * Returns null and shows an appropriate error toast if anything is missing.
 */
function _getHFCredentials() {
    const hfToken       = document.getElementById('hf-token-input').value.trim();
    const hfRawRepo     = document.getElementById('hf-raw-repo-input').value.trim();
    const hfCleanedRepo = document.getElementById('hf-cleaned-repo-input').value.trim();
    const hfChunkedRepo = document.getElementById('hf-chunked-repo-input').value.trim();

    if (!hfToken) {
        showToast('Error', 'Please enter your HuggingFace token', 'error');
        return null;
    }
    if (!hfRawRepo || !hfCleanedRepo || !hfChunkedRepo) {
        showToast('Error', 'Please enter all three repository names', 'error');
        return null;
    }
    return { hfToken, hfRawRepo, hfCleanedRepo, hfChunkedRepo };
}

/**
 * Show the push-complete result modal with uploaded / skipped / failed counts.
 */
function _showPushResultModal(title, data) {
    const { results, totals } = data;
    const failedChunks = results.chunked.failed_chunks || [];
    const html = `
        <div class="push-results">
            <p><strong>Upload Results:</strong></p>
            <ul style="text-align:left;margin:0.5rem 0;">
                <li>Raw: ${results.raw.uploaded} uploaded, ${results.raw.skipped||0} skipped, ${results.raw.failed} failed</li>
                <li>Cleaned: ${results.cleaned.uploaded} uploaded, ${results.cleaned.skipped||0} skipped, ${results.cleaned.failed} failed</li>
                <li>Chunks: ${results.chunked.uploaded} uploaded, ${results.chunked.skipped||0} skipped, ${results.chunked.failed} failed</li>
            </ul>
            ${failedChunks.length > 0 ? `
            <p style="color:#c0392b;margin-top:0.5rem;"><strong>Failed chunks (push again to retry):</strong></p>
            <ul style="text-align:left;font-size:0.8rem;color:#c0392b;max-height:120px;overflow-y:auto;">
                ${failedChunks.map(c => `<li>${c}</li>`).join('')}
            </ul>
            <p style="font-size:0.8rem;color:#888;">Already-pushed chunks are skipped automatically — just click Push again.</p>
            ` : ''}
        </div>`;
    showModal(title, html, [{ text: 'OK', class: 'btn-primary', onClick: hideModal }]);
}

// -----------------------------------------------------------------------------
// Per-file push
// -----------------------------------------------------------------------------

/**
 * Load and render the list of approved files in the admin panel.
 * Each file gets its own "🚀 Push" button scoped to only that file.
 */
async function loadApprovedFiles() {
    const listEl = document.getElementById('approved-files-list');
    if (!listEl) return;

    listEl.innerHTML = '<div style="padding:0.6rem;text-align:center;font-size:0.8rem;color:var(--text-secondary);">Loading…</div>';

    try {
        const data = await api('/api/admin/approved-files');
        if (!data.success || data.files.length === 0) {
            listEl.innerHTML = '<div style="padding:0.6rem;text-align:center;font-size:0.8rem;color:var(--text-secondary);">No approved files yet</div>';
            return;
        }

        listEl.innerHTML = data.files.map(file => {
            const hasSomething = file.raw || file.cleaned || (file.chunks > 0);
            if (!hasSomething) return '';

            const allPushed = (file.raw ? file.raw_pushed : true)
                           && (file.cleaned ? file.cleaned_pushed : true)
                           && (file.chunks === 0 || file.chunks_pushed === file.chunks);

            // Build per-stage badges WITH inline delete buttons
            const stageBadges = [];
            const delBtn = (type, label) =>
                `<button onclick="deleteApproved('${file.filename}','${type}')" 
                    title="Delete ${label} for ${file.filename}"
                    style="background:none;border:none;cursor:pointer;padding:0 2px;font-size:0.7rem;color:#c0392b;line-height:1;">🗑</button>`;

            if (file.raw)
                stageBadges.push(`<span>${file.raw_pushed ? '📥✓' : '📥'}${delBtn('raw','raw')}</span>`);
            if (file.cleaned)
                stageBadges.push(`<span>${file.cleaned_pushed ? '🧹✓' : '🧹'}${delBtn('cleaned','cleaned')}</span>`);
            if (file.chunks > 0)
                stageBadges.push(`<span>🧩 ${file.chunks_pushed}/${file.chunks}${delBtn('chunks','chunks')}</span>`);

            const statusBadge = allPushed
                ? '<span style="color:#27ae60;font-size:0.7rem;">✓ Done</span>'
                : '<span style="color:#e67e22;font-size:0.7rem;">⬆ Ready</span>';

            const pushEl = allPushed
                ? '<span style="font-size:0.72rem;color:#27ae60;padding:0.25rem 0.5rem;flex-shrink:0;">Done ✓</span>'
                : `<button class="btn btn-primary" onclick="pushSingleFile('${file.filename}')"
                        style="padding:0.25rem 0.55rem;font-size:0.75rem;white-space:nowrap;flex-shrink:0;"
                        title="Push only ${file.filename} to HuggingFace">🚀 Push</button>`;

            // Delete-all button (small red, shown always)
            const delAllBtn = `<button onclick="deleteApproved('${file.filename}','all')"
                title="Delete ALL stages for ${file.filename}"
                style="background:none;border:1px solid #c0392b;border-radius:4px;cursor:pointer;padding:0.15rem 0.35rem;font-size:0.7rem;color:#c0392b;flex-shrink:0;white-space:nowrap;">🗑 All</button>`;

            return `
            <div style="display:flex;align-items:flex-start;justify-content:space-between;padding:0.4rem 0.5rem;border-bottom:1px solid var(--border);gap:0.4rem;"
                 data-filename="${file.filename}">
                <div style="min-width:0;flex:1;overflow:hidden;">
                    <div style="font-size:0.8rem;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${file.filename}">${file.filename}</div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center;margin-top:2px;">
                        ${stageBadges.join('<span style="color:var(--border);">·</span>')}
                        &nbsp;${statusBadge}
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;flex-shrink:0;">
                    ${pushEl}
                    ${delAllBtn}
                </div>
            </div>`;
        }).join('');
    } catch (error) {
        listEl.innerHTML = `<div style="padding:0.6rem;text-align:center;font-size:0.8rem;color:#c0392b;">Error: ${error.message}</div>`;
    }
}

/**
 * Push ONE specific file (raw + cleaned + chunks) to HuggingFace.
 * Called by each per-file Push button.
 *
 * @param {string} filename - The base filename to push (e.g. 'grade_10_science')
 */
async function pushSingleFile(filename) {
    const creds = _getHFCredentials();
    if (!creds) return;

    // Disable this file's button while pushing
    const row = document.querySelector(`[data-filename="${filename}"]`);
    const btn = row ? row.querySelector('button') : null;
    if (btn) { btn.disabled = true; btn.textContent = '⏳…'; }

    showToast('Uploading…', `Pushing "${filename}" to HuggingFace`, 'info', 20000);

    try {
        const data = await api('/api/admin/push-to-hf', {
            method: 'POST',
            body: JSON.stringify({
                type: 'all',
                hf_token: creds.hfToken,
                raw_repo: creds.hfRawRepo,
                cleaned_repo: creds.hfCleanedRepo,
                chunked_repo: creds.hfChunkedRepo,
                filename: filename,          // ← only this file is pushed
            }),
        });

        if (data.success) {
            const { uploaded, failed, skipped } = data.totals;
            showToast(
                failed > 0 ? '⚠️ Partial Push' : '✅ Pushed!',
                `${filename}: ${uploaded} uploaded${skipped > 0 ? `, ${skipped} already done` : ''}${failed > 0 ? `, ${failed} failed` : ''}`,
                failed > 0 ? 'warning' : 'success',
            );
            if (failed > 0) {
                _showPushResultModal(`Push Results: ${filename}`, data);
            }
            // Refresh the list so the button updates to "Done ✓"
            loadApprovedFiles();
        } else {
            showToast('Error', data.error || 'Push failed', 'error');
            if (btn) { btn.disabled = false; btn.textContent = '🚀 Push'; }
        }
    } catch (error) {
        showToast('Error', `Push failed: ${error.message}`, 'error');
        if (btn) { btn.disabled = false; btn.textContent = '🚀 Push'; }
    }
}

/**
 * Delete one stage (or all stages) of an approved file.
 * Called by the 🗑 buttons in the approved-files list.
 *
 * @param {string} filename  - base filename  (e.g. 'grade_10_science')
 * @param {string} type      - 'raw' | 'cleaned' | 'chunks' | 'all'
 */
async function deleteApproved(filename, type) {
    const label = type === 'all' ? `ALL stages of "${filename}"` : `${type} data for "${filename}"`;
    if (!confirm(`Delete ${label}?\n\nThis cannot be undone.`)) return;

    showToast('Deleting…', label, 'info', 8000);
    try {
        const data = await api('/api/admin/delete-approved', {
            method: 'DELETE',
            body: JSON.stringify({ filename, type }),
        });
        if (data.success) {
            showToast('🗑 Deleted', data.message, 'success');
            loadApprovedFiles();
        } else {
            showToast('Error', data.error || 'Delete failed', 'error');
        }
    } catch (err) {
        showToast('Error', `Delete failed: ${err.message}`, 'error');
    }
}

// -----------------------------------------------------------------------------
// Global "Push All" (admin bulk action)
// -----------------------------------------------------------------------------

async function _pushToHuggingFace_full() {
    const creds = _getHFCredentials();
    if (!creds) return;

    showModal('Push ALL to HuggingFace', `
        <p>This will push <strong>every un-pushed approved file</strong> to:</p>
        <ul style="text-align:left;margin:0.5rem 0;">
            <li><strong>Raw:</strong> ${creds.hfRawRepo}</li>
            <li><strong>Cleaned:</strong> ${creds.hfCleanedRepo}</li>
            <li><strong>Chunked:</strong> ${creds.hfChunkedRepo}</li>
        </ul>
        <p style="font-size:0.85rem;color:var(--text-secondary);">To push only your file, use the individual Push buttons above.</p>
    `, [
        { text: 'Cancel', class: 'btn-secondary', onClick: hideModal },
        { text: 'Push All', class: 'btn-primary', onClick: async () => {
            hideModal();
            showToast('Uploading…', 'Pushing all files to HuggingFace', 'info', 30000);

            try {
                const data = await api('/api/admin/push-to-hf', {
                    method: 'POST',
                    body: JSON.stringify({
                        type: 'all',
                        hf_token: creds.hfToken,
                        raw_repo: creds.hfRawRepo,
                        cleaned_repo: creds.hfCleanedRepo,
                        chunked_repo: creds.hfChunkedRepo,
                        // no filename → push everything
                    }),
                });

                if (data.success) {
                    const { uploaded, failed, skipped } = data.totals;
                    showToast(
                        failed > 0 ? '⚠️ Partial Push' : '✅ Push Complete!',
                        `${uploaded} uploaded${skipped > 0 ? `, ${skipped} skipped` : ''}${failed > 0 ? `, ${failed} failed` : ''}`,
                        failed > 0 ? 'warning' : 'success',
                    );
                    _showPushResultModal('Push All — Results', data);
                    loadApprovedFiles();
                } else {
                    showToast('Error', data.error || 'Push failed', 'error');
                }
            } catch (error) {
                showToast('Error', `Push failed: ${error.message}`, 'error');
            }
        }},
    ]);
}

/**
 * Initialize HuggingFace configuration handlers
 */
function initHFConfig() {
    const syncBtn = document.getElementById('sync-hf-btn');
    const refreshBtn = document.getElementById('refresh-approved-btn');

    if (syncBtn) {
        syncBtn.addEventListener('click', pushToHuggingFace);
    }
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadApprovedFiles);
    }

    // ── Restore saved values from localStorage (fall back to org defaults) ─
    const savedToken       = localStorage.getItem('hf_token');
    const savedRawRepo     = localStorage.getItem('hf_raw_repo')     || 'Mozhii-AI/Raw_Data';
    const savedCleanedRepo = localStorage.getItem('hf_cleaned_repo') || 'Mozhii-AI/Cleaned';
    const savedChunkedRepo = localStorage.getItem('hf_chunked_repo') || 'Mozhii-AI/Chunk';

    if (savedToken)       document.getElementById('hf-token-input').value       = savedToken;
    document.getElementById('hf-raw-repo-input').value     = savedRawRepo;
    document.getElementById('hf-cleaned-repo-input').value = savedCleanedRepo;
    document.getElementById('hf-chunked-repo-input').value = savedChunkedRepo;

    // ── Persist changes ───────────────────────────────────────────────────
    document.getElementById('hf-token-input').addEventListener('change', e => localStorage.setItem('hf_token', e.target.value));
    document.getElementById('hf-raw-repo-input').addEventListener('change', e => localStorage.setItem('hf_raw_repo', e.target.value));
    document.getElementById('hf-cleaned-repo-input').addEventListener('change', e => localStorage.setItem('hf_cleaned_repo', e.target.value));
    document.getElementById('hf-chunked-repo-input').addEventListener('change', e => localStorage.setItem('hf_chunked_repo', e.target.value));

    // Load the approved files list on startup
    loadApprovedFiles();
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
