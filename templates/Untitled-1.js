// Store current expense ID for deletion
let currentExpenseId = null;
let baseCurrencySymbol = '{{ base_currency.symbol }}';

document.addEventListener('DOMContentLoaded', function() {
    // Set up global search functionality
    setupGlobalSearch();
    
    // Initialize date fields with sensible defaults
    initializeDates();
    
    // Set up event handlers for filter buttons
    setupFilterButtons();
    
    // Set up event handlers for transaction actions
    setupActionButtons();
    
    // Set up add transaction button
    const openAddTransactionBtn = document.getElementById('openAddTransactionBtn');
    if (openAddTransactionBtn) {
        openAddTransactionBtn.addEventListener('click', openAddTransactionPanel);
    }
    
    // Apply filters on page load
    applyFilters();
    
    // Set up bulk categorize button
    const bulkCategorizeBtn = document.getElementById('bulkCategorizeBtn');
    if (bulkCategorizeBtn) {
        bulkCategorizeBtn.addEventListener('click', bulkCategorize);
    }
});

// Set up global search
function setupGlobalSearch() {
    const globalSearchInput = document.getElementById('globalSearchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const resultCountEl = document.getElementById('resultCount');
    
    if (!globalSearchInput) return;
    
    // Function to perform global search
    function performGlobalSearch() {
        const searchTerm = globalSearchInput.value.toLowerCase().trim();
        clearSearchBtn.style.display = searchTerm ? 'block' : 'none';

        let visibleCount = 0;
        const rows = document.querySelectorAll('#transactionsTable tbody tr[data-expense-id]');
        const transactionsTable = document.querySelector('#transactionsTable tbody');

        rows.forEach(row => {
            // Search across multiple fields
            const searchableTexts = [
                row.cells[0].textContent.toLowerCase(),  // Date
                row.cells[2].textContent.toLowerCase(),  // Description
                row.cells[3].textContent.toLowerCase(),  // Amount
                row.cells[4].textContent.toLowerCase(),  // Account
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
        if (visibleCount === 0 && !noResultsRow && transactionsTable) {
            const noResultRow = document.createElement('tr');
            noResultRow.className = 'no-results';
            noResultRow.innerHTML = `<td colspan="7" class="text-center text-muted">No transactions match your search</td>`;
            transactionsTable.appendChild(noResultRow);
        } else if (visibleCount > 0 && noResultsRow) {
            noResultsRow.remove();
        }
    }

    // Add event listeners
    globalSearchInput.addEventListener('input', performGlobalSearch);
    
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
    
    // Edit expense buttons
    document.querySelectorAll('.edit-expense-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const expenseId = this.getAttribute('data-expense-id');
            if (expenseId) {
                openEditTransactionPanel(expenseId);
            }
        });
    });
    
    // Delete expense buttons
    document.querySelectorAll('.delete-expense-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const expenseId = this.getAttribute('data-expense-id');
            if (expenseId) {
                showDeleteConfirmation(expenseId);
            }
        });
    });
}

// Function to show delete confirmation
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

// Show a message toast
function showMessage(message, type = 'success', options = {}) {
    // Default options
    const defaultOptions = {
        autoHide: true,
        delay: 5000,
        actionButtons: [],
        onClose: null
    };
    
    // Merge options
    const finalOptions = {...defaultOptions, ...options};
    
    // Check if we can use Bootstrap toast
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toastId = `toast-${Date.now()}`;
        const iconClass = type === 'error' ? 'fa-exclamation-circle' : 
                          type === 'warning' ? 'fa-exclamation-triangle' : 'fa-check-circle';
        const bgColor = type === 'error' ? 'bg-danger' : 
                        type === 'warning' ? 'bg-warning text-dark' : 'bg-success';
        
        // Create action buttons HTML if provided
        let actionButtonsHtml = '';
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
            actionButtonsHtml = `
                <div class="mt-2 pt-2 border-top d-flex justify-content-end">
                    ${finalOptions.actionButtons.map(btn => 
                        `<button type="button" class="btn ${btn.class || 'btn-secondary'} btn-sm me-2 action-btn" 
                            data-action="${btn.text}">${btn.text}</button>`
                    ).join('')}
                </div>
            `;
        }
        
        // Create toast HTML
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" 
                ${finalOptions.autoHide ? `data-bs-delay="${finalOptions.delay}"` : 'data-bs-autohide="false"'}>
                <div class="toast-header ${bgColor} ${type !== 'warning' ? 'text-white' : ''}">
                    <i class="fas ${iconClass} me-2"></i>
                    <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <button type="button" class="btn-close ${type !== 'warning' ? 'btn-close-white' : ''}" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                    ${actionButtonsHtml}
                </div>
            </div>
        `;
        
        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Get toast element
        const toastEl = document.getElementById(toastId);
        
        // Add action button event listeners
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
            const actionBtns = toastEl.querySelectorAll('.action-btn');
            actionBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const actionText = this.getAttribute('data-action');
                    const actionBtn = finalOptions.actionButtons.find(b => b.text === actionText);
                    
                    if (actionBtn && typeof actionBtn.onClick === 'function') {
                        // Create toast instance reference to pass to handlers
                        const bsToast = bootstrap.Toast.getInstance(toastEl);
                        actionBtn.onClick(bsToast);
                    }
                });
            });
        }
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Handle close event
        toastEl.addEventListener('hidden.bs.toast', function() {
            if (typeof finalOptions.onClose === 'function') {
                finalOptions.onClose();
            }
            // Remove toast from DOM
            toastEl.remove();
        });
        
        return toast;
    } else {
        // Fallback to alert
        alert(message);
        
        // Call onClose if provided
        if (typeof finalOptions.onClose === 'function') {
            finalOptions.onClose();
        }
    }
}

// Open Add Transaction Panel
function openAddTransactionPanel() {
    // Create the slide panel first
    const panel = openSlidePanel('addTransactionPanel', {
        title: 'Add New Transaction',
        icon: 'fa-plus',
        iconColor: '#0ea5e9',
        loadingContent: '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>'
    });
    
    // Then fetch the form contents
    fetch('/get_transaction_form_html')
        .then(response => response.text())
        .then(html => {
            const contentDiv = panel.querySelector('.slide-panel-content');
            if (contentDiv) {
                contentDiv.innerHTML = html;
                
                // Initialize date with today's date
                const dateInput = document.getElementById('date');
                if (dateInput) {
                    dateInput.value = new Date().toISOString().split('T')[0];
                }
                
                // Set up event listeners for form controls
                setupAddTransactionFormListeners();
                
                // Make split_with select user-friendly (no need for Ctrl+click)
                initializeSelectWithoutCtrl('split_with');
            }
        })
        .catch(error => {
            console.error('Error loading form:', error);
            showMessage('Error loading transaction form. Please try again.', 'error');
        });
}

// Open Edit Transaction Panel
function openEditTransactionPanel(expenseId) {
    // Show a loading panel first
    const panel = openSlidePanel('editTransactionPanel', {
        title: 'Edit Transaction',
        icon: 'fa-edit',
        iconColor: '#0ea5e9',
        loadingContent: '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>'
    });
    
    // Fetch expense data
    fetch(`/get_expense_edit_form/${expenseId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to retrieve expense data');
            }
            return response.text();
        })
        .then(html => {
            const contentDiv = panel.querySelector('.slide-panel-content');
            if (contentDiv) {
                contentDiv.innerHTML = html;
                
                // Set up event listeners
                setupEditTransactionFormListeners();
                
                // Make split_with select user-friendly (no need for Ctrl+click)
                initializeSelectWithoutCtrl('edit_split_with');
                
                // Initialize UI state based on data
                toggleEditPersonalExpense();
                toggleEditSplitOptions();
                
                // Load any existing category splits
                loadExistingCategorySplits();
                
                // Setup form submission
                const editForm = document.getElementById('editTransactionForm');
                if (editForm) {
                    editForm.addEventListener('submit', function(e) {
                        e.preventDefault();
                        submitEditForm(this, expenseId);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage(`Error loading expense data: ${error.message}`, 'error');
            closeSlidePanel('editTransactionPanel');
        });
}

// Setup event listeners for add transaction form
function setupAddTransactionFormListeners() {
    // Transaction type change handler
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', handleTransactionTypeChange);
        // Initialize UI based on default transaction type
        handleTransactionTypeChange();
    }
    
    // Personal expense toggle
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (personalExpenseCheck) {
        personalExpenseCheck.addEventListener('change', togglePersonalExpense);
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById('split_method');
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', toggleSplitOptions);
    }
}

// Setup event listeners for edit transaction form
function setupEditTransactionFormListeners() {
    // Add transaction type change handler
    const transactionTypeSelect = document.getElementById('edit_transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', handleEditTransactionTypeChange);
        // Initialize UI based on current transaction type
        handleEditTransactionTypeChange();
    }
    
    // Personal expense toggle
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (personalExpenseCheck) {
        personalExpenseCheck.addEventListener('change', toggleEditPersonalExpense);
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', toggleEditSplitOptions);
    }
    
    // Category split toggle
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    const addSplitBtn = document.getElementById('add_split_btn');
    const amountInput = document.getElementById('edit_amount');
    
    if (enableCategorySplitCheck && categorySplitsContainer && addSplitBtn && amountInput) {
        // Toggle category splits container visibility
        enableCategorySplitCheck.addEventListener('change', function() {
            categorySplitsContainer.style.display = this.checked ? 'block' : 'none';
            
            if (this.checked) {
                // Initialize with one split row using the full amount
                const totalAmount = parseFloat(amountInput.value) || 0;
                // Clear existing splits
                document.getElementById('category_splits_list').innerHTML = '';
                addCategorySplit(totalAmount);
                updateSplitTotals();
            } else {
                // Clear all splits when disabling
                document.getElementById('category_splits_list').innerHTML = '';
                updateSplitTotals();
            }
        });

        // Add split button event listener
        if (addSplitBtn) {
            addSplitBtn.addEventListener('click', function() {
                addCategorySplit(0);
                updateSplitTotals();
            });
        }

        // Amount input change listener to update split total
        if (amountInput) {
            amountInput.addEventListener('input', updateSplitTotals);
        }
    }
}

// Function to load existing category splits data
function loadExistingCategorySplits() {
    const categorySplitsData = document.getElementById('category_splits_data')?.value;
    
    if (categorySplitsData && categorySplitsData.trim() !== '') {
        try {
            const splits = JSON.parse(categorySplitsData);
            if (Array.isArray(splits) && splits.length > 0) {
                // Enable the category splits toggle
                const enableCategorySplitCheck = document.getElementById('enable_category_split');
                const categorySplitsContainer = document.getElementById('category_splits_container');
                
                if (enableCategorySplitCheck && categorySplitsContainer) {
                    enableCategorySplitCheck.checked = true;
                    categorySplitsContainer.style.display = 'block';
                    
                    // Clear existing splits
                    document.getElementById('category_splits_list').innerHTML = '';
                    
                    // Add each split
                    splits.forEach(split => {
                        addCategorySplit(split.amount);
                        
                        // Get the latest added row
                        const rows = document.querySelectorAll('.split-row');
                        const lastRow = rows[rows.length - 1];
                        
                        if (lastRow) {
                            const splitId = lastRow.dataset.splitId;
                            const categorySelect = lastRow.querySelector(`.split-category[data-split-id="${splitId}"]`);
                            
                            if (categorySelect) {
                                categorySelect.value = split.category_id;
                            }
                        }
                    });
                    
                    // Update totals
                    updateSplitTotals();
                }
            }
        } catch (error) {
            console.error('Error parsing category splits data:', error);
        }
    }
}

// Function to handle transaction type changes in edit mode
function handleEditTransactionTypeChange() {
    const transactionTypeSelect = document.getElementById('edit_transaction_type');
    if (!transactionTypeSelect) return;
    
    const transactionType = transactionTypeSelect.value;
    const expenseOnlyFields = document.querySelector('.edit-expense-only-fields');
    const toAccountContainer = document.getElementById('edit_to_account_container');
    const accountLabel = document.getElementById('edit_account_label');
    const categorySplitToggle = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    
    // Show/hide fields based on transaction type
    if (transactionType === 'expense') {
        // Show splitting options for expenses
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'block';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
        
        // Make sure the destination account is cleared
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        if (destinationAccountSelect) {
            destinationAccountSelect.value = '';
        }
        
        // Enable category splits for expenses only
        if (categorySplitToggle) categorySplitToggle.parentElement.style.display = 'block';
    } 
    else if (transactionType === 'income') {
        // Hide splitting options for income
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'none';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Deposit Account';
        
        // Make sure the destination account is cleared
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        if (destinationAccountSelect) {
            destinationAccountSelect.value = '';
        }
        
        // Enable category splits for income
        if (categorySplitToggle) categorySplitToggle.parentElement.style.display = 'block';
    }
    else if (transactionType === 'transfer') {
        // Hide splitting options for transfers
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'none';
        
        // Show destination account
        if (toAccountContainer) toAccountContainer.style.display = 'block';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'From Account';
        
        // Update destination account options to exclude the selected source account
        updateDestinationAccountOptions();
        
        // Disable category splits for transfers
        if (categorySplitToggle) {
            categorySplitToggle.checked = false;
            categorySplitToggle.parentElement.style.display = 'none';
            if (categorySplitsContainer) categorySplitsContainer.style.display = 'none';
        }
    }
}

// Function to update destination account options
function updateDestinationAccountOptions() {
    const sourceAccountSelect = document.getElementById('edit_account_id');
    const destinationAccountSelect = document.getElementById('edit_destination_account_id');
    
    if (!sourceAccountSelect || !destinationAccountSelect) return;
    
    const sourceAccountId = sourceAccountSelect.value;
    
    // Enable all options first
    for (let i = 0; i < destinationAccountSelect.options.length; i++) {
        destinationAccountSelect.options[i].disabled = false;
    }
    
    // If a source account is selected, disable it in the destination select
    if (sourceAccountId) {
        for (let i = 0; i < destinationAccountSelect.options.length; i++) {
            if (destinationAccountSelect.options[i].value === sourceAccountId) {
                destinationAccountSelect.options[i].disabled = true;
                
                // If this was the selected destination, clear the selection
                if (destinationAccountSelect.options[i].selected) {
                    destinationAccountSelect.value = '';
                }
                
                break;
            }
        }
    }
}

// Toggle personal expense mode for edit form
function toggleEditPersonalExpense() {
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (!personalExpenseCheck) return;
    
    const splitWithSelect = document.getElementById('edit_split_with');
    const splitMethodContainer = document.getElementById('edit_split_method')?.parentNode;
    const customSplitContainer = document.getElementById('edit_custom_split_container');
    
    if (personalExpenseCheck.checked) {
        // This is a personal expense - disable split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        
        // Clear any existing split_with selections
        if (splitWithSelect) {
            for (let i = 0; i < splitWithSelect.options.length; i++) {
                splitWithSelect.options[i].selected = false;
            }
            splitWithSelect.disabled = true;
            splitWithSelect.parentNode.style.opacity = '0.5';
        }
    } else {
        // This is a shared expense - enable split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        if (splitWithSelect) {
            splitWithSelect.disabled = false;
            splitWithSelect.parentNode.style.opacity = '1';
        }
        
        // Show custom split container if needed
        const splitMethodSelect = document.getElementById('edit_split_method');
        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
            customSplitContainer.style.display = 'block';
        }
    }
}

// Toggle split options in edit form
function toggleEditSplitOptions() {
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    const customSplitContainer = document.getElementById('edit_custom_split_container');
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    
    if (!customSplitContainer) return;
    
    // Don't show custom split container for personal expenses
    if (personalExpenseCheck && personalExpenseCheck.checked) {
        customSplitContainer.style.display = 'none';
        return;
    }
    
    if (splitMethod === 'equal') {
        customSplitContainer.style.display = 'none';
    } else {
        customSplitContainer.style.display = 'block';
    }
}

// Function to add a new category split row
function addCategorySplit(amount) {
    const splitsList = document.getElementById('category_splits_list');
    if (!splitsList) return;
    
    const splitId = Date.now(); // Unique ID for this split
    
    const splitRow = document.createElement('div');
    splitRow.className = 'row mb-3 split-row';
    splitRow.dataset.splitId = splitId;
    
    // Create the split HTML with category dropdown and amount input
    splitRow.innerHTML = `
        <div class="col-md-5">
            <select class="form-select bg-dark text-light split-category" data-split-id="${splitId}">
                <option value="">Select category</option>
                ${document.getElementById('edit_category_id').innerHTML}
            </select>
        </div>
        <div class="col-md-5">
            <div class="input-group">
                <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                       data-split-id="${splitId}" value="${amount.toFixed(2)}">
            </div>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-outline-danger remove-split" data-split-id="${splitId}">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    splitsList.appendChild(splitRow);
    
    // Add event listeners to the new elements
    splitRow.querySelector('.split-amount').addEventListener('input', updateSplitTotals);
    splitRow.querySelector('.remove-split').addEventListener('click', function() {
        splitRow.remove();
        updateSplitTotals();
    });
}

// Update split totals and validate
function updateSplitTotals() {
    const transactionTotal = parseFloat(document.getElementById('edit_amount').value) || 0;
    let splitTotal = 0;
    
    // Calculate sum of all splits
    document.querySelectorAll('.split-amount').forEach(input => {
        splitTotal += parseFloat(input.value) || 0;
    });
    
    // Update UI
    const splitTotalEl = document.getElementById('split_total');
    const transactionTotalEl = document.getElementById('transaction_total');
    const statusEl = document.getElementById('split_status');
    
    if (splitTotalEl) splitTotalEl.textContent = splitTotal.toFixed(2);
    if (transactionTotalEl) transactionTotalEl.textContent = transactionTotal.toFixed(2);
    
    // Validate total
    if (statusEl) {
        if (Math.abs(splitTotal - transactionTotal) < 0.01) {
            statusEl.textContent = 'Balanced';
            statusEl.className = 'badge bg-success';
        } else if (splitTotal < transactionTotal) {
            statusEl.textContent = 'Underfunded';
            statusEl.className = 'badge bg-warning';
        } else {
            statusEl.textContent = 'Overfunded';
            statusEl.className = 'badge bg-danger';
        }
    }
    
    // Update hidden input with split data
    const splitData = [];
    document.querySelectorAll('.split-row').forEach(row => {
        const splitId = row.dataset.splitId;
        const categorySelect = row.querySelector(`.split-category[data-split-id="${splitId}"]`);
        const amountInput = row.querySelector(`.split-amount[data-split-id="${splitId}"]`);
        
        if (categorySelect && amountInput) {
            const categoryId = categorySelect.value;
            const amount = parseFloat(amountInput.value) || 0;
            
            if (categoryId && amount > 0) {
                splitData.push({
                    category_id: categoryId,
                    amount: amount
                });
            }
        }
    });
    
    const categoryDataInput = document.getElementById('category_splits_data');
    if (categoryDataInput) {
        categoryDataInput.value = JSON.stringify(splitData);
    }
}

// Function to initialize a select without requiring Ctrl+click
function initializeSelectWithoutCtrl(selectId) {
    const select = document.getElementById(selectId);
    if (!select || !select.multiple) return;
    
    // Replace the standard multiple select with a custom one
    const wrapper = document.createElement('div');
    wrapper.className = 'custom-multiselect-wrapper';
    wrapper.style.maxHeight = '200px';
    wrapper.style.overflowY = 'auto';
    wrapper.style.border = '1px solid #444';
    wrapper.style.borderRadius = '0.25rem';
    wrapper.style.backgroundColor = '#2d2d2d';
    
    // Hide the original select
    select.style.display = 'none';
    select.parentNode.insertBefore(wrapper, select.nextSibling);
    
    // Create checkbox options for each option in the select
    Array.from(select.options).forEach(option => {
        if (option.disabled) return;
        
        const item = document.createElement('div');
        item.className = 'custom-multiselect-item';
        item.style.padding = '0.5rem 1rem';
        item.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
        item.style.cursor = 'pointer';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.checked = option.selected;
        checkbox.value = option.value;
        
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.style.cursor = 'pointer';
        label.style.userSelect = 'none';
        label.style.marginLeft = '8px';
        label.textContent = option.textContent;
        
        item.appendChild(checkbox);
        item.appendChild(label);
        wrapper.appendChild(item);
        
        // Add event listener to update the original select when checkbox is clicked
        checkbox.addEventListener('change', function() {
            option.selected = checkbox.checked;
            // Trigger change event on original select
            const event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        });
        
        // Also make the whole item clickable
        item.addEventListener('click', function(e) {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
                option.selected = checkbox.checked;
                // Trigger change event on original select
                const event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
            }
        });
    });
}

// Submit edit form
function submitEditForm(form, expenseId) {
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    }
    
    // Create FormData from the form
    const formData = new FormData(form);
    
    // Handle destination_account_id for transfers
    const transactionTypeSelect = document.getElementById('edit_transaction_type');
    if (transactionTypeSelect && transactionTypeSelect.value === 'transfer') {
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        // If destination account is empty or not selected, make it null instead of empty string
        if (!destinationAccountSelect || !destinationAccountSelect.value) {
            formData.delete('destination_account_id');
            formData.append('destination_account_id', 'null');
        }
    }
    
    // Explicitly add the category_id from the select element
    const categorySelect = document.getElementById('edit_category_id');
    if (categorySelect) {
        // Remove any existing category_id entries to avoid duplicates
        formData.delete('category_id');
        
        // Add the selected category_id, ensuring it's never sent as an empty string
        const categoryId = categorySelect.value || null;
        formData.append('category_id', categoryId);
    }
    
    // Handle category splits
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    if (enableCategorySplitCheck) {
        // Ensure enable_category_split is included properly
        formData.delete('enable_category_split');
        if (enableCategorySplitCheck.checked) {
            formData.append('enable_category_split', 'on');
            
            // Make sure category_splits_data is included
            const categorySplitsData = document.getElementById('category_splits_data');
            if (categorySplitsData) {
                formData.delete('category_splits_data');
                formData.append('category_splits_data', categorySplitsData.value);
            }
        }
    }
    
    // Add proper handling for transaction type
    if (transactionTypeSelect) {
        formData.delete('transaction_type');
        formData.append('transaction_type', transactionTypeSelect.value);
    }
    
    // Send AJAX request
    fetch(`/update_expense/${expenseId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to update transaction: ${response.status} ${response.statusText}`);
        }
        return response.text();
    })
    .then(() => {
        // Success - close panel and reload
        closeSlidePanel('editTransactionPanel');
        showMessage('Transaction updated successfully');
        window.location.reload();
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage(`Error updating transaction: ${error.message}`, 'error');
        
        // Reset button state
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Save Changes';
        }
    });
}

// Handle transaction type change
function handleTransactionTypeChange() {
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (!transactionTypeSelect) return;
    
    const transactionType = transactionTypeSelect.value;
    const expenseOnlyFields = document.querySelectorAll('.expense-only-fields');
    const toAccountContainer = document.getElementById('to_account_container');
    const accountLabel = document.getElementById('account_label');
    
    // Show/hide fields based on transaction type
    if (transactionType === 'expense') {
        // Show splitting options for expenses
        expenseOnlyFields.forEach(el => el.style.display = 'block');
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
    } 
    else if (transactionType === 'income') {
        // Hide splitting options for income
        expenseOnlyFields.forEach(el => el.style.display = 'none');
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Deposit Account';
    }
    else if (transactionType === 'transfer') {
        // Hide splitting options for transfers
        expenseOnlyFields.forEach(el => el.style.display = 'none');
        
        // Show destination account
        if (toAccountContainer) toAccountContainer.style.display = 'block';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'From Account';
    }
}

// Toggle personal expense mode for add form
function togglePersonalExpense() {
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (!personalExpenseCheck) return;
    
    const splitWithSelect = document.getElementById('split_with');
    const splitMethodContainer = document.getElementById('split_method')?.parentNode;
    const customSplitContainer = document.getElementById('custom_split_container');
    
    if (personalExpenseCheck.checked) {
        // This is a personal expense - simplify the form
        if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        
        // Clear any existing split_with selections
        if (splitWithSelect) {
            for (let i = 0; i < splitWithSelect.options.length; i++) {
                splitWithSelect.options[i].selected = false;
            }
            splitWithSelect.disabled = true;
            splitWithSelect.parentNode.style.opacity = '0.5';
        }
    } else {
        // This is a shared expense - enable the split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        if (splitWithSelect) {
            splitWithSelect.disabled = false;
            splitWithSelect.parentNode.style.opacity = '1';
        }
        
        // Show custom split container if needed
        const splitMethodSelect = document.getElementById('split_method');
        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
            customSplitContainer.style.display = 'block';
        }
    }
}

// Toggle split options in add form
function toggleSplitOptions() {
    const splitMethodSelect = document.getElementById('split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    const customSplitContainer = document.getElementById('custom_split_container');
    const personalExpenseCheck = document.getElementById('personal_expense');
    
    if (!customSplitContainer) return;
    
    // Don't show custom split container for personal expenses
    if (personalExpenseCheck && personalExpenseCheck.checked) {
        customSplitContainer.style.display = 'none';
        return;
    }
    
    if (splitMethod === 'equal') {
        customSplitContainer.style.display = 'none';
    } else {
        customSplitContainer.style.display = 'block';
    }
}

// Open slide panel
function openSlidePanel(panelId, options = {}) {
    // Check if panel already exists
    let panel = document.getElementById(panelId);
    
    // Create panel if it doesn't exist
    if (!panel) {
        panel = document.createElement('div');
        panel.id = panelId;
        panel.className = 'slide-panel';
        
        // Create panel header
        const header = document.createElement('div');
        header.className = 'slide-panel-header';
        header.innerHTML = `
            <h4 class="mb-0">
                <i class="fas ${options.icon || 'fa-info-circle'} me-2" style="color: ${options.iconColor || '#15803d'}"></i>
                ${options.title || 'Panel'}
            </h4>
            <button type="button" class="btn-close btn-close-white" onclick="closeSlidePanel('${panelId}')"></button>
        `;
        
        // Create panel content
        const content = document.createElement('div');
        content.className = 'slide-panel-content';
        
        // Add loading content if provided
        if (options.loadingContent) {
            content.innerHTML = options.loadingContent;
        } else if (options.content) {
            content.innerHTML = options.content;
        }
        
        // Assemble panel
        panel.appendChild(header);
        panel.appendChild(content);
        
        // Add to DOM
        document.body.appendChild(panel);
    }
    
    // Show overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.classList.add('active');
        overlay.onclick = function() {
            closeSlidePanel(panelId);
        };
    }
    
    // Show panel with animation
    setTimeout(() => {
        panel.classList.add('active');
    }, 10);
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    return panel;
}

// Close slide panel
function closeSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.classList.remove('active');
    }
    
    // Hide overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}