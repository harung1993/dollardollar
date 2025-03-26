// Modified recurring-detection.js

/**
 * Initialize the recurring transaction detection module
 */
function initRecurringDetection() {
    // Fetch detected recurring transactions when the page loads
    fetchDetectedRecurring();
    
    // Setup event handlers
    setupRecurringDetectionEvents();
}

/**
 * Fetch detected recurring transactions from the server
 */
function fetchDetectedRecurring() {
    // Show loading state
    const container = document.getElementById('detected-recurring-container');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin me-2"></i>Analyzing transaction patterns...</div>';
    
    // Fetch data from the server
    fetch('/detect_recurring_transactions')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Error fetching recurring transactions');
            }
            renderDetectedRecurring(data);
        })
        .catch(error => {
            console.error('Error fetching recurring transactions:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error detecting recurring transactions: ${error.message}
                </div>
                <div class="text-center mt-3">
                    <button class="btn btn-outline-light" onclick="fetchDetectedRecurring()">
                        <i class="fas fa-sync me-1"></i>Try Again
                    </button>
                </div>
            `;
        });
}

/**
 * Render detected recurring transactions in the UI
 */
function renderDetectedRecurring(data) {
    const container = document.getElementById('detected-recurring-container');
    if (!container) return;
    
    // If no detected transactions
    if (!data.candidates || data.candidates.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No recurring transactions detected. We'll continue to analyze your transaction patterns.
            </div>
        `;
        return;
    }
    
    // Build HTML for candidates
    let html = `
        <div class="text-muted mb-4 small">
            <i class="fas fa-lightbulb me-2"></i>
            Detected ${data.candidates.length} patterns in your transaction history
        </div>
        <div class="row">
    `;
    
    // Add each candidate
    data.candidates.forEach(candidate => {
        const nextDateStr = new Date(candidate.next_date).toLocaleDateString();
        const frequencyText = getFrequencyText(candidate.frequency);
        const confidenceClass = getConfidenceClass(candidate.confidence);
        
        html += `
            <div class="col-md-6 mb-4 candidate-card" data-candidate-id="${candidate.id}">
                <div class="card bg-dark">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">${escapeHtml(candidate.description)}</h5>
                        <span class="badge ${confidenceClass}">${Math.round(candidate.confidence)}% match</span>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <div class="d-flex align-items-center mb-2">
                                    <i class="fas fa-money-bill-wave text-success me-2"></i>
                                    <span class="text-muted">Amount:</span>
                                    <span class="ms-2">${data.currency_symbol}${candidate.amount.toFixed(2)}</span>
                                </div>
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-calendar-alt text-primary me-2"></i>
                                    <span class="text-muted">Frequency:</span>
                                    <span class="ms-2">${frequencyText}</span>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="d-flex align-items-center mb-2">
                                    <i class="fas fa-history text-warning me-2"></i>
                                    <span class="text-muted">Occurrences:</span>
                                    <span class="ms-2">${candidate.occurrences} times</span>
                                </div>
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-calendar-day text-info me-2"></i>
                                    <span class="text-muted">Next expected:</span>
                                    <span class="ms-2">${nextDateStr}</span>
                                </div>
                            </div>
                        </div>
                        <div class="text-end">
                            <button class="btn btn-sm btn-outline-light me-2 btn-ignore-recurring" 
                                    data-candidate-id="${candidate.id}">
                                <i class="fas fa-ban me-1"></i>Ignore
                            </button>
                            <button class="btn btn-sm btn-outline-info btn-view-history" 
                                    data-candidate-id="${candidate.id}">
                                <i class="fas fa-history me-1"></i>View History
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

/**
 * Setup event handlers for the recurring detection UI
 */
function setupRecurringDetectionEvents() {
    // Event delegation for button clicks
    document.addEventListener('click', function(e) {
        // View history button
        if (e.target && e.target.closest('.btn-view-history')) {
            const button = e.target.closest('.btn-view-history');
            const candidateId = button.getAttribute('data-candidate-id');
            viewTransactionHistory(candidateId);
        }
        
        // Ignore button
        if (e.target && e.target.closest('.btn-ignore-recurring')) {
            const button = e.target.closest('.btn-ignore-recurring');
            const candidateId = button.getAttribute('data-candidate-id');
            ignoreRecurringCandidate(candidateId);
        }
    });
    
    // Toggle detected recurring section
    const toggleBtn = document.getElementById('toggle-detected-recurring');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const container = document.getElementById('detected-recurring-container');
            const icon = this.querySelector('i');
            
            if (container.style.display === 'none') {
                container.style.display = 'block';
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
                this.querySelector('span').textContent = 'Hide Detected Recurring';
            } else {
                container.style.display = 'none';
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
                this.querySelector('span').textContent = 'Show Detected Recurring';
            }
        });
    }
}

/**
 * View transaction history for a recurring candidate
 */
function viewTransactionHistory(candidateId) {
    // Show loading state
    const loadingHtml = `
        <div class="text-center py-4">
            <i class="fas fa-spinner fa-spin me-2"></i>
            <span>Loading transaction history...</span>
        </div>
    `;
    
    // Check if openSlidePanel function exists
    if (typeof openSlidePanel !== 'function') {
        // Fallback method if the function doesn't exist
        createSimpleSlidePanel('transaction-history', 'Transaction History', loadingHtml);
    } else {
        // Open slide panel with loading state using the expected function
        openSlidePanel('transaction-history', {
            title: 'Transaction History',
            icon: 'fa-history',
            iconColor: '#3b82f6',
            content: loadingHtml
        });
    }
    
    // Fetch transaction history
    fetch(`/recurring_candidate_history/${candidateId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to fetch transaction history');
            }
            
            // Update slide panel with transaction history
            const slidePanel = document.getElementById('transaction-history');
            if (slidePanel) {
                const contentDiv = slidePanel.querySelector('.slide-panel-content');
                if (contentDiv) {
                    contentDiv.innerHTML = renderTransactionHistoryContent(data);
                }
            }
        })
        .catch(error => {
            console.error('Error fetching transaction history:', error);
            
            // Show error message in slide panel
            const slidePanel = document.getElementById('transaction-history');
            if (slidePanel) {
                const contentDiv = slidePanel.querySelector('.slide-panel-content');
                if (contentDiv) {
                    contentDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error fetching transaction history: ${error.message}
                        </div>
                    `;
                }
            }
        });
}

/**
 * Create a simple slide panel as fallback if openSlidePanel doesn't exist
 */
function createSimpleSlidePanel(panelId, title, content) {
    // Check if panel already exists
    let panel = document.getElementById(panelId);
    
    // If panel doesn't exist, create it
    if (!panel) {
        // Create panel element
        panel = document.createElement('div');
        panel.id = panelId;
        panel.className = 'slide-panel';
        panel.style.cssText = `
            position: fixed;
            top: 0;
            right: 0;
            width: 500px;
            max-width: 90%;
            height: 100vh;
            background-color: #1e1e1e;
            box-shadow: -5px 0 15px rgba(0, 0, 0, 0.3);
            z-index: 1060;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
        `;
        
        // Create header
        const header = document.createElement('div');
        header.className = 'slide-panel-header';
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border-bottom: 1px solid #2d2d2d;
            background-color: #1a2e22;
        `;
        header.innerHTML = `
            <h4 class="mb-0">${title}</h4>
            <button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="closeSlidePanel('${panelId}')"></button>
        `;
        
        // Create content area
        const contentDiv = document.createElement('div');
        contentDiv.className = 'slide-panel-content';
        contentDiv.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        `;
        contentDiv.innerHTML = content;
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'slide-panel-overlay';
        overlay.className = 'slide-panel-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1050;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease;
        `;
        overlay.addEventListener('click', () => closeSlidePanel(panelId));
        
        // Assemble and append to body
        panel.appendChild(header);
        panel.appendChild(contentDiv);
        document.body.appendChild(panel);
        document.body.appendChild(overlay);
        
        // Also add a document click listener to close when clicking outside
        document.addEventListener('click', function(e) {
            // Check if click is outside the panel
            if (panel.style.transform === 'translateX(0px)' && 
                !panel.contains(e.target) && 
                e.target !== overlay) {
                closeSlidePanel(panelId);
            }
        });
        
        // Show panel and overlay
        setTimeout(() => {
            panel.style.transform = 'translateX(0)';
            overlay.style.opacity = '1';
            overlay.style.visibility = 'visible';
        }, 50);
    } else {
        // Update existing panel
        const contentDiv = panel.querySelector('.slide-panel-content');
        if (contentDiv) {
            contentDiv.innerHTML = content;
        }
        
        // Show panel
        panel.style.transform = 'translateX(0)';
        
        // Show overlay
        const overlay = document.getElementById('slide-panel-overlay');
        if (overlay) {
            overlay.style.opacity = '1';
            overlay.style.visibility = 'visible';
        }
    }
}

/**
 * Render transaction history content for slide panel
 */
function renderTransactionHistoryContent(data) {
    if (!data.transactions || data.transactions.length === 0) {
        return `<div class="alert alert-info">No transaction history available.</div>`;
    }
    
    let html = `
        <div class="mb-4">
            <h5 class="text-light">${escapeHtml(data.description)}</h5>
            <div class="text-muted">Detected ${data.transactions.length} occurrences with similar pattern</div>
        </div>
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th class="text-light">Date</th>
                        <th class="text-light">Amount</th>
                        <th class="text-light">Account</th>
                        <th class="text-light">Category</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.transactions.forEach(transaction => {
        html += `
            <tr>
                <td class="text-light">${new Date(transaction.date).toLocaleDateString()}</td>
                <td class="text-light">${data.currency_symbol}${transaction.amount.toFixed(2)}</td>
                <td class="text-light">${transaction.account_name || 'N/A'}</td>
                <td>
                    ${transaction.category_name ? 
                      `<span class="badge" style="background-color: ${transaction.category_color}">
                        <i class="fas ${transaction.category_icon} me-1"></i>
                        ${transaction.category_name}
                       </span>` : 
                      '<span class="text-muted">None</span>'}
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        <div class="d-flex justify-content-between mt-4">
            <button class="btn btn-outline-danger" onclick="ignoreRecurringCandidate('${data.candidate_id}')">
                <i class="fas fa-ban me-2"></i>Ignore This Pattern
            </button>
        </div>
    `;
    
    return html;
}

/**
 * Ignore a recurring transaction candidate
 */
function ignoreRecurringCandidate(candidateId) {
    // Show confirmation dialog
    if (!confirm('Are you sure you want to ignore this recurring pattern? It will be removed from detection.')) {
        return;
    }
    
    // Show loading indicator on button
    const button = document.querySelector(`.btn-ignore-recurring[data-candidate-id="${candidateId}"]`);
    if (button) {
        const originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Ignoring...';
        button.disabled = true;
    }
    
    fetch(`/ignore_recurring_candidate/${candidateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken() // Get CSRF token if needed
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Close any open slide panel
            closeSlidePanel();
            
            // Remove the candidate card
            const card = document.querySelector(`.candidate-card[data-candidate-id="${candidateId}"]`);
            if (card) {
                // Add fade-out animation before removing
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '0';
                
                setTimeout(() => {
                    card.remove();
                    
                    // Check if there are no more candidates
                    const remainingCards = document.querySelectorAll('.candidate-card');
                    if (remainingCards.length === 0) {
                        const container = document.getElementById('detected-recurring-container');
                        if (container) {
                            container.innerHTML = `
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    No recurring transactions detected. We'll continue to analyze your transaction patterns.
                                </div>
                            `;
                        }
                    }
                }, 500);
            }
            
            // Show success message
            showToast('success', data.message || 'Pattern successfully ignored');
        } else {
            throw new Error(data.message || 'Failed to ignore pattern');
        }
    })
    .catch(error => {
        console.error('Error ignoring recurring candidate:', error);
        
        // Reset button
        if (button) {
            button.innerHTML = '<i class="fas fa-ban me-1"></i>Ignore';
            button.disabled = false;
        }
        
        // Show error message
        showToast('error', 'Error: ' + error.message);
    });
}

/**
 * Show a toast notification
 */
function showToast(type, message) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create a unique ID for this toast
    const toastId = 'toast-' + Date.now();
    
    // Determine toast color based on type
    let bgClass, iconClass;
    switch (type) {
        case 'success':
            bgClass = 'bg-success';
            iconClass = 'fa-check-circle';
            break;
        case 'error':
            bgClass = 'bg-danger';
            iconClass = 'fa-exclamation-circle';
            break;
        case 'warning':
            bgClass = 'bg-warning';
            iconClass = 'fa-exclamation-triangle';
            break;
        default:
            bgClass = 'bg-info';
            iconClass = 'fa-info-circle';
    }
    
    // Create toast HTML
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
            <div class="toast-header ${bgClass} text-white">
                <i class="fas ${iconClass} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body bg-dark text-light">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Close slide panel
 */
function closeSlidePanel(panelId = null) {
    // Close specific panel or all panels
    const panels = panelId 
        ? [document.getElementById(panelId)] 
        : document.querySelectorAll('.slide-panel');
    
    panels.forEach(panel => {
        if (panel) panel.style.transform = 'translateX(100%)';
    });
    
    // Hide overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        overlay.style.visibility = 'hidden';
    }
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

/**
 * Get CSRF token from cookies
 */
function getCsrfToken() {
    // Look for a CSRF token in cookies
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrf_token=')) {
            return cookie.substring('csrf_token='.length, cookie.length);
        }
    }
    
    // Try to find it in a meta tag
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    // Return an empty string if not found
    return '';
}

/**
 * Helper function to get readable frequency text
 */
function getFrequencyText(frequency) {
    switch (frequency) {
        case 'daily': return 'Daily';
        case 'weekly': return 'Weekly';
        case 'biweekly': return 'Every 2 weeks';
        case 'monthly': return 'Monthly';
        case 'quarterly': return 'Every 3 months';
        case 'yearly': return 'Yearly';
        default: return frequency.charAt(0).toUpperCase() + frequency.slice(1);
    }
}

/**
 * Helper function to get confidence badge class
 */
function getConfidenceClass(confidence) {
    if (confidence >= 90) return 'bg-success';
    if (confidence >= 75) return 'bg-info';
    if (confidence >= 60) return 'bg-warning';
    return 'bg-secondary';
}

/**
 * Helper function to escape HTML
 */
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initRecurringDetection);