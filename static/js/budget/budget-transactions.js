/**
 * Budget transaction management functions
 */

import { formatCurrency, formatDate, showToast } from '../common/utils.js';

/**
 * Load transactions for a specific budget
 * @param {string} budgetId - Budget ID to load transactions for
 */
function loadBudgetTransactions(budgetId) {
    const transactionsContainer = document.getElementById('budget-transactions-container');
    if (!transactionsContainer) return;
    
    // Show loading state
    transactionsContainer.innerHTML = `
        <div class="d-flex justify-content-center py-4">
            <div class="spinner-border text-secondary" role="status">
                <span class="visually-hidden">Loading transactions...</span>
            </div>
            <span class="ms-2">Loading transactions...</span>
        </div>
    `;
    
    // Use the budget transactions endpoint
    fetch(`/budgets/transactions/${budgetId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load transactions');
            }
            return response.json();
        })
        .then(data => {
            displayBudgetTransactions(data.transactions || [], transactionsContainer);
            
            // Update transaction count badge
            const countBadge = document.getElementById('transaction-count-badge');
            if (countBadge) {
                countBadge.textContent = `${data.transactions.length} transactions`;
            }
            
            // Store budget name for reference
            window.currentBudgetName = data.budget_name || 'Budget';
            window.currentBudgetId = budgetId;
        })
        .catch(error => {
            console.error('Error fetching transactions:', error);
            transactionsContainer.innerHTML = `
                <div class="alert alert-warning text-center m-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Unable to load transactions. Please try again later.
                </div>
            `;
        });
}

/**
 * Display fetched transactions in the container
 * @param {Array} transactions - Array of transaction objects
 * @param {HTMLElement} container - Container to display transactions in
 */
function displayBudgetTransactions(transactions, container) {
    // If no transactions
    if (transactions.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <p class="text-muted">No transactions found for this budget.</p>
            </div>
        `;
        return;
    }
    
    // Create transactions table
    let tableHTML = `
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th style="width: 20px;"></th>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Category</th>
                        <th style="width: 50px;"></th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Add transaction rows
    transactions.forEach((transaction) => {
        const amountClass = transaction.amount < 0 ? 'text-danger' : 'text-success';
        const amountPrefix = transaction.amount < 0 ? '-' : '';
        const formattedAmount = `${amountPrefix}${formatCurrency(Math.abs(transaction.amount))}`;
        
        // Generate unique IDs for this transaction
        const transId = `trans-${transaction.id}`;
        const detailsId = `details-${transId}`;
        
        // Main transaction row
        tableHTML += `
            <tr class="transaction-row" data-transaction-id="${transaction.id}">
                <td>
                    <button class="btn btn-sm btn-link p-0 expand-button" onclick="toggleTransactionDetails('${detailsId}', this)">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </td>
                <td>${formatDate(transaction.date)}</td>
                <td>${transaction.description}</td>
                <td class="${amountClass}">${formattedAmount}</td>
                <td>
                    <span class="badge" style="background-color: ${transaction.category_color || '#6c757d'};">
                        <i class="fas ${transaction.category_icon || 'fa-tag'}"></i>
                        ${transaction.category_name || 'Uncategorized'}
                    </span>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="editTransaction(${transaction.id})">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                </td>
            </tr>
            
            <!-- Expandable details row (hidden by default) -->
            <tr id="${detailsId}" class="transaction-details" style="display: none;">
                <td colspan="6" class="p-0">
                    <div class="card bg-dark border-secondary mb-0">
                        <div class="card-body py-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6 class="mb-2">Transaction Details</h6>
                                    <ul class="list-unstyled mb-0">
                                        <li><strong>ID:</strong> ${transaction.id}</li>
                                        <li><strong>Payment Method:</strong> ${transaction.payment_method || transaction.card_used || 'Not specified'}</li>
                                        <li><strong>Transaction Type:</strong> ${transaction.transaction_type || 'Expense'}</li>
                                        ${transaction.has_user_splits ? '<li><strong>Split with other users:</strong> Yes</li>' : ''}
                                        ${transaction.has_category_splits ? '<li><strong>Split between categories:</strong> Yes</li>' : ''}
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <h6 class="mb-2">Budget Information</h6>
                                    <ul class="list-unstyled mb-0">
                                        <li><strong>Budget:</strong> ${transaction.category_name || 'Uncategorized'}</li>
                                        <li><strong>Tags:</strong> ${(transaction.tags || []).join(', ') || 'No tags'}</li>
                                        ${transaction.original_amount ? `<li><strong>Original amount:</strong> ${formatCurrency(transaction.original_amount)}</li>` : ''}
                                        ${(() => {
                                            // Completely skip rendering if split_details is problematic
                                            if (!transaction.split_details || 
                                                transaction.split_details === 'null' || 
                                                transaction.split_details === '' || 
                                                transaction.split_details === '{}' || 
                                                transaction.split_details === '[]') {
                                                return '';
                                            }
                                            
                                            try {
                                                // Safely parse split_details
                                                const splitDetails = typeof transaction.split_details === 'string' 
                                                    ? JSON.parse(transaction.split_details) 
                                                    : transaction.split_details;
                                                
                                                // Only render if it has a user_amount
                                                if (splitDetails && 
                                                    typeof splitDetails === 'object' && 
                                                    'user_amount' in splitDetails) {
                                                    return `<li><strong>Your portion:</strong> ${formatCurrency(splitDetails.user_amount)}</li>`;
                                                }
                                                
                                                return '';
                                            } catch (error) {
                                                console.warn('Error parsing split details:', error);
                                                return '';
                                            }
                                        })()}
                                    </ul>
                                </div>
                            </div>
                            <div class="mt-3 text-end">
                                <form action="/delete_expense/${transaction.id}" method="POST" class="d-inline" 
                                      onsubmit="return confirm('Are you sure you want to delete this transaction?')">
                                    <button type="submit" class="btn btn-sm btn-danger me-2">
                                        <i class="fas fa-trash me-1"></i> Delete
                                    </button>
                                </form>
                                <button type="button" class="btn btn-sm btn-primary" onclick="editTransaction(${transaction.id})">
                                    <i class="fas fa-pencil-alt me-1"></i> Edit
                                </button>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
        </div>
    `;
    
    container.innerHTML = tableHTML;
    
}

/**
 * Toggle transaction details visibility
 * @param {string} detailsId - ID of the details row to toggle
 * @param {HTMLElement} button - Button that triggered the toggle
 */
function toggleTransactionDetails(detailsId, button) {
    const detailsRow = document.getElementById(detailsId);
    if (!detailsRow) return;
    
    if (detailsRow.style.display === 'none') {
        // Show details
        detailsRow.style.display = 'table-row';
        button.innerHTML = '<i class="fas fa-chevron-down"></i>';
        
        // Find the associated transaction row and highlight it
        const transactionRow = detailsRow.previousElementSibling;
        if (transactionRow) {
            transactionRow.classList.add('bg-dark');
        }
    } else {
        // Hide details
        detailsRow.style.display = 'none';
        button.innerHTML = '<i class="fas fa-chevron-right"></i>';
        
        // Find the associated transaction row and remove highlight
        const transactionRow = detailsRow.previousElementSibling;
        if (transactionRow) {
            transactionRow.classList.remove('bg-dark');
        }
    }
}

/**
 * Edit a transaction
 * @param {string} transactionId - ID of the transaction to edit
 */
function editTransaction(transactionId) {
    openTransactionSlidePanel(transactionId);
}

/**
 * Open slide panel to edit a transaction
 * @param {string} transactionId - ID of the transaction to edit
 */
function openTransactionSlidePanel(transactionId) {
    // Create or get the slide panel if it already exists
    let slidePanel = document.getElementById('transaction-slide-panel');
    
    if (!slidePanel) {
        // Create the panel
        slidePanel = document.createElement('div');
        slidePanel.id = 'transaction-slide-panel';
        slidePanel.className = 'budget-slide-panel transaction-slide-panel'; // Reuse the same styling
        
        // Create overlay if it doesn't exist
        let overlay = document.getElementById('slide-panel-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'slide-panel-overlay';
            overlay.id = 'slide-panel-overlay';
            overlay.addEventListener('click', closeTransactionSlidePanel);
            document.body.appendChild(overlay);
        }
        
        // Add to DOM
        document.body.appendChild(slidePanel);
    }
    
    // Show loading state
    slidePanel.innerHTML = `
        <div class="slide-panel-header">
            <h4 class="mb-0">
                <i class="fas fa-receipt me-2" style="color: #0ea5e9;"></i>
                Edit Transaction
            </h4>
            <button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="closeTransactionSlidePanel()"></button>
        </div>
        <div class="slide-panel-content">
            <div class="d-flex justify-content-center align-items-center p-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-3">Loading transaction details...</span>
            </div>
        </div>
    `;
    
    // Show the panel and overlay
    document.getElementById('slide-panel-overlay').classList.add('active');
    slidePanel.classList.add('active');
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    // Fetch transaction data
    fetch(`/get_expense/${transactionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateTransactionSlidePanel(data.expense, transactionId);
            } else {
                showTransactionSlidePanelError(data.message || 'Error fetching transaction details');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showTransactionSlidePanelError('Failed to fetch transaction details: ' + error.message);
        });
}

/**
 * Close the transaction slide panel
 */
function closeTransactionSlidePanel() {
    // Get the panel and overlay
    const slidePanel = document.getElementById('transaction-slide-panel');
    const overlay = document.getElementById('slide-panel-overlay');
    
    if (slidePanel) slidePanel.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

/**
 * Show error message in transaction slide panel
 * @param {string} message - Error message to display
 */
function showTransactionSlidePanelError(message) {
    const slidePanel = document.getElementById('transaction-slide-panel');
    if (!slidePanel) return;
    
    const contentDiv = slidePanel.querySelector('.slide-panel-content');
    if (contentDiv) {
        contentDiv.innerHTML = `
            <div class="alert alert-danger m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
            <div class="text-center mt-3">
                <button type="button" class="btn btn-secondary" onclick="closeTransactionSlidePanel()">
                    Close
                </button>
            </div>
        `;
    }
}

/**
 * Populate the transaction slide panel with transaction data
 * @param {Object} transaction - Transaction data
 * @param {string} transactionId - Transaction ID
 */
function populateTransactionSlidePanel(transaction, transactionId) {
    const slidePanel = document.getElementById('transaction-slide-panel');
    if (!slidePanel) return;
    
    const contentDiv = slidePanel.querySelector('.slide-panel-content');
    if (!contentDiv) return;
    
    // Format the date for the input field (YYYY-MM-DD)
    const expenseDate = new Date(transaction.date);
    const formattedDate = expenseDate.toISOString().split('T')[0];
    
    // Get the current budget context
    const budgetName = window.currentBudgetName || 'Budget';
    
    // Create form HTML
    contentDiv.innerHTML = `
        <form id="slide-panel-transaction-form" action="/update_expense/${transactionId}" method="POST">
            <div class="p-4">
                <!-- Transaction Info Summary -->
                <div class="card bg-dark mb-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <span class="badge bg-info text-dark me-2">
                                Budget: ${budgetName}
                            </span>
                            <h5 class="mb-0">
                                Transaction #${transactionId}
                            </h5>
                        </div>
                        
                        <div class="mt-2">
                            <span class="badge bg-secondary">
                                <i class="fas fa-clock me-1"></i>
                                ${formattedDate}
                            </span>
                            <span class="badge bg-secondary ms-2">
                                <i class="fas fa-wallet me-1"></i>
                                ${transaction.card_used || 'No payment method'}
                            </span>
                        </div>
                    </div>
                </div>
                
                <!-- Form Fields -->
                <div class="row">
                    <div class="col-md-8 mb-3">
                        <label for="slide_transaction_description" class="form-label">Description</label>
                        <input type="text" class="form-control bg-dark text-light" 
                               id="slide_transaction_description" name="description" 
                               value="${transaction.description}" required>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="slide_transaction_amount" class="form-label">Amount</label>
                        <div class="input-group">
                            <span class="input-group-text bg-dark text-light border-secondary">$</span>
                            <input type="number" step="0.01" class="form-control bg-dark text-light" 
                                   id="slide_transaction_amount" name="amount" 
                                   value="${transaction.amount}" required>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="slide_transaction_date" class="form-label">Date</label>
                        <input type="date" class="form-control bg-dark text-light" 
                               id="slide_transaction_date" name="date" 
                               value="${formattedDate}" required>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="slide_transaction_category" class="form-label">Category</label>
                        <select class="form-select bg-dark text-light" 
                                id="slide_transaction_category" name="category_id">
                            <option value="">Select category</option>
                            <!-- Will be populated by JavaScript -->
                        </select>
                    </div>
                    
                </div>
                
                <!-- Hidden fields to preserve data -->
                <input type="hidden" name="paid_by" value="${transaction.paid_by}">
                <input type="hidden" name="personal_expense" value="on">
                <input type="hidden" name="split_method" value="equal">
                
                <div class="d-flex justify-content-between align-items-center">
                    <button type="button" class="btn btn-outline-danger" onclick="confirmDeleteTransaction(${transactionId})">
                        <i class="fas fa-trash-alt me-1"></i> Delete
                    </button>
                    
                    <div>
                        <button type="button" class="btn btn-secondary me-2" onclick="closeTransactionSlidePanel()">
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save me-1"></i> Save Changes
                        </button>
                    </div>
                </div>
            </div>
        </form>
    `;
    
    // Populate category dropdown
    populateTransactionCategoryOptions('slide_transaction_category', transaction.category_id);
    
    // Add form submit handler
    const form = document.getElementById('slide-panel-transaction-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch(this.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to update transaction');
            return response.text();
        })
        .then(() => {
            // Show success notification
            showToast('Transaction updated successfully!', 'success');
            
            // Close the panel
            closeTransactionSlidePanel();
            
            // Refresh the transactions in the current budget view
            const currentBudgetId = getCurrentSelectedBudgetId();
            if (currentBudgetId) {
                loadBudgetTransactions(currentBudgetId);
            } else {
                // Fallback to full page reload if we can't determine the current budget
                setTimeout(() => window.location.reload(), 500);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error updating transaction: ' + error.message, 'error');
        });
    });
}

/**
 * Confirm delete transaction
 * @param {string} transactionId - ID of transaction to delete
 */
function confirmDeleteTransaction(transactionId) {
    if (confirm('Are you sure you want to delete this transaction? This action cannot be undone.')) {
        fetch(`/delete_expense/${transactionId}`, {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete transaction');
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Show success notification
                showToast('Transaction deleted successfully!', 'success');
                
                // Close the panel
                closeTransactionSlidePanel();
                
                // Refresh transactions in the current budget view
                const currentBudgetId = getCurrentSelectedBudgetId();
                if (currentBudgetId) {
                    loadBudgetTransactions(currentBudgetId);
                } else {
                    // Fallback to full page reload
                    setTimeout(() => window.location.reload(), 500);
                }
            } else {
                throw new Error(data.message || 'Failed to delete transaction');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error deleting transaction: ' + error.message, 'error');
        });
    }
}

/**
 * Get the currently selected budget ID
 * @returns {string|null} ID of selected budget or null if none selected
 */
function getCurrentSelectedBudgetId() {
    const selectedRow = document.querySelector('.budget-row.selected-budget');
    return selectedRow ? selectedRow.getAttribute('data-budget-id') : null;
}

/**
 * Populate category options for transaction
 * @param {string} selectId - ID of select element to populate
 * @param {string} selectedCategoryId - ID of category to select
 */
function populateTransactionCategoryOptions(selectId, selectedCategoryId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Get categories from the existing page dropdown
    const existingCategorySelect = document.getElementById('edit_category_id');
    if (existingCategorySelect) {
        // Clone options from existing select
        select.innerHTML = existingCategorySelect.innerHTML;
        
        // Set selected option
        if (selectedCategoryId) {
            const option = select.querySelector(`option[value="${selectedCategoryId}"]`);
            if (option) option.selected = true;
        }
    }
}

// Export transaction functions
export {
    loadBudgetTransactions,
    displayBudgetTransactions,
    toggleTransactionDetails,
    editTransaction,
    confirmDeleteTransaction,
    getCurrentSelectedBudgetId,
    populateTransactionCategoryOptions
};