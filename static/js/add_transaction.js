/**
 * JavaScript file for handling add transaction functionality with enhanced multi-select
 * 
 * NOTE: The openAddTransactionPanel function has been moved to utils.js to ensure
 * it's globally available. Only the supporting functions remain in this file.
 */

// At the top of add_transaction.js
let baseCurrencySymbol = '$'; // Default fallback

// Try to get the symbol from multiple potential sources
function initBaseCurrencySymbol() {
    // Try window object first
    if (window.baseCurrencySymbol) {
        baseCurrencySymbol = window.baseCurrencySymbol;
        console.log("Currency symbol from window:", baseCurrencySymbol);
        return;
    }

    // Try data attribute
    const currencyDataEl = document.getElementById('currency-data');
    if (currencyDataEl) {
        const symbolFromData = currencyDataEl.getAttribute('data-symbol');
        if (symbolFromData) {
            baseCurrencySymbol = symbolFromData;
            console.log("Currency symbol from data attribute:", baseCurrencySymbol);
            return;
        }
    }

    // Try global variable
    if (typeof baseCurrencySymbol !== 'undefined') {
        console.log("Currency symbol from global variable:", baseCurrencySymbol);
        return;
    }

    console.warn("Could not find base currency symbol, using default: $");
}
initBaseCurrencySymbol();

/**
 * Enhanced Multi-Select Implementation
 * Creates a user-friendly multi-select with checkboxes
 */

// Add styles for the enhanced multi-select
function addMultiSelectStyles() {
    // Check if styles are already added
    if (document.getElementById('enhanced-multi-select-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'enhanced-multi-select-styles';
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
        
        .enhanced-multi-select {
            display: none;
        }
    `;
    document.head.appendChild(styleEl);
}

// Function to initialize enhanced multi-select dropdowns
function initializeEnhancedMultiSelect(selector = '.enhanced-multi-select') {
    const multiSelects = document.querySelectorAll(selector);
    
    multiSelects.forEach(select => {
        // Skip if already initialized
        if (select.getAttribute('data-enhanced') === 'true') return;
        
        // Mark as enhanced to prevent duplicate initialization
        select.setAttribute('data-enhanced', 'true');
        
        // Create wrapper container
        const container = document.createElement('div');
        container.className = 'custom-multi-select-container';
        select.parentNode.insertBefore(container, select);
        container.appendChild(select);
        
        // Create display element
        const displayBox = document.createElement('div');
        displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
        displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
        container.insertBefore(displayBox, select);
        
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
        Array.from(select.options).forEach(option => {
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
                const event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
                
                // Update display box
                updateDisplayBox();
            });
        });
        
        // Function to update display box
        function updateDisplayBox() {
            const selectedOptions = Array.from(select.selectedOptions);
            
            if (selectedOptions.length === 0) {
                displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
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
            e.stopPropagation();
            const isVisible = dropdownMenu.style.display === 'block';
            dropdownMenu.style.display = isVisible ? 'none' : 'block';
            
            if (!isVisible) {
                searchInput.focus();
                
                // Position dropdown
                const rect = displayBox.getBoundingClientRect();
                dropdownMenu.style.width = rect.width + 'px';
                dropdownMenu.style.top = rect.bottom + 'px';
                dropdownMenu.style.left = rect.left + 'px';
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
        select.addEventListener('change', () => {
            Array.from(optionList.children).forEach(optionItem => {
                const value = optionItem.getAttribute('data-value');
                const option = select.querySelector(`option[value="${value}"]`);
                const checkbox = optionItem.querySelector('input[type="checkbox"]');
                
                if (option && checkbox) {
                    checkbox.checked = option.selected;
                }
            });
            
            updateDisplayBox();
        });
    });
}

// Function to auto-select the paid by user in the split with dropdown
function autoSelectPaidByUser() {
    const paidBySelect = document.getElementById('paid_by');
    const splitWithSelect = document.getElementById('split_with');
    
    if (!paidBySelect || !splitWithSelect) return;
    
    const paidById = paidBySelect.value;
    if (!paidById) return;
    
    // If there are no existing selections yet
    if (Array.from(splitWithSelect.selectedOptions).length === 0) {
        // Find the option for the paid by user and select it
        const option = splitWithSelect.querySelector(`option[value="${paidById}"]`);
        if (option) {
            option.selected = true;
            // Trigger change event to update the UI
            splitWithSelect.dispatchEvent(new Event('change'));
        }
    }
}

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
    
    // Amount field change handler
    const amountField = document.getElementById('amount');
    if (amountField) {
        amountField.addEventListener('input', function() {
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateSplitValues();
            }
        });
    }
    
    // Paid by change handler
    const paidBySelect = document.getElementById('paid_by');
    if (paidBySelect) {
        paidBySelect.addEventListener('change', function() {
            updateSplitWithOptions();
            
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateSplitValues();
            }
        });
    }
    
    // Split with change handler
    const splitWithSelect = document.getElementById('split_with');
    if (splitWithSelect) {
        splitWithSelect.addEventListener('change', function() {
            // Only update split values if a split method is selected
            const splitMethod = document.getElementById('split_method')?.value;
            if (splitMethod && splitMethod !== 'equal') {
                updateSplitValues();
            }
        });
    }
    
    // Add form submission handler to ensure split details are properly included
    const newTransactionForm = document.getElementById('newTransactionForm');
    if (newTransactionForm) {
        newTransactionForm.addEventListener('submit', function(e) {
            // If this is a custom split, validate the split details are present
            const splitMethod = document.getElementById('split_method')?.value;
            const isPersonalExpense = document.getElementById('personal_expense')?.checked;
            
            if (!isPersonalExpense && splitMethod && splitMethod !== 'equal') {
                const splitDetailsInput = document.getElementById('split_details');
                
                // Check if we have valid split details
                if (!splitDetailsInput || !splitDetailsInput.value) {
                    console.warn('Split details missing, regenerating...');
                    // Force update split values one last time before submission
                    updateSplitValues();
                }
                
                // Double-check we have split details after the update
                if (splitDetailsInput && !splitDetailsInput.value) {
                    console.error('Failed to generate split details');
                    e.preventDefault();
                    alert('Error with split details. Please try again.');
                    return false;
                }
                
                console.log('Form submission with split details:', splitDetailsInput.value);
            }
        });
    }
    
    ensureCustomSplitPersistence();
}

// Handle transaction type change
function handleTransactionTypeChange() {
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (!transactionTypeSelect) return;
    
    const transactionType = transactionTypeSelect.value;
    const expenseOnlyFields = document.querySelectorAll('.expense-only-fields');
    const toAccountContainer = document.getElementById('to_account_container');
    const accountLabel = document.getElementById('account_label');
    const personalExpenseCheck = document.getElementById('personal_expense');
    
    // Show/hide fields based on transaction type
    if (transactionType === 'expense') {
        // Show splitting options for expenses
        expenseOnlyFields.forEach(el => el.style.display = 'block');
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
        
        // Enable personal expense toggle
        if (personalExpenseCheck) {
            personalExpenseCheck.disabled = false;
            const switchContainer = personalExpenseCheck.closest('.form-check');
            if (switchContainer) switchContainer.style.opacity = '1';
        }
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
            
            // Also disable the custom multi-select
            const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
            if (customMultiSelect) {
                customMultiSelect.style.opacity = '0.5';
                customMultiSelect.style.pointerEvents = 'none';
            } else {
                splitWithSelect.parentNode.style.opacity = '0.5';
            }
        }
    } else {
        // This is a shared expense - enable the split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        
        if (splitWithSelect) {
            splitWithSelect.disabled = false;
            
            // Re-enable the custom multi-select
            const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
            if (customMultiSelect) {
                customMultiSelect.style.opacity = '1';
                customMultiSelect.style.pointerEvents = 'auto';
            } else {
                splitWithSelect.parentNode.style.opacity = '1';
            }
            
            // Auto-select the paid_by user
            autoSelectPaidByUser();
        }
        
        // Show custom split container if needed
        const splitMethodSelect = document.getElementById('split_method');
        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
            customSplitContainer.style.display = 'block';
        }
    }
    
    // Update split values if needed
    updateSplitValues();
    
    // Trigger change event to update UI
    if (splitWithSelect) {
        splitWithSelect.dispatchEvent(new Event('change'));
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
        
        // Update the split values UI
        updateSplitValues();
    }
}

// Update split_with options for add form
function updateSplitWithOptions() {
    const paidById = document.getElementById('paid_by')?.value;
    const splitWithSelect = document.getElementById('split_with');
    
    if (!splitWithSelect || !paidById) return;
    
    // Remember currently selected options
    const selectedOptions = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
    
    // If there are no selections yet, auto-select the payer
    if (selectedOptions.length === 0) {
        // Find and select the payer
        for (let i = 0; i < splitWithSelect.options.length; i++) {
            const option = splitWithSelect.options[i];
            if (option.value === paidById) {
                option.selected = true;
                break;
            }
        }
    }
    
    // Trigger change event to update UI
    splitWithSelect.dispatchEvent(new Event('change'));
}

// Updated split values handling functions

/**
 * Update split values UI for the add form
 * FIXED: Custom amount split now properly allows custom values
 */
function updateSplitValues() {
    const splitMethodSelect = document.getElementById('split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (personalExpenseCheck && personalExpenseCheck.checked) return;
    
    const amountInput = document.getElementById('amount');
    const paidBySelect = document.getElementById('paid_by');
    const splitWithSelect = document.getElementById('split_with');
    const splitTotalEl = document.getElementById('split_total');
    const splitValuesContainer = document.getElementById('split_values_container');
    const splitDetailsInput = document.getElementById('split_details');
    
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
    
    // Try to retrieve existing split values from the hidden input
    let existingSplitValues = {};
    if (splitDetailsInput && splitDetailsInput.value) {
        try {
            const splitDetails = JSON.parse(splitDetailsInput.value);
            if (splitDetails && splitDetails.values) {
                existingSplitValues = splitDetails.values;
            }
        } catch (e) {
            console.warn('Could not parse existing split details', e);
        }
    }
    
    splitValuesContainer.innerHTML = '';
    let splitValues = {};
    
    if (splitMethod === 'percentage') {
        // For percentage split, we'll still initialize with equal percentages
        // unless we already have values from previous interactions
        const equalPercentage = allParticipantIds.length ? (100 / allParticipantIds.length) : 0;
        
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            
            // Use existing value if available, otherwise use equal percentage
            const userPercentage = existingSplitValues[userId] !== undefined ? 
                existingSplitValues[userId] : equalPercentage;
            
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
                        <input type="number" class="form-control bg-dark text-light split-value-input"
                            data-user-id="${userId}" step="0.1" min="0" max="100" 
                            value="${userPercentage.toFixed(1)}">
                        <span class="input-group-text bg-dark text-light">%</span>
                    </div>
                </div>
            `;
            splitValuesContainer.appendChild(row);
            
            // Save the initial value
            splitValues[userId] = userPercentage;
        });
    } else { // Custom amount
        // For custom amount split, if we're initially creating the form,
        // set a reasonable default: payer pays 0, others split equally
        
        allParticipantIds.forEach(userId => {
            const userName = Array.from(paidBySelect.options)
                .find(opt => opt.value === userId)?.text || userId;
            
            const isPayerId = userId === paidById;
            
            // Determine the default amount to show:
            // 1. Use existing value if available
            // 2. If this is the payer, default to 0 (they're paying for others)
            // 3. Otherwise, calculate a fair share among non-payers
            
            let userAmount;
            
            if (existingSplitValues[userId] !== undefined) {
                // Use existing value if available
                userAmount = existingSplitValues[userId];
            } else if (isPayerId) {
                // Default payer amount to 0 (they're paying for others)
                userAmount = 0;
            } else {
                // For non-payers, split the total amount among them
                const nonPayerIds = allParticipantIds.filter(id => id !== paidById);
                userAmount = nonPayerIds.length ? (totalAmount / nonPayerIds.length) : 0;
            }
            
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
                        <input type="number" class="form-control bg-dark text-light split-value-input"
                            data-user-id="${userId}" step="0.01" min="0" 
                            value="${userAmount.toFixed(2)}">
                    </div>
                </div>
            `;
            splitValuesContainer.appendChild(row);
            
            // Save the initial value
            splitValues[userId] = userAmount;
        });
    }
    
    // Add event listeners to inputs and update split details
    setupSplitInputListeners(splitMethod, splitValues, totalAmount);
}
function updateSplitDetailsInput() {
    const splitMethodSelect = document.getElementById('split_method');
    const splitDetailsInput = document.getElementById('split_details');
    const splitInputs = document.querySelectorAll('.split-value-input');
    
    if (!splitMethodSelect || !splitDetailsInput || splitInputs.length === 0) return;
    
    const splitMethod = splitMethodSelect.value;
    const splitValues = {};
    
    splitInputs.forEach(input => {
        const userId = input.getAttribute('data-user-id');
        const value = parseFloat(input.value) || 0;
        splitValues[userId] = value;
    });
    
    const splitDetails = {
        type: splitMethod,
        values: splitValues
    };
    
    // Set the hidden input with stringified split details
    splitDetailsInput.value = JSON.stringify(splitDetails);
    
    console.log('Updated Split Details:', splitDetails);
}

function setupSplitInputListeners(splitMethod, splitValues, totalAmount) {
    const splitDetailsInput = document.getElementById('split_details');
    const splitTotalEl = document.getElementById('split_total');
    const splitStatusEl = document.getElementById('split_status');
    
    // Ensure the split_details hidden input has a value from the start
    if (splitDetailsInput) {
        splitDetailsInput.value = JSON.stringify({
            type: splitMethod,
            values: splitValues
        });
        console.log('Initial split details set:', splitDetailsInput.value);
    }
    
    document.querySelectorAll('.split-value-input').forEach(input => {
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
            
            // Update hidden split details field - CRITICALLY IMPORTANT
            if (splitDetailsInput) {
                const splitDetails = {
                    type: splitMethod,
                    values: splitValues
                };
                splitDetailsInput.value = JSON.stringify(splitDetails);
                console.log('Updated split details:', splitDetailsInput.value);
            }
        });
        
        // Trigger input event to initialize values
        input.dispatchEvent(new Event('input'));
    });
}

// Ensure this function is called after creating split inputs
function ensureCustomSplitPersistence() {
    const splitMethodSelect = document.getElementById('split_method');
    const splitWithSelect = document.getElementById('split_with');
    const amountInput = document.getElementById('amount');
    
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', function() {
            // When split method changes, re-apply split values
            updateSplitValues();
        });
    }
    
    if (splitWithSelect) {
        splitWithSelect.addEventListener('change', function() {
            // When split participants change, re-apply split values
            updateSplitValues();
        });
    }
    
    if (amountInput) {
        amountInput.addEventListener('input', function() {
            // When amount changes, re-apply split values
            updateSplitValues();
        });
    }
}


// Explicitly make these functions globally available
window.addMultiSelectStyles = addMultiSelectStyles;
window.initializeEnhancedMultiSelect = initializeEnhancedMultiSelect;
window.setupAddTransactionFormListeners = setupAddTransactionFormListeners;
window.autoSelectPaidByUser = autoSelectPaidByUser;
window.handleTransactionTypeChange = handleTransactionTypeChange;
window.togglePersonalExpense = togglePersonalExpense;
window.toggleSplitOptions = toggleSplitOptions;
window.updateSplitWithOptions = updateSplitWithOptions;
window.updateSplitValues = updateSplitValues;
window.setupSplitInputListeners = setupSplitInputListeners;

