/**
 * JavaScript file for handling edit transaction functionality
 */

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
                
                // Setup form submission
                const editForm = document.getElementById('editTransactionForm');
                if (editForm) {
                    editForm.addEventListener('submit', function(e) {
                        e.preventDefault();
                        logFormValues(); // Debug function
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

// Debug function to log form values
function logFormValues() {
    const categorySelect = document.getElementById('edit_category_id');
    const formElement = document.getElementById('editTransactionForm');
    
    if (categorySelect && formElement) {
        console.log('Current category ID value:', categorySelect.value);
        console.log('Form has category_id field:', formElement.elements['category_id'] !== undefined);
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
    
    // Ensure proper category selection handling
    const categorySelect = document.getElementById('edit_category_id');
    if (categorySelect) {
        // Add a change event listener to log selection changes
        categorySelect.addEventListener('change', function() {
            console.log('Category changed to:', this.value);
        });
        
        // Ensure the category select isn't disabled
        categorySelect.disabled = false;
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', toggleEditSplitOptions);
    }
    
    // Amount field change handler
    const amountField = document.getElementById('edit_amount');
    if (amountField) {
        amountField.addEventListener('input', function() {
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('edit_split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateEditSplitValues();
            }
        });
    }
    
    // Paid by change handler
    const paidBySelect = document.getElementById('edit_paid_by');
    if (paidBySelect) {
        paidBySelect.addEventListener('change', function() {
            updateEditSplitWithOptions();
            
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('edit_split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateEditSplitValues();
            }
        });
    }
    
    // Split with change handler
    const splitWithSelect = document.getElementById('edit_split_with');
    if (splitWithSelect) {
        splitWithSelect.addEventListener('change', function() {
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('edit_split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateEditSplitValues();
            }
        });
    }
    
    // Source account change handler (for transfers)
    const sourceAccountSelect = document.getElementById('edit_account_id');
    if (sourceAccountSelect) {
        sourceAccountSelect.addEventListener('change', function() {
            // Only update if the transaction type is transfer
            const transactionType = document.getElementById('edit_transaction_type')?.value;
            if (transactionType === 'transfer') {
                updateDestinationAccountOptions();
            }
        });
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
    }
}

// Function to update destination account options to exclude the selected source account
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
    
    // Update split values if needed
    updateEditSplitValues();
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
        
        // Update the split values UI
        updateEditSplitValues();
    }
}

// Update split_with options for edit form
function updateEditSplitWithOptions() {
    const paidById = document.getElementById('edit_paid_by')?.value;
    const splitWithSelect = document.getElementById('edit_split_with');
    
    if (!splitWithSelect || !paidById) return;
    
    // Remember currently selected options
    const selectedOptions = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
    
    // Enable/disable payer option
    for (let i = 0; i < splitWithSelect.options.length; i++) {
        const option = splitWithSelect.options[i];
        if (option.value === paidById) {
            // Don't allow selecting the payer
            option.disabled = true;
            option.selected = false;
        } else {
            option.disabled = false;
        }
    }
    
    // Restore selections (except payer)
    for (let i = 0; i < splitWithSelect.options.length; i++) {
        const option = splitWithSelect.options[i];
        if (option.value !== paidById && selectedOptions.includes(option.value)) {
            option.selected = true;
        }
    }
}

// Update split values UI for edit form
function updateEditSplitValues() {
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (personalExpenseCheck && personalExpenseCheck.checked) return;
    
    const amountInput = document.getElementById('edit_amount');
    const paidBySelect = document.getElementById('edit_paid_by');
    const splitWithSelect = document.getElementById('edit_split_with');
    const splitTotalEl = document.getElementById('edit_split_total');
    const splitValuesContainer = document.getElementById('edit_split_values_container');
    const splitDetailsInput = document.getElementById('edit_split_details');
    
    if (!amountInput || !paidBySelect || !splitWithSelect || !splitTotalEl || !splitValuesContainer) return;
    
    const totalAmount = parseFloat(amountInput.value) || 0;
    const paidById = paidBySelect.value;
    
    // Get selected users to split with
    const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
    
    // If no participants, show a message
    if (splitWithIds.length === 0) {
        splitValuesContainer.innerHTML = '<p class="text-center text-warning">Please select people to split with</p>';
        return;
    }
    
    // Get all participant IDs (include payer only if they aren't already in the split list)
    const allParticipantIds = [...splitWithIds];
    if (!allParticipantIds.includes(paidById)) {
        allParticipantIds.unshift(paidById);
    }
    
    splitValuesContainer.innerHTML = '';
    let splitValues = {};
    
    // Try to load existing split details
    try {
        if (splitDetailsInput && splitDetailsInput.value) {
            const details = JSON.parse(splitDetailsInput.value);
            if (details && details.values) {
                splitValues = details.values;
            }
        }
    } catch (e) {
        console.warn('Could not parse existing split details', e);
    }
    
    if (splitMethod === 'percentage') {
        // Start with equal percentages or use existing values
        const equalPercentage = allParticipantIds.length ? (100 / allParticipantIds.length) : 0;
        
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            const userPercentage = splitValues[userId] !== undefined ? splitValues[userId] : equalPercentage;
            
            // Create row for this user
            const row = document.createElement('div');
            row.className = 'row mb-2 align-items-center';
            row.innerHTML = `
                <div class="col-md-6">
                    <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                        ${isPayerId ? '💰' : ''} ${userName}
                    </span>
                    ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
                </div>
                <div class="col-md-6">
                    <div class="input-group">
                        <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                            data-user-id="${userId}" step="0.1" min="0" max="100" 
                            value="${userPercentage.toFixed(1)}">
                        <span class="input-group-text bg-dark text-light">%</span>
                    </div>
                </div>
            `;
            splitValuesContainer.appendChild(row);
            
            // Initialize or use existing value
            splitValues[userId] = userPercentage;
        });
    } else { // Custom amount
        // Start with equal amounts or use existing values
        const equalAmount = allParticipantIds.length ? (totalAmount / allParticipantIds.length) : 0;
        
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            const userAmount = splitValues[userId] !== undefined ? splitValues[userId] : equalAmount;
            
            // Create row for this user
            const row = document.createElement('div');
            row.className = 'row mb-2 align-items-center';
            row.innerHTML = `
                <div class="col-md-6">
                    <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                        ${isPayerId ? '💰' : ''} ${userName}
                    </span>
                    ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
                </div>
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                        <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                            data-user-id="${userId}" step="0.01" min="0" 
                            value="${userAmount.toFixed(2)}">
                    </div>
                </div>
            `;
            splitValuesContainer.appendChild(row);
            
            // Initialize or use existing value
            splitValues[userId] = userAmount;
        });
    }
    
    // Add event listeners to inputs and update split details
    setupEditSplitInputListeners(splitMethod, splitValues, totalAmount);
}

// Setup input listeners for split values in edit form
function setupEditSplitInputListeners(splitMethod, splitValues, totalAmount) {
    const splitDetailsInput = document.getElementById('edit_split_details');
    const splitTotalEl = document.getElementById('edit_split_total');
    const splitStatusEl = document.getElementById('edit_split_status');
    
    document.querySelectorAll('.edit-split-value-input').forEach(input => {
        input.addEventListener('input', function() {
            const userId = this.getAttribute('data-user-id');
            const value = parseFloat(this.value) || 0;
            splitValues[userId] = value;
            
            // Calculate total
            const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
            
            // Update UI
            if (splitTotalEl) {
                if (splitMethod === 'percentage') {
                    splitTotalEl.textContent = total.toFixed(1) + '%';
                    
                    // Update status
                    if (splitStatusEl) {
                        if (Math.abs(total - 100) < 0.1) {
                            splitStatusEl.textContent = 'Balanced';
                            splitStatusEl.className = 'badge bg-success';
                        } else if (total < 100) {
                            splitStatusEl.textContent = 'Underfunded';
                            splitStatusEl.className = 'badge bg-warning';
                        } else {
                            splitStatusEl.textContent = 'Overfunded';
                            splitStatusEl.className = 'badge bg-danger';
                        }
                    }
                } else { // Custom amount
                    splitTotalEl.textContent = total.toFixed(2);
                    
                    // Update status
                    if (splitStatusEl) {
                        if (Math.abs(total - totalAmount) < 0.01) {
                            splitStatusEl.textContent = 'Balanced';
                            splitStatusEl.className = 'badge bg-success';
                        } else if (total < totalAmount) {
                            splitStatusEl.textContent = 'Underfunded';
                            splitStatusEl.className = 'badge bg-warning';
                        } else {
                            splitStatusEl.textContent = 'Overfunded';
                            splitStatusEl.className = 'badge bg-danger';
                        }
                    }
                }
            }
            
            // Update hidden split details field
            if (splitDetailsInput) {
                splitDetailsInput.value = JSON.stringify({
                    type: splitMethod,
                    values: splitValues
                });
            }
        });
        
        // Trigger input event to initialize values
        input.dispatchEvent(new Event('input'));
    });
}

// Modify the submitEditForm function to ensure category_id and category splits are properly included
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
        
        // Log for debugging
        console.log('Category ID selected:', categoryId);
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
                console.log('Category splits data:', categorySplitsData.value);
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