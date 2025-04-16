/**
 * Main JavaScript file for the transactions page
 */

// Store current expense ID for deletion
let currentExpenseId = null;
let baseCurrencySymbol = ''; // Will be set from the template

document.addEventListener('DOMContentLoaded', function() {
    // Get base currency symbol from the page
    baseCurrencySymbol = document.querySelector('meta[name="base-currency-symbol"]')?.content || '$';
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize date fields
    initializeDates();
    
    // Set up event handlers for filter buttons
    setupFilterButtons();
    
    // Set up event handlers for transaction actions
    setupActionButtons();
    
    // Set up add transaction button
    const openAddTransactionBtn = document.getElementById('openAddTransactionBtn');
    if (openAddTransactionBtn) {
        openAddTransactionBtn.addEventListener('click', function() {
            openAddTransactionPanel();
        });
    }
    
    // Set up category split display in the transaction list
    setupCategorySplitDisplay();

    // Auto-categorize button
    const bulkCategorizeBtn = document.getElementById('bulkCategorizeBtn');
    if (bulkCategorizeBtn) {
        bulkCategorizeBtn.addEventListener('click', bulkCategorize);
    }
    
    // Apply filters on page load
    applyFilters();
});

// Initialize search functionality
function initializeSearch() {
    const globalSearchInput = document.getElementById('globalSearchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const transactionsTable = document.querySelector('#transactionsTable tbody');
    const resultCountEl = document.getElementById('resultCount');

    // Function to perform global search
    function performGlobalSearch() {
        const searchTerm = globalSearchInput.value.toLowerCase().trim();
        clearSearchBtn.style.display = searchTerm ? 'block' : 'none';

        let visibleCount = 0;
        const rows = document.querySelectorAll('#transactionsTable tbody tr[data-expense-id]');

        rows.forEach(row => {
            // Search across multiple fields
            const searchableTexts = [
                row.cells[0].textContent.toLowerCase(),  // Date
                row.cells[2].textContent.toLowerCase(),  // Description
                row.cells[3].textContent.toLowerCase(),  // Amount
                row.cells[4].textContent.toLowerCase(), // Account
                row.querySelector('td:nth-child(6)').textContent.toLowerCase() // Category
            ];

            // Additional metadata search
            const typeText = row.querySelector('.badge').textContent.toLowerCase();
            searchableTexts.push(typeText);

            // Check if any searchable text includes the search term
            const isMatch = searchableTexts.some(text => 
                text.includes(searchTerm) || 
                (searchTerm.startsWith('>') && parseFloat(text.replace(/[^\d.-]/g, '')) > parseFloat(searchTerm.slice(1))) ||
                (searchTerm.startsWith('<') && parseFloat(text.replace(/[^\d.-]/g, '')) < parseFloat(searchTerm.slice(1)))
            );

            row.style.display = isMatch ? '' : 'none';
            if (isMatch) visibleCount++;
        });

        // Update result count
        if (resultCountEl) {
            resultCountEl.textContent = `${visibleCount} transaction${visibleCount !== 1 ? 's' : ''}`;
        }

        // Handle no results
        const noResultsRow = document.querySelector('#transactionsTable tbody tr.no-results');
        if (visibleCount === 0 && !noResultsRow) {
            const noResultRow = document.createElement('tr');
            noResultRow.className = 'no-results';
            noResultRow.innerHTML = `<td colspan="7" class="text-center text-muted">No transactions match your search</td>`;
            transactionsTable.appendChild(noResultRow);
        } else if (visibleCount > 0 && noResultsRow) {
            noResultsRow.remove();
        }
    }

    // Add event listeners for dynamic search
    if (globalSearchInput) {
        globalSearchInput.addEventListener('input', performGlobalSearch);
    }

    // Clear search button functionality
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            globalSearchInput.value = '';
            performGlobalSearch();
        });
    }
}

// Initialize date inputs with sensible defaults
function initializeDates() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    const endDateInput = document.getElementById('endDate');
    const startDateInput = document.getElementById('startDate');
    
    if (endDateInput) {
        endDateInput.value = today.toISOString().split('T')[0];
    }
    
    if (startDateInput) {
        startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
    }
}

// Set up filter buttons
function setupFilterButtons() {
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }
    
    const exportDataBtn = document.getElementById('exportDataBtn');
    if (exportDataBtn) {
        exportDataBtn.addEventListener('click', exportTransactions);
    }
}

// Set up action buttons for transactions
function setupActionButtons() {
    // View split details buttons
    document.querySelectorAll('.view-split-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const expenseId = this.getAttribute('data-expense-id');
            if (expenseId) {
                const splitDetails = document.getElementById(`split-${expenseId}`);
                if (splitDetails) {
                    splitDetails.style.display = splitDetails.style.display === 'none' ? 'block' : 'none';
                }
            }
        });
    });
    
    // Edit expense buttons - use TransactionModule if available
    document.querySelectorAll('.edit-expense-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const expenseId = this.getAttribute('data-expense-id');
            if (expenseId) {
                if (window.TransactionModule && typeof TransactionModule.openEditForm === 'function') {
                    console.log("Using TransactionModule for edit");
                    TransactionModule.openEditForm(expenseId);
                } else {
                    console.log("Fallback to original edit function");
                    openEditTransactionPanel(expenseId);
                }
            }
        });
    });
    
    // Delete expense buttons remain unchanged
    document.querySelectorAll('.delete-expense-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const expenseId = this.getAttribute('data-expense-id');
            if (expenseId) {
                showDeleteConfirmation(expenseId);
            }
        });
    });
    
    // Confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            if (currentExpenseId) {
                deleteExpense(currentExpenseId);
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
                if (modal) {
                    modal.hide();
                }
            }
        });
    }
}
// Function to display split categories in the transactions table
function setupCategorySplitDisplay() {
    // Find all transactions with split categories
    document.querySelectorAll('[data-has-splits="true"]').forEach(element => {
        const expenseId = element.getAttribute('data-expense-id');
        
        // Add click handler to toggle
        element.querySelector('.split-toggle')?.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const expenseId = this.getAttribute('data-expense-id');
            const detailElement = document.getElementById(`split-categories-${expenseId}`);
            
            if (detailElement) {
                // Toggle visibility
                if (detailElement.style.display === 'none') {
                    detailElement.style.display = 'block';
                    this.querySelector('i').classList.replace('fa-chevron-down', 'fa-chevron-up');
                    
                    // Check if we need to load the data
                    if (detailElement.querySelector('.loading')) {
                        loadCategorySplits(expenseId, detailElement);
                    }
                } else {
                    detailElement.style.display = 'none';
                    this.querySelector('i').classList.replace('fa-chevron-up', 'fa-chevron-down');
                }
            }
        });
    });
}

// Function to load category split details via AJAX
function loadCategorySplits(expenseId, detailElement) {
    fetch(`/get_category_splits/${expenseId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.splits.length > 0) {
                // Create split detail UI
                let html = '<div class="list-group list-group-flush bg-dark">';
                
                data.splits.forEach(split => {
                    // Get category details from the response
                    const categoryName = split.category?.name || 'Unknown';
                    const categoryColor = split.category?.color || '#6c757d';
                    const categoryIcon = split.category?.icon || 'fa-tag';
                    
                    html += `
                        <div class="list-group-item bg-dark border-secondary py-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <span class="badge me-2" style="background-color: ${categoryColor}">
                                        <i class="fas ${categoryIcon}"></i>
                                    </span>
                                    ${categoryName}
                                </div>
                                <span class="badge bg-secondary">${window.baseCurrencySymbol || '$'}${split.amount.toFixed(2)}</span>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                detailElement.innerHTML = html;
            } else {
                detailElement.innerHTML = '<div class="text-muted">No split categories found</div>';
            }
        })
        .catch(error => {
            console.error('Error loading category splits:', error);
            detailElement.innerHTML = '<div class="text-danger">Error loading splits</div>';
        });
}

// Show delete confirmation dialog
function showDeleteConfirmation(expenseId) {
    // Store the expense ID
    currentExpenseId = expenseId;
    
    // Find the expense description for better UX
    const row = document.querySelector(`tr[data-expense-id="${expenseId}"]`);
    const description = row ? row.cells[2].textContent.trim() : 'this transaction';
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create unique ID for this toast
    const toastId = `delete-toast-${Date.now()}`;
    
    // Create the confirm delete toast with buttons
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="false">
            <div class="toast-header bg-danger text-white">
                <strong class="me-auto"><i class="fas fa-trash me-2"></i>Confirm Deletion</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <p>Are you sure you want to delete "${description}"?</p>
                <p class="text-danger small mb-2">This action cannot be undone.</p>
                <div class="mt-2 pt-2 border-top d-flex justify-content-end">
                    <button type="button" class="btn btn-secondary btn-sm me-2" data-bs-dismiss="toast">Cancel</button>
                    <button type="button" class="btn btn-danger btn-sm delete-confirm-btn">Delete</button>
                </div>
            </div>
        </div>
    `;
    
    // Add the toast to the container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Get the toast element
    const toastEl = document.getElementById(toastId);
    
    // Add delete confirmation button handler
    toastEl.querySelector('.delete-confirm-btn').addEventListener('click', function() {
        // Hide the toast
        const bsToast = bootstrap.Toast.getInstance(toastEl);
        if (bsToast) bsToast.hide();
        
        // Delete the expense
        deleteExpense(currentExpenseId);
    });
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    
    // Clean up the toast element when hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

// Delete expense
function deleteExpense(expenseId) {
    // Show loading state on the row
    const row = document.querySelector(`tr[data-expense-id="${expenseId}"]`);
    if (row) {
        row.classList.add('deleting');
        row.style.opacity = '0.5';
    }
    
    fetch(`/delete_expense/${expenseId}`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove row with animation
            if (row) {
                row.style.height = row.offsetHeight + 'px';
                row.style.transition = 'all 0.3s ease-out';
                
                setTimeout(() => {
                    row.style.height = '0';
                    row.style.opacity = '0';
                    row.style.overflow = 'hidden';
                    
                    // Remove row after animation
                    setTimeout(() => {
                        row.remove();
                        
                        // Update the counter
                        const resultCount = document.getElementById('resultCount');
                        if (resultCount) {
                            const count = parseInt(resultCount.textContent);
                            if (!isNaN(count)) {
                                resultCount.textContent = (count - 1) + ' transactions';
                            }
                        }
                    }, 300);
                }, 100);
            }
        } else {
            // Show error and reset row
            showMessage(data.message || 'Failed to delete transaction', 'error');
            if (row) {
                row.classList.remove('deleting');
                row.style.opacity = '1';
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Error deleting transaction: ' + error.message, 'error');
        
        // Reset row
        if (row) {
            row.classList.remove('deleting');
            row.style.opacity = '1';
        }
    });
}

// Apply filters to transactions table
function applyFilters() {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    const transactionType = document.getElementById('transactionTypeFilter')?.value || 'all';
    const categoryId = document.getElementById('categoryFilter')?.value || 'all';
    const description = (document.getElementById('descriptionFilter')?.value || '').toLowerCase();
    const minAmount = document.getElementById('minAmount')?.value;
    const maxAmount = document.getElementById('maxAmount')?.value;
    
    let visibleCount = 0;
    
    // Get all rows
    const rows = document.querySelectorAll('#transactionsTable tbody tr[data-expense-id]');
    if (!rows.length) return;
    
    rows.forEach(row => {
        const rowDate = row.cells[0].textContent.trim();
        const rowType = row.querySelector('.badge')?.textContent.toLowerCase() || '';
        const rowDescription = row.cells[2].textContent.trim().toLowerCase();
        const rowCategory = row.getAttribute('data-category-id') || 'none';
        
        // Extract amount from the amount cell (removing currency symbol and formatting)
        const amountText = row.cells[3].textContent.trim();
        const rowAmount = parseFloat(amountText.replace(/[^\d.-]/g, '')) || 0;
        
        let visible = true;
        
        // Date filter
        if (startDate && new Date(rowDate) < new Date(startDate)) visible = false;
        if (endDate && new Date(rowDate) > new Date(endDate)) visible = false;
        
        // Transaction type filter
        if (transactionType !== 'all') {
            if (transactionType === 'expense' && !rowType.includes('expense')) visible = false;
            if (transactionType === 'income' && !rowType.includes('income')) visible = false;
            if (transactionType === 'transfer' && !rowType.includes('transfer')) visible = false;
        }
        
        // Category filter
        if (categoryId === 'none') {
            // Only show uncategorized items
            if (rowCategory !== 'none') visible = false;
        } else if (categoryId !== 'all') {
            // Show only the selected category
            if (rowCategory !== categoryId) visible = false;
        }
        
        // Description filter
        if (description && !rowDescription.includes(description)) visible = false;
        
        // Amount filter
        if (minAmount && !isNaN(parseFloat(minAmount)) && Math.abs(rowAmount) < parseFloat(minAmount)) visible = false;
        if (maxAmount && !isNaN(parseFloat(maxAmount)) && Math.abs(rowAmount) > parseFloat(maxAmount)) visible = false;
        
        // Show/hide row
        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });
    
    // Update result count
    const resultCountEl = document.getElementById('resultCount');
    if (resultCountEl) {
        resultCountEl.textContent = `${visibleCount} transaction${visibleCount !== 1 ? 's' : ''}`;
    }
    
    // Show/hide the "no results" message
    const tbody = document.querySelector('#transactionsTable tbody');
    let noResultsRow = document.querySelector('#transactionsTable tbody tr.no-results');
    
    if (visibleCount === 0) {
        // Add "no results" row if none exists
        if (!noResultsRow && tbody) {
            noResultsRow = document.createElement('tr');
            noResultsRow.className = 'no-results';
            noResultsRow.innerHTML = '<td colspan="7" class="text-center">No transactions match your filters</td>';
            tbody.appendChild(noResultsRow);
        }
    } else if (noResultsRow) {
        // Remove "no results" row if we have visible rows
        noResultsRow.remove();
    }
}

// Clear all filters
function clearFilters() {
    // Reset filter form fields
    const form = document.getElementById('filterForm');
    if (form) form.reset();
    
    // Re-initialize date range
    initializeDates();
    
    // Apply the cleared filters
    applyFilters();
}

// Export transactions as CSV
function exportTransactions() {
    // Collect filter data from form
    const filters = {
        startDate: document.getElementById('startDate')?.value,
        endDate: document.getElementById('endDate')?.value,
        transactionType: document.getElementById('transactionTypeFilter')?.value,
        categoryId: document.getElementById('categoryFilter')?.value,
        minAmount: document.getElementById('minAmount')?.value,
        maxAmount: document.getElementById('maxAmount')?.value,
        description: document.getElementById('descriptionFilter')?.value
    };

    // Show loading state
    const exportBtn = document.getElementById('exportDataBtn');
    if (exportBtn) {
        exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
        exportBtn.disabled = true;
    }

    // Perform AJAX request to export
    fetch('/export_transactions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(filters)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Export failed');
        }
        return response.blob();
    })
    .then(blob => {
        // Create a download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        a.href = url;
        a.download = `transactions_${timestamp}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    })
    .catch(error => {
        console.error('Export error:', error);
        showMessage('Failed to export transactions. Please try again.', 'error');
    })
    .finally(() => {
        // Reset button state
        if (exportBtn) {
            exportBtn.innerHTML = '<i class="fas fa-file-export me-2"></i>Export';
            exportBtn.disabled = false;
        }
    });
}

// Bulk categorize transactions
function bulkCategorize() {
    // Show a confirmation toast
    showMessage('This will attempt to categorize all uncategorized transactions based on your category mapping rules.', 'warning', {
        autoHide: false,
        actionButtons: [
            {
                text: 'Cancel',
                class: 'btn-outline-secondary',
                onClick: function(toast) {
                    // Just close the toast
                    toast.hide();
                }
            },
            {
                text: 'Continue',
                class: 'btn-warning',
                onClick: function(toast) {
                    toast.hide();
                    performBulkCategorization();
                }
            }
        ]
    });
}

// Function to perform the actual categorization
function performBulkCategorization() {
    // Show loading state
    const bulkBtn = document.getElementById('bulkCategorizeBtn');
    if (bulkBtn) {
        bulkBtn.disabled = true;
        bulkBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Categorizing...';
    }
    
    // Perform AJAX request
    fetch('/bulk_categorize_transactions', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Bulk categorization failed');
        }
        // Just get the response text instead of expecting JSON
        return response.text();
    })
    .then(data => {
        // Show success message
        showMessage('Auto-categorization complete! Page will reload to show changes.', 'success', {
            autoHide: true,
            delay: 3000,
            onClose: function() {
                // Reload page to show changes
                window.location.reload();
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage(`Error during categorization: ${error.message}`, 'error');
        
        // Reset button state
        if (bulkBtn) {
            bulkBtn.disabled = false;
            bulkBtn.innerHTML = '<i class="fas fa-tags me-2"></i>Auto-Categorize';
        }
    });
}