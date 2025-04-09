/**
 * JavaScript file for handling edit transaction functionality
 * Includes enhanced multi-select functionality for the split_with field
 * 
 * Features:
 * - Enhanced multi-select for split_with field with searchable dropdown
 * - Proper handling of form validation and submission
 * - Support for all transaction types (expense, income, transfer)
 * - Category split functionality for dividing transactions between categories
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
                
                // Initialize enhanced multi-select for split_with
                initializeEditMultiSelect();
                
                // Initialize UI state based on data
                toggleEditPersonalExpense();
                toggleEditSplitOptions();
                
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
            
            // Handle enhanced multi-select if present
            const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
            if (multiSelectContainer) {
                multiSelectContainer.style.opacity = '0.5';
                multiSelectContainer.style.pointerEvents = 'none';
            } else {
                splitWithSelect.parentNode.style.opacity = '0.5';
            }
        }
    } else {
        // This is a shared expense - enable split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        if (splitWithSelect) {
            splitWithSelect.disabled = false;
            
            // Handle enhanced multi-select if present
            const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
            if (multiSelectContainer) {
                multiSelectContainer.style.opacity = '1';
                multiSelectContainer.style.pointerEvents = 'auto';
            } else {
                splitWithSelect.parentNode.style.opacity = '1';
            }
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
    
    // Update the enhanced multi-select if present
    triggerSelectChange(splitWithSelect);
}

// In edit_transaction.js file

/**
 * Fix for the split values not being correctly saved or displayed
 * 
 * This code addresses the inconsistency between what's shown in the UI
 * and what's stored in the database for transaction splits.
 */

// Enhanced function to update split values in the edit form
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
                console.log("Loaded existing split values:", splitValues);
            }
        }
    } catch (e) {
        console.warn('Could not parse existing split details', e);
    }
    
    // Ensure we have entries for all participants
    allParticipantIds.forEach(userId => {
        // Only initialize values that don't exist
        if (splitValues[userId] === undefined) {
            // For the payer, default to 0 (they're paying for others)
            if (userId === paidById) {
                splitValues[userId] = 0;
            } else {
                // For others, calculate a fair share
                const otherParticipantsCount = allParticipantIds.length - 1; // Exclude payer
                
                if (splitMethod === 'percentage') {
                    splitValues[userId] = otherParticipantsCount > 0 ? 
                        (100 / otherParticipantsCount) : 100;
                } else { // custom amount
                    splitValues[userId] = otherParticipantsCount > 0 ? 
                        (totalAmount / otherParticipantsCount) : totalAmount;
                }
            }
        }
    });
    
    // Now build the UI with the values
    if (splitMethod === 'percentage') {
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            const userPercentage = splitValues[userId];
            
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
        });
    } else { // Custom amount
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            const userAmount = splitValues[userId];
            
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
        });
    }
    
    // Add event listeners to inputs and update split details
    setupEditSplitInputListeners(splitMethod, splitValues, totalAmount);
}

// Enhanced function to set up input listeners for split values in edit form
function setupEditSplitInputListeners(splitMethod, splitValues, totalAmount) {
    const splitDetailsInput = document.getElementById('edit_split_details');
    const splitTotalEl = document.getElementById('edit_split_total');
    const splitStatusEl = document.getElementById('edit_split_status');
    
    document.querySelectorAll('.edit-split-value-input').forEach(input => {
        input.addEventListener('input', function() {
            const userId = this.getAttribute('data-user-id');
            const value = parseFloat(this.value) || 0;
            
            // Update the value for this user
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
            
            // Update hidden split details field with proper structure
            if (splitDetailsInput) {
                const detailsObj = {
                    type: splitMethod,
                    values: splitValues
                };
                splitDetailsInput.value = JSON.stringify(detailsObj);
                console.log("Updated split details:", detailsObj);
            }
        });
        
        // Trigger input event to initialize values
        input.dispatchEvent(new Event('input'));
    });
}

// Add this function in your transaction_module.js or edit_transaction.js
function ensureValidSplitData() {
    console.log("Ensuring valid split data before submission");
    
    // Get the key elements
    const splitMethodSelect = document.getElementById('edit_split_method');
    const splitDetailsInput = document.getElementById('edit_split_details');
    const paidBySelect = document.getElementById('edit_paid_by');
    const amountInput = document.getElementById('edit_amount');
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    
    // Skip if personal expense or no split method
    if (!splitMethodSelect || !splitDetailsInput || !paidBySelect || !amountInput || 
        (personalExpenseCheck && personalExpenseCheck.checked)) {
      return;
    }
    
    const splitMethod = splitMethodSelect.value;
    const paidById = paidBySelect.value;
    const totalAmount = parseFloat(amountInput.value) || 0;
    
    // Parse existing split details
    let splitDetails;
    try {
      splitDetails = JSON.parse(splitDetailsInput.value || '{}');
      if (!splitDetails.values) splitDetails.values = {};
      splitDetails.type = splitMethod; // Ensure type matches selected method
    } catch (e) {
      console.error("Error parsing split details:", e);
      splitDetails = { type: splitMethod, values: {} };
    }
    
    // Ensure payer is in the values (typically with value 0 for custom splits)
    if (!(paidById in splitDetails.values)) {
      splitDetails.values[paidById] = 0;
    }
    
    // Update the hidden input
    splitDetailsInput.value = JSON.stringify(splitDetails);
    console.log("Updated split details before submission:", splitDetails);
  }


// Enhanced submit function with additional data validation
function submitEditForm(form, expenseId) {
    // First, validate the split data if present
    const splitMethodSelect = document.getElementById('edit_split_method');
    const splitWithSelect = document.getElementById('edit_split_with');
    const splitDetailsInput = document.getElementById('edit_split_details');
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    
    let hasValidSplitData = true;
    ensureValidSplitData();
    // Only validate if this is a shared expense (not personal)
    if (splitMethodSelect && splitWithSelect && splitDetailsInput && 
        personalExpenseCheck && !personalExpenseCheck.checked) {
        
        const splitMethod = splitMethodSelect.value;
        const splitWithUsers = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
        
        // Parse split details
        try {
            const splitDetails = JSON.parse(splitDetailsInput.value);
            
            // Make sure the values property exists and has data
            if (!splitDetails.values || Object.keys(splitDetails.values).length === 0) {
                console.error("Split details missing values property or it's empty");
                hasValidSplitData = false;
            }
            
            // Ensure the split method matches
            if (splitDetails.type !== splitMethod) {
                console.log("Correcting split method mismatch in details");
                splitDetails.type = splitMethod;
                splitDetailsInput.value = JSON.stringify(splitDetails);
            }
            
            // Make sure all selected users are in the values
            const missingUsers = splitWithUsers.filter(userId => !(userId in splitDetails.values));
            if (missingUsers.length > 0) {
                console.warn("Some users missing from split values:", missingUsers);
                
                // Add missing users with default values
                missingUsers.forEach(userId => {
                    splitDetails.values[userId] = splitMethod === 'percentage' ? 
                        (100 / splitWithUsers.length) : 
                        (parseFloat(document.getElementById('edit_amount')?.value || 0) / splitWithUsers.length);
                });
                
                // Update the input
                splitDetailsInput.value = JSON.stringify(splitDetails);
            }
            
        } catch (e) {
            console.error("Error validating split details:", e);
            hasValidSplitData = false;
        }
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    }
    
    // If split data validation failed, warn the user
    if (!hasValidSplitData) {
        // Show warning but proceed with submission
        console.warn("Split data validation failed, but proceeding with form submission");
        // You can choose to show a message to the user here if you want
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
    
    // Log the form data for debugging
    console.log("Submitting form data:");
    for (const [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
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

/**
 * ENHANCED MULTI-SELECT FUNCTIONALITY
 * Converts the standard select multi to a user-friendly dropdown with checkboxes
 */

// Add necessary styles for multi-select
function addEditMultiSelectStyles() {
    // Check if styles are already added
    if (document.getElementById('edit-form-multi-select-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'edit-form-multi-select-styles';
    styleEl.textContent = `
        .custom-multi-select-container {
            position: relative;
        }
        
        .custom-multi-select-display {
            cursor: pointer;
            min-height: 38px;
            white-space: normal;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 4px;
            padding: 6px 10px;
        }
        
        .custom-multi-select-display .placeholder {
            color: #6c757d;
        }
        
        .custom-multi-select-dropdown {
            position: absolute;
            width: 100%;
            max-height: 250px;
            overflow-y: auto;
            z-index: 1050;
            border: 1px solid #444;
            border-radius: 0.25rem;
            padding: 8px;
            margin-top: 2px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
        }
        
        .custom-multi-select-option {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            cursor: pointer;
            color: #fff;
            border-radius: 0.25rem;
            transition: background-color 0.15s ease;
        }
        
        .custom-multi-select-option:hover {
            background-color: #2d3748;
        }
    `;
    document.head.appendChild(styleEl);
}

// Initialize enhanced multi-select in the edit form
function initializeEditMultiSelect() {
    console.log('Initializing enhanced multi-select for edit form...');
    
    // Add styles first
    addEditMultiSelectStyles();
    
    // Find the select element
    const editSplitWith = document.querySelector('#edit_split_with[data-enhance="true"]') || 
                          document.getElementById('edit_split_with');
    if (!editSplitWith) {
        console.warn('Split with select element not found');
        return;
    }
    
    // Don't re-initialize if already enhanced
    if (editSplitWith.getAttribute('data-enhanced') === 'true') {
        console.log('Multi-select already enhanced, skipping initialization');
        return;
    }
    
    // Apply the enhancement
    enhanceMultiSelect(editSplitWith);
    console.log('Enhanced multi-select initialized for edit form');
}

// Function to convert a standard select into an enhanced multi-select
function enhanceMultiSelect(selectElement) {
    if (!selectElement || !selectElement.multiple) {
        console.warn('Not a multi-select element, cannot enhance:', selectElement);
        return;
    }
    
    // Mark as enhanced to prevent duplicate initialization
    selectElement.setAttribute('data-enhanced', 'true');
    
    // Create wrapper container
    const container = document.createElement('div');
    container.className = 'custom-multi-select-container';
    selectElement.parentNode.insertBefore(container, selectElement);
    container.appendChild(selectElement);
    
    // Create display element
    const displayBox = document.createElement('div');
    displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
    displayBox.innerHTML = '<span class="placeholder">Select people to split with...</span>';
    container.insertBefore(displayBox, selectElement);
    
    // Create dropdown menu container
    const dropdownMenu = document.createElement('div');
    dropdownMenu.className = 'custom-multi-select-dropdown bg-dark';
    dropdownMenu.style.display = 'none';
    container.appendChild(dropdownMenu);
    
    // Add search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control form-control-sm bg-dark text-light mb-2 custom-multi-select-search';
    searchInput.placeholder = 'Search...';
    dropdownMenu.appendChild(searchInput);
    
    // Create option list
    const optionList = document.createElement('div');
    optionList.className = 'custom-multi-select-options';
    dropdownMenu.appendChild(optionList);
    
    // Populate options
    Array.from(selectElement.options).forEach(option => {
        // Skip disabled options
        if (option.disabled) return;
        
        const optionItem = document.createElement('div');
        optionItem.className = 'custom-multi-select-option';
        optionItem.setAttribute('data-value', option.value);
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.checked = option.selected;
        
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.textContent = option.textContent;
        
        optionItem.appendChild(checkbox);
        optionItem.appendChild(label);
        optionList.appendChild(optionItem);
        
        // Handle option click
        optionItem.addEventListener('click', (e) => {
            e.stopPropagation();
            checkbox.checked = !checkbox.checked;
            
            // Update the original select element
            option.selected = checkbox.checked;
            
            // Dispatch change event on the original select
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Update display box
            updateDisplayBox();
        });
    });
    
    // Function to update display box
    function updateDisplayBox() {
        const selectedOptions = Array.from(selectElement.selectedOptions);
        
        if (selectedOptions.length === 0) {
            displayBox.innerHTML = '<span class="placeholder">Select people to split with...</span>';
        } else {
            displayBox.innerHTML = selectedOptions
                .map(opt => `<span class="badge bg-primary me-1">${opt.textContent}</span>`)
                .join(' ');
        }
    }
    
    // Initial update of display box
    updateDisplayBox();
    
    // Toggle dropdown on display box click
    displayBox.addEventListener('click', (e) => {
        // If the select is disabled, don't allow opening the dropdown
        if (selectElement.disabled) {
            return;
        }
        
        e.stopPropagation();
        const isVisible = dropdownMenu.style.display === 'block';
        dropdownMenu.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            searchInput.focus();
            
            // Position dropdown
            const rect = displayBox.getBoundingClientRect();
            dropdownMenu.style.width = rect.width + 'px';
            
            // Position dropdown above or below based on available space
            const spaceBelow = window.innerHeight - rect.bottom;
            if (spaceBelow < 300 && rect.top > 300) {
                dropdownMenu.style.bottom = displayBox.offsetHeight + 'px';
                dropdownMenu.style.top = 'auto';
            } else {
                dropdownMenu.style.top = displayBox.offsetHeight + 'px';
                dropdownMenu.style.bottom = 'auto';
            }
        }
    });
    
    // Handle search
    searchInput.addEventListener('input', (e) => {
        const searchText = e.target.value.toLowerCase();
        
        Array.from(optionList.children).forEach(optionItem => {
            const optionText = optionItem.querySelector('label').textContent.toLowerCase();
            optionItem.style.display = optionText.includes(searchText) ? 'block' : 'none';
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            dropdownMenu.style.display = 'none';
        }
    });
    
    // Sync original select with our custom one when it changes externally
    selectElement.addEventListener('change', () => {
        Array.from(optionList.children).forEach(optionItem => {
            const value = optionItem.getAttribute('data-value');
            const option = selectElement.querySelector(`option[value="${value}"]`);
            const checkbox = optionItem.querySelector('input[type="checkbox"]');
            
            if (option && checkbox) {
                checkbox.checked = option.selected;
            }
        });
        
        updateDisplayBox();
    });
    
    // Ensure disabled state is reflected
    function updateDisabledState() {
        if (selectElement.disabled) {
            container.style.opacity = '0.5';
            container.style.pointerEvents = 'none';
            displayBox.style.backgroundColor = '#1e1e1e';
        } else {
            container.style.opacity = '1';
            container.style.pointerEvents = 'auto';
            displayBox.style.backgroundColor = '#2d2d2d';
        }
    }
    
    // Initial update of disabled state
    updateDisabledState();
    
    // Watch for changes to the disabled attribute
    const observer = new MutationObserver(() => {
        updateDisabledState();
    });
    
    observer.observe(selectElement, { 
        attributes: true, 
        attributeFilter: ['disabled'] 
    });
    
    // Ensure multi-select dropdown stays in the slide panel
    const slidePanel = container.closest('.slide-panel');
    if (slidePanel) {
        slidePanel.addEventListener('scroll', () => {
            if (dropdownMenu.style.display === 'block') {
                const rect = displayBox.getBoundingClientRect();
                dropdownMenu.style.top = displayBox.offsetHeight + 'px';
            }
        });
    }
    
    return container;
}